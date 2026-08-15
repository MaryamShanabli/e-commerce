from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.categories.schemas import CategoryResponse, CreateCategoryRequest, UpdateCategoryRequest
from app.categories.service import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)
from app.core.db import get_db
from app.core.security import require_admin

router = APIRouter(prefix="/api/category", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db)) -> list[CategoryResponse]:
    return list_categories(db)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category_by_id(category_id: int, db: Session = Depends(get_db)) -> CategoryResponse:
    return get_category(db, category_id)


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category_route(
    payload: CreateCategoryRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> CategoryResponse:
    return create_category(db, payload)


@router.put("", response_model=CategoryResponse)
def update_category_route(
    payload: UpdateCategoryRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> CategoryResponse:
    return update_category(db, payload)


@router.delete("/{category_id}", status_code=204)
def delete_category_route(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> None:
    delete_category(db, category_id)
