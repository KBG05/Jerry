"""Pagination schemas."""

from typing import TypeVar, Generic, List, Optional

from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationParams(BaseModel):
    """Query parameters for pagination."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., ge=0, description="Total number of items across all pages")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """
        Create a paginated response.
        
        Args:
            items: List of items for current page
            total: Total number of items across all pages
            page: Current page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            PaginatedResponse instance
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
