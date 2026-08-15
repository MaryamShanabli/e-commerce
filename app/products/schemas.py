from decimal import Decimal

from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    id: int
    name: str
    price: Decimal
    quantity: int
    category_id: int
    category_name: str
    description: str | None = None


class CreateProductRequest(BaseModel):
    name: str
    price: Decimal = Field(gt=0)
    description: str | None = None
    quantity: int = Field(ge=0)
    category_id: int


class UpdateProductRequest(BaseModel):
    name: str
    price: Decimal = Field(gt=0)
    description: str | None = None
    quantity: int = Field(ge=0)
    category_id: int
