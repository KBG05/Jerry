"""Filter and sort schemas for job search."""

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class PostedFilter(str, Enum):
    """Filter for when job was posted."""
    
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


class JobSortOption(str, Enum):
    """Sort options for job listings."""
    
    DATE_POSTED = "date-posted"
    DATE_POSTED_ASC = "date-posted-asc"
    RELEVANCE = "relevance"
    VIEWS = "views"


class JobTypeFilter(str, Enum):
    """Job type filter options."""
    
    FULLTIME = "fulltime"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    ALL = "all"


class JobFilterParams(BaseModel):
    """Query parameters for filtering jobs."""

    q: Optional[str] = Field(None, max_length=255, description="Search query for title/description")
    experience: Optional[str] = Field(None, max_length=100, description="Experience level filter")
    job_type: Optional[JobTypeFilter] = Field(None, description="Job type filter")
    is_remote: Optional[bool] = Field(None, description="Filter for remote jobs only")
    posted: Optional[PostedFilter] = Field(default=PostedFilter.ALL, description="Posted date filter")
    skills: Optional[List[str]] = Field(None, description="Filter by required skills")
    company_slug: Optional[str] = Field(None, max_length=255, description="Filter by company slug")


class JobSortParams(BaseModel):
    """Query parameters for sorting jobs."""

    sort: JobSortOption = Field(default=JobSortOption.DATE_POSTED, description="Sort option")
