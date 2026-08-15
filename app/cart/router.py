from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.cart.schemas import (
    AddToCartRequest,
    CartResponse,
    UpdateQuantityRequest,
)
from app.cart.service import add_to_cart, get_cart, update_quantity
from app.core.db import get_db
from app.core.security import get_current_user, require_owner_or_admin
from app.orders.schemas import CheckoutRequest, OrderResponse
from app.orders.service import checkout_cart

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("/{user_id}", response_model=CartResponse)
def get_cart_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    require_owner_or_admin(user_id, current_user)
    return get_cart(db, user_id)


@router.post("/add", response_model=CartResponse)
def add_to_cart_route(
    userID: int,
    payload: AddToCartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    require_owner_or_admin(userID, current_user)
    return add_to_cart(db, userID, payload)


@router.put("/quantity", response_model=CartResponse)
def update_quantity_route(
    payload: UpdateQuantityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    return update_quantity(db, current_user.id, payload)


@router.post("/checkout", response_model=OrderResponse)
def checkout_route(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    return checkout_cart(db, payload, current_user)
