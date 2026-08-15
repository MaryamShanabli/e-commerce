from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_price: Decimal
    quantity: int
    subtotal: Decimal


class CartResponse(BaseModel):
    id: int
    user_id: int
    total_price: Decimal
    items: list[CartItemResponse]


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class UpdateQuantityRequest(BaseModel):
    cart_item_id: int
    quantity_required: int = Field(ge=0)
