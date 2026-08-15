from decimal import Decimal

from sqlalchemy.orm import Session

from app.cart.models import Cart, CartItem
from app.cart.schemas import (
    AddToCartRequest,
    CartItemResponse,
    CartResponse,
    UpdateQuantityRequest,
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.products.models import Product


def _item_response(item: CartItem) -> CartItemResponse:
    return CartItemResponse(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product.name,
        product_price=item.product.price,
        quantity=item.quantity,
        subtotal=item.product.price * item.quantity,
    )


def _cart_response(cart: Cart) -> CartResponse:
    subtotals = [item.product.price * item.quantity for item in cart.items]
    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        total_price=sum(subtotals, Decimal("0")),
        items=[_item_response(item) for item in cart.items],
    )


def get_cart(db: Session, user_id: int) -> CartResponse:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return _cart_response(cart)


def _load_active_product(db: Session, product_id: int) -> Product:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active == True)  # noqa: E712
        .first()
    )
    if product is None:
        raise NotFoundException(f"Product with ID {product_id} not found")
    return product


def add_to_cart(db: Session, user_id: int, payload: AddToCartRequest) -> CartResponse:
    product = _load_active_product(db, payload.product_id)
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()
    item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.product_id == payload.product_id)
        .first()
    )
    new_quantity = (item.quantity + payload.quantity) if item is not None else payload.quantity
    if new_quantity > product.quantity:
        raise ConflictException("Insufficient stock")
    if item is not None:
        item.quantity = new_quantity
    else:
        item = CartItem(
            cart_id=cart.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
        )
        db.add(item)
    db.commit()
    return _cart_response(cart)


def update_quantity(db: Session, current_user_id: int, payload: UpdateQuantityRequest) -> CartResponse:
    item = db.get(CartItem, payload.cart_item_id)
    if item is None:
        raise NotFoundException(f"Cart item with ID {payload.cart_item_id} not found")
    cart = db.get(Cart, item.cart_id)
    if cart is None or cart.user_id != current_user_id:
        raise ForbiddenException("You do not have access to this resource")
    if payload.quantity_required == 0:
        db.delete(item)
        db.commit()
        return _cart_response(cart)
    product = _load_active_product(db, item.product_id)
    if payload.quantity_required > product.quantity:
        raise ConflictException("Insufficient stock")
    item.quantity = payload.quantity_required
    db.commit()
    return _cart_response(cart)
