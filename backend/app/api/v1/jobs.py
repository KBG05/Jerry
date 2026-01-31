"""Jobs API endpoints."""

import uuid
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Job, Company, Location, JobCategory, JobSubCategory
from app.schemas.job import (
    JobCreate, 
    JobUpdate, 
    JobResponse, 
    JobListItem, 
    JobDetailResponse,
    JobBulkCreateRequest,
    JobBulkCreateResponse,
)
from app.schemas.filters import JobFilterParams, JobSortParams, PostedFilter, JobSortOption, JobTypeFilter
from app.schemas.pagination import PaginationParams, PaginatedResponse
from app.services.job_search_service import (
    search_and_filter_jobs, 
    get_job_by_slug, 
    increment_job_view_count
)
from app.services.job_expiration_service import deactivate_job, bulk_deactivate_jobs
from app.services.scheduler import run_cleanup_now
from app.utils.slug import generate_job_slug, generate_slug
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


# Helper function to build filter params from query
def get_filter_params(
    q: Optional[str] = Query(None, max_length=255, description="Search query"),
    experience: Optional[str] = Query(None, max_length=100, description="Experience level"),
    job_type: Optional[JobTypeFilter] = Query(None, description="Job type filter"),
    is_remote: Optional[bool] = Query(None, description="Remote jobs only"),
    posted: PostedFilter = Query(PostedFilter.ALL, description="Posted date filter"),
    skills: Optional[List[str]] = Query(None, description="Skills filter"),
    company_slug: Optional[str] = Query(None, max_length=255, description="Company slug"),
) -> JobFilterParams:
    return JobFilterParams(
        q=q,
        experience=experience,
        job_type=job_type,
        is_remote=is_remote,
        posted=posted,
        skills=skills,
        company_slug=company_slug,
    )


def get_sort_params(
    sort: JobSortOption = Query(JobSortOption.DATE_POSTED, description="Sort option"),
) -> JobSortParams:
    return JobSortParams(sort=sort)


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, limit=limit)


@router.get(
    "",
    response_model=PaginatedResponse[JobListItem],
    summary="List all jobs with filters",
)
async def list_jobs(
    filters: JobFilterParams = Depends(get_filter_params),
    sort: JobSortParams = Depends(get_sort_params),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active jobs with optional filters and pagination.
    
    Query Parameters:
    - q: Search query for title/description
    - experience: Filter by experience level
    - job_type: Filter by job type (fulltime, contract, internship)
    - is_remote: Filter for remote jobs only
    - posted: Filter by posted date (today, week, month, all)
    - skills: Filter by required skills (can specify multiple)
    - company_slug: Filter by company
    - sort: Sort option (date-posted, date-posted-asc, views, relevance)
    - page: Page number (default 1)
    - limit: Items per page (default 20, max 100)
    """
    jobs, total = await search_and_filter_jobs(
        db=db,
        filters=filters,
        sort=sort,
        pagination=pagination,
    )
    
    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
    )


@router.get(
    "/view/{job_slug}",
    summary="Get job details by slug",
)
async def get_job_detail(
    job_slug: str = Path(..., description="Job slug"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed job information by slug.
    
    Increments view count for the job.
    Returns 404 if job not found or expired.
    """
    job = await get_job_by_slug(db, job_slug)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or has expired"
        )
    
    # Increment view count asynchronously
    await increment_job_view_count(db, job['id'])
    job['view_count'] += 1  # Update local response
    
    return job


@router.get(
    "/in-{location_slug}",
    response_model=PaginatedResponse[JobListItem],
    summary="List jobs by location",
)
async def list_jobs_by_location(
    location_slug: str = Path(..., description="Location slug (e.g., san-francisco-ca)"),
    filters: JobFilterParams = Depends(get_filter_params),
    sort: JobSortParams = Depends(get_sort_params),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """
    List jobs in a specific location.
    
    URL format: /jobs/in-{city}-{state}
    Example: /jobs/in-san-francisco-ca
    """
    # Verify location exists
    result = await db.execute(
        select(Location).where(Location.slug == location_slug)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location not found: {location_slug}"
        )
    
    jobs, total = await search_and_filter_jobs(
        db=db,
        filters=filters,
        sort=sort,
        pagination=pagination,
        location_slug=location_slug,
    )
    
    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
    )


@router.get(
    "/{category_slug}/remote",
    response_model=PaginatedResponse[JobListItem],
    summary="List remote jobs by category",
)
async def list_remote_jobs_by_category(
    category_slug: str = Path(..., description="Category slug"),
    filters: JobFilterParams = Depends(get_filter_params),
    sort: JobSortParams = Depends(get_sort_params),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """
    List remote jobs in a specific category.
    
    URL format: /jobs/{category}/remote
    Example: /jobs/software-engineering/remote
    """
    # Verify category exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.slug == category_slug)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_slug}"
        )
    
    jobs, total = await search_and_filter_jobs(
        db=db,
        filters=filters,
        sort=sort,
        pagination=pagination,
        category_slug=category_slug,
        is_remote_only=True,
    )
    
    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
    )


@router.get(
    "/{category_slug}/in-{location_slug}",
    response_model=PaginatedResponse[JobListItem],
    summary="List jobs by category and location",
)
async def list_jobs_by_category_and_location(
    category_slug: str = Path(..., description="Category slug"),
    location_slug: str = Path(..., description="Location slug"),
    filters: JobFilterParams = Depends(get_filter_params),
    sort: JobSortParams = Depends(get_sort_params),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """
    List jobs in a specific category and location.
    
    URL format: /jobs/{category}/in-{city}-{state}
    Example: /jobs/software-engineer/in-san-francisco-ca
    """
    # Verify category exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.slug == category_slug)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_slug}"
        )
    
    # Verify location exists
    result = await db.execute(
        select(Location).where(Location.slug == location_slug)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location not found: {location_slug}"
        )
    
    jobs, total = await search_and_filter_jobs(
        db=db,
        filters=filters,
        sort=sort,
        pagination=pagination,
        category_slug=category_slug,
        location_slug=location_slug,
    )
    
    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
    )


@router.get(
    "/{category_slug}/{subcategory_slug}",
    response_model=PaginatedResponse[JobListItem],
    summary="List jobs by category and subcategory",
)
async def list_jobs_by_subcategory(
    category_slug: str = Path(..., description="Category slug"),
    subcategory_slug: str = Path(..., description="Subcategory slug"),
    filters: JobFilterParams = Depends(get_filter_params),
    sort: JobSortParams = Depends(get_sort_params),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """
    List jobs in a specific subcategory.
    
    URL format: /jobs/{category}/{subcategory}
    Example: /jobs/software-engineering/backend-developer
    """
    # Verify category exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.slug == category_slug)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_slug}"
        )
    
    # Verify subcategory exists and belongs to category
    result = await db.execute(
        select(JobSubCategory).where(
            JobSubCategory.slug == subcategory_slug,
            JobSubCategory.category_id == category.id
        )
    )
    subcategory = result.scalar_one_or_none()
    
    if not subcategory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcategory not found: {subcategory_slug}"
        )
    
    jobs, total = await search_and_filter_jobs(
        db=db,
        filters=filters,
        sort=sort,
        pagination=pagination,
        category_slug=category_slug,
        subcategory_slug=subcategory_slug,
    )
    
    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
    )


@router.get(
    "/{category_slug}",
    response_model=PaginatedResponse[JobListItem],
    summary="List jobs by category",
)
async def list_jobs_by_category(
    category_slug: str = Path(..., description="Category slug"),
    filters: JobFilterParams = Depends(get_filter_params),
    sort: JobSortParams = Depends(get_sort_params),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """
    List jobs in a specific category.
    
    URL format: /jobs/{category}
    Example: /jobs/software-engineering
    """
    # Verify category exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.slug == category_slug)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_slug}"
        )
    
    jobs, total = await search_and_filter_jobs(
        db=db,
        filters=filters,
        sort=sort,
        pagination=pagination,
        category_slug=category_slug,
    )
    
    return PaginatedResponse.create(
        items=jobs,
        total=total,
        page=pagination.page,
        page_size=pagination.limit,
    )


# Admin endpoints
admin_router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


@admin_router.patch(
    "/{job_id}/deactivate",
    summary="Deactivate a job",
)
async def deactivate_single_job(
    job_id: uuid.UUID = Path(..., description="Job UUID"),
    db: AsyncSession = Depends(get_db),
):
    """Manually deactivate a job."""
    success = await deactivate_job(db, job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return {"message": "Job deactivated successfully", "job_id": str(job_id)}


@admin_router.post(
    "/bulk-deactivate",
    summary="Bulk deactivate jobs",
)
async def bulk_deactivate_jobs_endpoint(
    job_ids: Optional[List[uuid.UUID]] = None,
    company_id: Optional[uuid.UUID] = None,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk deactivate jobs by IDs or filters.
    
    Provide at least one filter:
    - job_ids: List of job UUIDs
    - company_id: Deactivate all jobs for a company
    - category_id: Deactivate all jobs in a category
    """
    if not any([job_ids, company_id, category_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter (job_ids, company_id, or category_id) is required"
        )
    
    count = await bulk_deactivate_jobs(
        db=db,
        job_ids=job_ids,
        company_id=str(company_id) if company_id else None,
        category_id=category_id,
    )
    
    return {"message": f"Deactivated {count} jobs", "count": count}


@admin_router.post(
    "/cleanup-expired",
    summary="Trigger cleanup of expired jobs",
)
async def trigger_cleanup():
    """Manually trigger cleanup of all expired jobs."""
    count = await run_cleanup_now()
    return {"message": f"Cleanup complete. Deactivated {count} expired jobs.", "count": count}
