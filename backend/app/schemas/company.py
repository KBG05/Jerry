"""Company schemas."""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class CompanyBase(BaseModel):
    """Base Company schema."""

    name: str = Field(..., max_length=255, description="Company name")
    logo_url: Optional[str] = Field(None, max_length=500, description="URL to company logo")
    website: Optional[str] = Field(None, max_length=500, description="Company website URL")
    description: Optional[str] = Field(None, description="Company description")
    is_verified: bool = Field(default=False, description="Whether company is verified")


class CompanyCreate(CompanyBase):
    """Schema for creating a Company."""

    location_id: Optional[int] = Field(None, description="Location ID for company headquarters")


class CompanyUpdate(BaseModel):
    """Schema for updating a Company."""

    name: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    location_id: Optional[int] = None
    is_verified: Optional[bool] = None


class CompanyResponse(CompanyBase):
    """Schema for Company response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    location_id: Optional[int] = None
    scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    """Schema for Company list item response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    is_verified: bool


class CompanyBulkUpsertItem(BaseModel):
    """Schema for single company in bulk upsert."""

    name: str = Field(..., max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)


class CompanyBulkUpsertRequest(BaseModel):
    """Schema for bulk company upsert request."""

    companies: List[CompanyBulkUpsertItem] = Field(..., min_length=1, max_length=1000)


class CompanyBulkUpsertResponse(BaseModel):
    """Schema for bulk company upsert response."""

    created: int = Field(..., description="Number of companies created")
    updated: int = Field(..., description="Number of companies updated")
    failed: int = Field(..., description="Number of companies failed")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed items")
