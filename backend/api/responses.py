import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1"


class SuccessResponse(BaseModel, Generic[T]):  # noqa: UP046
    success: bool = True
    data: T
    meta: Meta = Field(default_factory=Meta)


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    meta: Meta = Field(default_factory=Meta)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):  # noqa: UP046
    success: bool = True
    data: list[T]
    pagination: PaginationMeta
    meta: Meta = Field(default_factory=Meta)
