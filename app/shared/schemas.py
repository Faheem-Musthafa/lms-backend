"""Shared Pydantic building blocks: ORM base, pagination, envelopes."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response schemas mapped from SQLAlchemy models."""

    model_config = ConfigDict(from_attributes=True)


class PageParams(BaseModel):
    """Standard pagination + search query params."""

    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    search: str | None = Field(None, max_length=200)
    sort: str | None = Field(None, description="field or -field for desc")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page(BaseModel, Generic[T]):
    """Paginated response envelope."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, params: PageParams) -> Page[T]:
        pages = (total + params.size - 1) // params.size if params.size else 0
        return cls(items=items, total=total, page=params.page, size=params.size, pages=pages)


class Message(BaseModel):
    message: str
