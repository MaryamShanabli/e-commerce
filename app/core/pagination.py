from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Query

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total_count: int
    page_number: int
    page_size: int
    total_pages: int
    has_previous_page: bool
    has_next_page: bool


def paginate(query: Query, page: int, size: int) -> dict:
    page = max(page, 1)
    size = min(max(size, 1), 100)
    total_count = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    total_pages = ceil(total_count / size) if total_count else 0
    return {
        "items": items,
        "total_count": total_count,
        "page_number": page,
        "page_size": size,
        "total_pages": total_pages,
        "has_previous_page": page > 1,
        "has_next_page": page < total_pages,
    }
