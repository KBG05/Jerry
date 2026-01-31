"""Job Sub Category schemas."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class JobSubCategoryBase(BaseModel):
    """Base Job Sub Category schema."""

    category_id: int = Field(..., description="Parent category ID")
    name: str = Field(..., max_length=255, description="Sub-category name")
    count: int = Field(default=0, ge=0, description="Number of jobs in this sub-category")


class JobSubCategoryCreate(JobSubCategoryBase):
    """Schema for creating Job Sub Category."""
    pass


class JobSubCategoryUpdate(BaseModel):
    """Schema for updating Job Sub Category."""

    category_id: Optional[int] = Field(None, description="Parent category ID")
    name: Optional[str] = Field(None, max_length=255, description="Sub-category name")
    count: Optional[int] = Field(None, ge=0, description="Number of jobs in this sub-category")


class JobSubCategoryResponse(JobSubCategoryBase):
    """Schema for Job Sub Category response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
