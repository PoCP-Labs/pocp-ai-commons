"""Pagination utilities for list endpoints."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    """Common pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


def paginate(query, db, page_params: PageParams):
    """Apply pagination to a SQLAlchemy query.

    Returns (items, meta) tuple.
    """
    total = query.count()
    total_pages = max(1, (total + page_params.page_size - 1) // page_params.page_size)

    items = query.offset(page_params.offset).limit(page_params.limit).all()

    meta = PageMeta(
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
        total_pages=total_pages,
        has_next=page_params.page < total_pages,
        has_prev=page_params.page > 1,
    )

    return items, meta
