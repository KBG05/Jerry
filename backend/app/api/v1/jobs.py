"""Jobs API endpoints."""

import uuid
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from pydantic import BaseModel, Field
from sqlalchemy import select, func
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
from app.utils.slug import generate_job_slug, generate_slug, generate_unique_slug, generate_location_slug
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


# Sitemap schemas
class SitemapURL(BaseModel):
    """Individual sitemap URL entry."""
    url: str = Field(..., description="The URL path")
    count: int = Field(..., description="Number of jobs for this URL")


class SitemapResponse(BaseModel):
    """Sitemap generation response grouped by type."""
    main_categories: List[SitemapURL] = Field(default_factory=list, description="Main category pages")
    subcategories: List[SitemapURL] = Field(default_factory=list, description="Subcategory pages with 5+ jobs")
    locations: List[SitemapURL] = Field(default_factory=list, description="Location pages with 5+ jobs")
    subcategory_locations: List[SitemapURL] = Field(default_factory=list, description="Subcategory + Location with 3+ jobs")
    category_locations: List[SitemapURL] = Field(default_factory=list, description="Main Category + Location with 10+ jobs")
    remote_categories: List[SitemapURL] = Field(default_factory=list, description="Remote jobs by category")
    total_urls: int = Field(..., description="Total number of URLs generated")


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
    "/sitemap",
    response_model=SitemapResponse,
    summary="Generate sitemap URLs",
)
async def generate_sitemap(
    db: AsyncSession = Depends(get_db),
):
    """
    Generate sitemap URLs based on job counts.
    
    Rules:
    - Main Categories: All categories with active jobs
    - Subcategories: Create when 5+ jobs exist
    - Locations: Create when 5+ jobs exist
    - Subcategory + Location: Create when 3+ jobs exist
    - Main Category + Location: Create when 10+ jobs exist
    - Remote Categories: All categories with remote jobs
    """
    sitemap = SitemapResponse(
        main_categories=[],
        subcategories=[],
        locations=[],
        subcategory_locations=[],
        category_locations=[],
        remote_categories=[],
        total_urls=0,
    )
    
    # 1. Main Categories - all categories with active jobs
    category_query = select(
        JobCategory.slug,
        func.count(Job.id).label('count')
    ).join(
        Job, Job.category_id == JobCategory.id
    ).where(
        Job.is_active == True
    ).group_by(JobCategory.id, JobCategory.slug)
    
    result = await db.execute(category_query)
    for row in result:
        sitemap.main_categories.append(
            SitemapURL(url=f"/jobs/{row.slug}", count=row.count) #type: ignore
        )
    
    # 2. Subcategories - 5+ jobs
    subcat_query = select(
        JobSubCategory.slug,
        func.count(Job.id).label('count')
    ).join(
        Job, Job.subcategory_id == JobSubCategory.id
    ).where(
        Job.is_active == True
    ).group_by(JobSubCategory.id, JobSubCategory.slug).having(
        func.count(Job.id) >= 5
    )
    
    result = await db.execute(subcat_query)
    for row in result:
        sitemap.subcategories.append(
            SitemapURL(url=f"/jobs/{row.slug}", count=row.count)#type: ignore
        )
    
    # 3. Locations - 5+ jobs
    location_query = select(
        Location.slug,
        func.count(Job.id).label('count')
    ).join(
        Job, Job.location_id == Location.id
    ).where(
        Job.is_active == True
    ).group_by(Location.id, Location.slug).having(
        func.count(Job.id) >= 5
    )
    
    result = await db.execute(location_query)
    for row in result:
        sitemap.locations.append(
            SitemapURL(url=f"/jobs/in-{row.slug}", count=row.count) #type: ignore
        )
    
    # 4. Subcategory + Location - 3+ jobs
    subcat_loc_query = select(
        JobSubCategory.slug.label('subcat_slug'),
        Location.slug.label('loc_slug'),
        func.count(Job.id).label('count')
    ).join(
        Job, Job.subcategory_id == JobSubCategory.id
    ).join(
        Location, Job.location_id == Location.id
    ).where(
        Job.is_active == True
    ).group_by(
        JobSubCategory.id, JobSubCategory.slug,
        Location.id, Location.slug
    ).having(
        func.count(Job.id) >= 3
    )
    
    result = await db.execute(subcat_loc_query)
    for row in result:
        sitemap.subcategory_locations.append(
            SitemapURL(
                url=f"/jobs/{row.subcat_slug}/in-{row.loc_slug}",
                count=row.count #type: ignore
            )
        )
    
    # 5. Main Category + Location - 10+ jobs
    cat_loc_query = select(
        JobCategory.slug.label('cat_slug'),
        Location.slug.label('loc_slug'),
        func.count(Job.id).label('count')
    ).join(
        Job, Job.category_id == JobCategory.id
    ).join(
        Location, Job.location_id == Location.id
    ).where(
        Job.is_active == True
    ).group_by(
        JobCategory.id, JobCategory.slug,
        Location.id, Location.slug
    ).having(
        func.count(Job.id) >= 10
    )
    
    result = await db.execute(cat_loc_query)
    for row in result:
        sitemap.category_locations.append(
            SitemapURL(
                url=f"/jobs/{row.cat_slug}/in-{row.loc_slug}",
                count=row.count #type: ignore
            )
        )
    
    # 6. Remote Categories - all categories with remote jobs
    remote_query = select(
        JobCategory.slug,
        func.count(Job.id).label('count')
    ).join(
        Job, Job.category_id == JobCategory.id
    ).where(
        Job.is_active == True,
        Job.is_remote == True
    ).group_by(JobCategory.id, JobCategory.slug)
    
    result = await db.execute(remote_query)
    for row in result:
        sitemap.remote_categories.append(
            SitemapURL(url=f"/jobs/{row.slug}/remote", count=row.count)#type: ignore
        )
    
    # Calculate total URLs
    sitemap.total_urls = (
        len(sitemap.main_categories) +
        len(sitemap.subcategories) +
        len(sitemap.locations) +
        len(sitemap.subcategory_locations) +
        len(sitemap.category_locations) +
        len(sitemap.remote_categories)
    )
    
    logger.info(f"Generated sitemap with {sitemap.total_urls} URLs")
    return sitemap


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


@admin_router.post(
    "/bulk-create",
    response_model=JobBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create jobs",
)
async def bulk_create_jobs(
    request: JobBulkCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk create jobs for scraper/data import.
    
    - Automatically creates/links companies and locations
    - Generates slugs for SEO-friendly URLs
    - Validates categories and subcategories
    - Returns count of created/failed jobs with error details
    """
    created = 0
    failed = 0
    errors = []
    
    for idx, job_data in enumerate(request.jobs):
        try:
            # 1. Find or create company
            company_result = await db.execute(
                select(Company).where(
                    Company.name == job_data.company_name
                )
            )
            company = company_result.scalar_one_or_none()
            
            if not company:
                # Create new company
                base_slug = generate_slug(job_data.company_name)
                
                async def check_company_slug_exists(slug: str) -> bool:
                    result = await db.execute(select(Company).where(Company.slug == slug))
                    return result.scalar_one_or_none() is not None
                
                company_slug = await generate_unique_slug(base_slug, check_company_slug_exists)
                company = Company(
                    name=job_data.company_name,
                    slug=company_slug,
                )
                db.add(company)
                await db.flush()
            
            # 2. Find or create location
            location_id = None
            if job_data.location_city and job_data.location_state:
                location_result = await db.execute(
                    select(Location).where(
                        Location.city == job_data.location_city,
                        Location.state == job_data.location_state
                    )
                )
                location = location_result.scalar_one_or_none()
                
                if not location:
                    base_slug = generate_location_slug(job_data.location_city, job_data.location_state)
                    
                    async def check_location_slug_exists(slug: str) -> bool:
                        result = await db.execute(select(Location).where(Location.slug == slug))
                        return result.scalar_one_or_none() is not None
                    
                    location_slug = await generate_unique_slug(base_slug, check_location_slug_exists)
                    location = Location(
                        city=job_data.location_city,
                        state=job_data.location_state,
                        slug=location_slug,
                    )
                    db.add(location)
                    await db.flush()
                
                location_id = location.id
            
            # 3. Find category
            category_result = await db.execute(
                select(JobCategory).where(JobCategory.slug == job_data.category_slug)
            )
            category = category_result.scalar_one_or_none()
            if not category:
                errors.append(f"Job {idx + 1}: Category '{job_data.category_slug}' not found")
                failed += 1
                continue
            
            # 4. Find subcategory (optional)
            subcategory_id = None
            if job_data.subcategory_slug:
                subcategory_result = await db.execute(
                    select(JobSubCategory).where(
                        JobSubCategory.slug == job_data.subcategory_slug,
                        JobSubCategory.category_id == category.id
                    )
                )
                subcategory = subcategory_result.scalar_one_or_none()
                if not subcategory:
                    errors.append(f"Job {idx + 1}: Subcategory '{job_data.subcategory_slug}' not found in category")
                    failed += 1
                    continue
                subcategory_id = subcategory.id
            
            # 5. Generate job slug
            job_slug = generate_job_slug(
                job_data.title,
                job_data.company_name,
                uuid.uuid4()
            )
            
            # 6. Create job
            job = Job(
                title=job_data.title,
                company_id=company.id,
                location_id=location_id,
                category_id=category.id,
                subcategory_id=subcategory_id,
                job_type=job_data.job_type,
                is_remote=job_data.is_remote,
                salary=job_data.salary,
                experience=job_data.experience,
                skills=job_data.skills,
                description=job_data.description,
                job_url=job_data.job_url,
                slug=job_slug,
                posted_date=job_data.posted_date,
                end_date=job_data.end_date,
                is_active=True,
            )
            db.add(job)
            created += 1
            
        except Exception as e:
            errors.append(f"Job {idx + 1}: {str(e)}")
            failed += 1
            logger.error(f"Failed to create job {idx + 1}: {str(e)}")
    
    # Commit all changes
    try:
        await db.commit()
        logger.info(f"Bulk create completed: {created} created, {failed} failed")
    except Exception as e:
        await db.rollback()
        logger.error(f"Bulk create failed during commit: {str(e)}")
        return JobBulkCreateResponse(
            created=0,
            failed=len(request.jobs),
            errors=[f"Database commit failed: {str(e)}"]
        )
    
    return JobBulkCreateResponse(
        created=created,
        failed=failed,
        errors=errors
    )


