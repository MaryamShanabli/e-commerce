from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import PaginatedResponse
from app.core.security import require_admin
from app.products.schemas import CreateProductRequest, ProductResponse, UpdateProductRequest
from app.products.service import (
    create_product,
    delete_product,
    get_product,
    list_products,
    update_product,
)

router = APIRouter(prefix="/api/product", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
def get_products(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    return list_products(db, page, size)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)) -> ProductResponse:
    return get_product(db, product_id)


@router.post("", response_model=ProductResponse, status_code=201)
def create_product_route(
    payload: CreateProductRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> ProductResponse:
    return create_product(db, payload)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product_route(
    product_id: int,
    payload: UpdateProductRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> ProductResponse:
    return update_product(db, product_id, payload)


@router.delete("/{product_id}", status_code=204)
def delete_product_route(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> None:
    delete_product(db, product_id)
