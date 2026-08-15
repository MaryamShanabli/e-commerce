from sqlalchemy.orm import Session

from app.categories.models import Category
from app.categories.schemas import CategoryResponse, CreateCategoryRequest, UpdateCategoryRequest
from app.core.exceptions import ConflictException, NotFoundException
from app.products.models import Product


def _to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(id=category.id, name=category.name)


def list_categories(db: Session) -> list[CategoryResponse]:
    categories = db.query(Category).order_by(Category.id).all()
    return [_to_response(c) for c in categories]


def get_category(db: Session, category_id: int) -> CategoryResponse:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundException(f"Category with ID {category_id} not found")
    return _to_response(category)


def create_category(db: Session, payload: CreateCategoryRequest) -> CategoryResponse:
    name = payload.name.strip()
    if not name:
        raise ConflictException("Category name cannot be empty")
    existing = db.query(Category).filter(Category.name == name).first()
    if existing is not None:
        raise ConflictException("Category name already exists")
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return _to_response(category)


def update_category(db: Session, payload: UpdateCategoryRequest) -> CategoryResponse:
    name = payload.name.strip()
    if not name:
        raise ConflictException("Category name cannot be empty")
    category = db.get(Category, payload.id)
    if category is None:
        raise NotFoundException(f"Category with ID {payload.id} not found")
    duplicate = (
        db.query(Category)
        .filter(Category.name == name, Category.id != payload.id)
        .first()
    )
    if duplicate is not None:
        raise ConflictException("Category name already exists")
    category.name = name
    db.commit()
    db.refresh(category)
    return _to_response(category)


def delete_category(db: Session, category_id: int) -> None:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundException(f"Category with ID {category_id} not found")
    has_products = (
        db.query(Product.id).filter(Product.category_id == category_id).first()
    )
    if has_products is not None:
        raise ConflictException("Category has associated products")
    db.delete(category)
    db.commit()
