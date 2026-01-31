"""Job schemas."""

import uuid
from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.company import CompanyListResponse
from app.schemas.location import LocationResponse


class JobBase(BaseModel):
    """Base Job schema."""

    title: str = Field(..., max_length=255, description="Job title")
    job_type: str = Field(..., max_length=50, description="Job type: fulltime, contract, internship")
    is_remote: bool = Field(default=False, description="Whether job is remote")
    salary: Optional[str] = Field(None, max_length=200, description="Salary information (scraped text)")
    experience: Optional[str] = Field(None, max_length=100, description="Experience requirement (scraped text)")
    skills: Optional[List[str]] = Field(None, description="List of required skills")
    description: str = Field(..., description="Job description")
    job_url: str = Field(..., max_length=1000, description="Original job posting URL")
    posted_date: date = Field(..., description="Date job was posted")
    end_date: Optional[date] = Field(None, description="Date job expires/ends")


class JobCreate(JobBase):
    """Schema for creating a Job."""

    company_id: uuid.UUID = Field(..., description="Company ID")
    location_id: Optional[int] = Field(None, description="Location ID")
    category_id: int = Field(..., description="Job category ID")
    subcategory_id: Optional[int] = Field(None, description="Job subcategory ID")


class JobUpdate(BaseModel):
    """Schema for updating a Job."""

    title: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, max_length=50)
    is_remote: Optional[bool] = None
    salary: Optional[str] = Field(None, max_length=200)
    experience: Optional[str] = Field(None, max_length=100)
    skills: Optional[List[str]] = None
    description: Optional[str] = None
    job_url: Optional[str] = Field(None, max_length=1000)
    posted_date: Optional[date] = None
    end_date: Optional[date] = None
    location_id: Optional[int] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    is_active: Optional[bool] = None


class JobResponse(JobBase):
    """Schema for Job response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    company_id: uuid.UUID
    location_id: Optional[int] = None
    category_id: int
    subcategory_id: Optional[int] = None
    view_count: int = 0
    is_active: bool = True
    scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JobListItem(BaseModel):
    """Schema for Job list item (lighter response)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    job_type: str
    is_remote: bool
    salary: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[str]] = None
    posted_date: date
    company_name: str
    company_slug: str
    company_logo_url: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    category_name: str
    category_slug: str


class JobDetailResponse(BaseModel):
    """Schema for Job detail response with related data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    job_type: str
    is_remote: bool
    salary: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[str]] = None
    description: str
    requirements: Optional[List[str]] = None
    job_url: str
    posted_date: date
    end_date: Optional[date] = None
    view_count: int
    is_active: bool
    company: CompanyListResponse
    location: Optional[LocationResponse] = None
    category_name: str
    category_slug: str
    subcategory_name: Optional[str] = None
    subcategory_slug: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobBulkCreateItem(BaseModel):
    """Schema for single job in bulk create."""

    title: str = Field(..., max_length=255)
    company_name: str = Field(..., max_length=255)
    job_type: str = Field(..., max_length=50)
    is_remote: bool = False
    salary: Optional[str] = Field(None, max_length=200)
    experience: Optional[str] = Field(None, max_length=100)
    skills: Optional[List[str]] = None
    description: str
    job_url: str = Field(..., max_length=1000)
    posted_date: date
    end_date: Optional[date] = None
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)
    category_slug: str = Field(..., max_length=255)
    subcategory_slug: Optional[str] = Field(None, max_length=255)


class JobBulkCreateRequest(BaseModel):
    """Schema for bulk job create request."""

    jobs: List[JobBulkCreateItem] = Field(..., min_length=1, max_length=500)


class JobBulkCreateResponse(BaseModel):
    """Schema for bulk job create response."""

    created: int = Field(..., description="Number of jobs created")
    failed: int = Field(..., description="Number of jobs failed")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed items")
