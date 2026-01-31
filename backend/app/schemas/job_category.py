"""Job Category schemas."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class JobCategoryBase(BaseModel):
    """Base Job Category schema."""

    name: str = Field(..., max_length=255, description="Category name")
    count: int = Field(default=0, ge=0, description="Number of jobs in this category")


class JobCategoryCreate(JobCategoryBase):
    """Schema for creating Job Category."""
    
    slug: Optional[str] = Field(None, max_length=255, description="URL-friendly slug (auto-generated if not provided)")


class JobCategoryUpdate(BaseModel):
    """Schema for updating Job Category."""

    name: Optional[str] = Field(None, max_length=255, description="Category name")
    slug: Optional[str] = Field(None, max_length=255, description="URL-friendly slug")
    count: Optional[int] = Field(None, ge=0, description="Number of jobs in this category")


class JobCategoryResponse(JobCategoryBase):
    """Schema for Job Category response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
