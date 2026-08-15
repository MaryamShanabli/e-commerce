from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth.models import User
from app.cart.models import Cart, CartItem
from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from app.orders.models import Order, OrderItem
from app.orders.schemas import CheckoutRequest, OrderItemResponse, OrderResponse
from app.products.models import Product


def _order_response(order: Order) -> OrderResponse:
    items = [
        OrderItemResponse(
            product_id=oi.product_id,
            product_name=oi.product_name,
            quantity=oi.quantity,
            unit_price=oi.unit_price,
            subtotal=oi.unit_price * oi.quantity,
        )
        for oi in order.items
    ]
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        order_date=order.order_date,
        status=order.status,
        price=order.price,
        items=items,
        shipping_address=order.shipping_address,
        payment_method=order.payment_method,
    )


def checkout_cart(db: Session, payload: CheckoutRequest, current_user: User) -> OrderResponse:
    if payload.user_id != current_user.id and not current_user.is_admin:
        raise ForbiddenException("You do not have access to this resource")

    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if cart is None or not cart.items:
        raise BadRequestException("Cart is empty")

    for item in cart.items:
        result = db.execute(
            update(Product)
            .where(
                Product.id == item.product_id,
                Product.quantity >= item.quantity,
                Product.is_active == True,  # noqa: E712
            )
            .values(quantity=Product.quantity - item.quantity)
        )
        if result.rowcount != 1:
            raise ConflictException(f"Insufficient stock for {item.product.name}")

    total_price = sum(
        (item.product.price * item.quantity for item in cart.items), Decimal("0")
    )
    order = Order(
        user_id=current_user.id,
        status="Pending",
        price=total_price,
        shipping_address=payload.shipping_address,
        payment_method=payload.payment_method,
    )
    db.add(order)
    db.flush()
    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
        )
    for item in cart.items:
        db.delete(item)
    db.commit()
    db.refresh(order)
    return _order_response(order)


def list_orders(db: Session, current_user: User) -> list[OrderResponse]:
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.order_date.desc(), Order.id.desc())
        .all()
    )
    return [_order_response(order) for order in orders]


def get_order(db: Session, order_id: int, current_user: User) -> OrderResponse:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundException(f"Order with ID {order_id} not found")
    if order.user_id != current_user.id and not current_user.is_admin:
        raise ForbiddenException("You do not have access to this resource")
    return _order_response(order)
