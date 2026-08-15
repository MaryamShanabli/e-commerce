from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.db import get_db
from app.core.security import get_current_user
from app.orders.schemas import OrderResponse
from app.orders.service import get_order, list_orders

router = APIRouter(prefix="/api/order", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
def get_orders_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderResponse]:
    return list_orders(db, current_user)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_route(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return get_order(db, order_id, current_user)
