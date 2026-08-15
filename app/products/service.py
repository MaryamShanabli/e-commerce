from sqlalchemy.orm import Session

from app.categories.models import Category
from app.core.exceptions import NotFoundException
from app.core.pagination import paginate
from app.products.models import Product
from app.products.schemas import CreateProductRequest, ProductResponse, UpdateProductRequest


def _to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        price=product.price,
        quantity=product.quantity,
        category_id=product.category_id,
        category_name=product.category.name,
        description=product.description,
    )


def _require_category(db: Session, category_id: int) -> None:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundException(f"Category with ID {category_id} not found")


def list_products(db: Session, page: int, size: int) -> dict:
    query = (
        db.query(Product)
        .join(Product.category)
        .filter(Product.is_active == True)  # noqa: E712
        .order_by(Product.id)
    )
    result = paginate(query, page, size)
    result["items"] = [_to_response(p) for p in result["items"]]
    return result


def create_product(db: Session, payload: CreateProductRequest) -> ProductResponse:
    _require_category(db, payload.category_id)
    product = Product(
        name=payload.name,
        price=payload.price,
        description=payload.description,
        quantity=payload.quantity,
        category_id=payload.category_id,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_response(product)


def get_product(db: Session, product_id: int) -> ProductResponse:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active == True)  # noqa: E712
        .first()
    )
    if product is None:
        raise NotFoundException(f"Product with ID {product_id} not found")
    return _to_response(product)


def update_product(db: Session, product_id: int, payload: UpdateProductRequest) -> ProductResponse:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active == True)  # noqa: E712
        .first()
    )
    if product is None:
        raise NotFoundException(f"Product with ID {product_id} not found")
    _require_category(db, payload.category_id)
    product.name = payload.name
    product.price = payload.price
    product.description = payload.description
    product.quantity = payload.quantity
    product.category_id = payload.category_id
    db.commit()
    db.refresh(product)
    return _to_response(product)


def delete_product(db: Session, product_id: int) -> None:
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active == True)  # noqa: E712
        .first()
    )
    if product is None:
        raise NotFoundException(f"Product with ID {product_id} not found")
    product.is_active = False
    db.commit()
