from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

OrderStatus = Literal["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    id: int
    user_id: int
    order_date: datetime
    status: OrderStatus
    price: Decimal
    items: list[OrderItemResponse]
    shipping_address: str
    payment_method: str


class CheckoutRequest(BaseModel):
    user_id: int
    payment_method: str
    shipping_address: str
