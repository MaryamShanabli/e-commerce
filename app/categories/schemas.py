from pydantic import BaseModel, Field, field_validator


class CategoryResponse(BaseModel):
    id: int
    name: str


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class UpdateCategoryRequest(BaseModel):
    id: int
    name: str = Field(min_length=1)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value
