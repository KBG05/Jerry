"""Job search and filter service."""

from datetime import date, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Job, Company, Location, JobCategory, JobSubCategory
from app.schemas.filters import JobFilterParams, JobSortParams, PostedFilter, JobSortOption, JobTypeFilter
from app.schemas.pagination import PaginationParams
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_active_job_base_filter():
    """Get base filter for active, non-expired jobs."""
    today = date.today()
    return and_(
        Job.is_active == True,
        or_(Job.end_date.is_(None), Job.end_date >= today)
    )


def build_posted_date_filter(posted: PostedFilter):
    """Build filter for posted date range."""
    if posted == PostedFilter.ALL:
        return None
    
    today = date.today()
    
    if posted == PostedFilter.TODAY:
        return Job.posted_date == today
    elif posted == PostedFilter.WEEK:
        week_ago = today - timedelta(days=7)
        return Job.posted_date >= week_ago
    elif posted == PostedFilter.MONTH:
        month_ago = today - timedelta(days=30)
        return Job.posted_date >= month_ago
    
    return None


def build_sort_clause(sort: JobSortOption):
    """Build ORDER BY clause based on sort option."""
    if sort == JobSortOption.DATE_POSTED:
        return desc(Job.posted_date), desc(Job.created_at)
    elif sort == JobSortOption.DATE_POSTED_ASC:
        return asc(Job.posted_date), asc(Job.created_at)
    elif sort == JobSortOption.VIEWS:
        return desc(Job.view_count), desc(Job.posted_date)
    elif sort == JobSortOption.RELEVANCE:
        # For relevance, we'd need full-text search ranking
        # Fall back to date for now
        return desc(Job.posted_date), desc(Job.created_at)
    
    return desc(Job.posted_date), desc(Job.created_at)


async def search_and_filter_jobs(
    db: AsyncSession,
    filters: JobFilterParams,
    sort: JobSortParams,
    pagination: PaginationParams,
    category_slug: Optional[str] = None,
    subcategory_slug: Optional[str] = None,
    location_slug: Optional[str] = None,
    is_remote_only: bool = False
) -> Tuple[List[dict], int]:
    """
    Search and filter jobs with pagination.
    
    Args:
        db: Database session
        filters: Filter parameters (q, experience, job_type, etc.)
        sort: Sort parameters
        pagination: Pagination parameters
        category_slug: Optional category slug filter
        subcategory_slug: Optional subcategory slug filter
        location_slug: Optional location slug filter
        is_remote_only: Filter for remote jobs only
        
    Returns:
        Tuple of (list of job dicts with related data, total count)
    """
    # Build base query with joins for related data
    query = (
        select(
            Job,
            Company.name.label('company_name'),
            Company.slug.label('company_slug'),
            Company.logo_url.label('company_logo_url'),
            Location.city.label('location_city'),
            Location.state.label('location_state'),
            JobCategory.name.label('category_name'),
            JobCategory.slug.label('category_slug'),
            JobSubCategory.name.label('subcategory_name'),
            JobSubCategory.slug.label('subcategory_slug'),
        )
        .join(Company, Job.company_id == Company.id)
        .outerjoin(Location, Job.location_id == Location.id)
        .join(JobCategory, Job.category_id == JobCategory.id)
        .outerjoin(JobSubCategory, Job.subcategory_id == JobSubCategory.id)
    )
    
    # Build conditions list
    conditions = [get_active_job_base_filter()]
    
    # Category filter
    if category_slug:
        conditions.append(JobCategory.slug == category_slug)
    
    # Subcategory filter
    if subcategory_slug:
        conditions.append(JobSubCategory.slug == subcategory_slug)
    
    # Location filter
    if location_slug:
        conditions.append(Location.slug == location_slug)
    
    # Remote filter (from URL path or query param)
    if is_remote_only or filters.is_remote:
        conditions.append(Job.is_remote == True)
    
    # Job type filter
    if filters.job_type and filters.job_type != JobTypeFilter.ALL:
        conditions.append(Job.job_type == filters.job_type.value)
    
    # Experience filter
    if filters.experience:
        conditions.append(Job.experience.ilike(f"%{filters.experience}%"))
    
    # Posted date filter
    posted_filter = build_posted_date_filter(filters.posted)#type: ignore
    if posted_filter is not None:
        conditions.append(posted_filter)
    
    # Company filter
    if filters.company_slug:
        conditions.append(Company.slug == filters.company_slug)
    
    # Skills filter (JSONB contains)
    if filters.skills:
        for skill in filters.skills:
            # Case-insensitive skill matching in JSONB array
            conditions.append(
                func.lower(func.cast(Job.skills, String)).contains(skill.lower())
            )
    
    # Search query (title and description)
    if filters.q:
        search_term = f"%{filters.q}%"
        conditions.append(
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term),
            )
        )
    
    # Apply all conditions
    query = query.where(*conditions)
    
    # Get total count
    count_query = select(func.count()).select_from(Job).join(Company).outerjoin(Location).join(JobCategory).outerjoin(JobSubCategory).where(*conditions)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Apply sorting
    sort_clauses = build_sort_clause(sort.sort)
    if isinstance(sort_clauses, tuple):
        query = query.order_by(*sort_clauses)
    else:
        query = query.order_by(sort_clauses)
    
    # Apply pagination
    query = query.offset(pagination.offset).limit(pagination.limit)
    
    # Execute query
    result = await db.execute(query)
    rows = result.all()
    
    # Transform results
    jobs = []
    for row in rows:
        job = row[0]  # Job model instance
        jobs.append({
            'id': job.id,
            'title': job.title,
            'slug': job.slug,
            'job_type': job.job_type,
            'is_remote': job.is_remote,
            'salary': job.salary,
            'experience': job.experience,
            'skills': job.skills,
            'posted_date': job.posted_date,
            'company_name': row.company_name,
            'company_slug': row.company_slug,
            'company_logo_url': row.company_logo_url,
            'location_city': row.location_city,
            'location_state': row.location_state,
            'category_name': row.category_name,
            'category_slug': row.category_slug,
        })
    
    return jobs, total


async def get_job_by_slug(db: AsyncSession, slug: str) -> Optional[dict]:
    """
    Get job detail by slug.
    
    Args:
        db: Database session
        slug: Job slug
        
    Returns:
        Job detail dict or None if not found
    """
    today = date.today()
    
    query = (
        select(
            Job,
            Company,
            Location,
            JobCategory.name.label('category_name'),
            JobCategory.slug.label('category_slug'),
            JobSubCategory.name.label('subcategory_name'),
            JobSubCategory.slug.label('subcategory_slug'),
        )
        .join(Company, Job.company_id == Company.id)
        .outerjoin(Location, Job.location_id == Location.id)
        .join(JobCategory, Job.category_id == JobCategory.id)
        .outerjoin(JobSubCategory, Job.subcategory_id == JobSubCategory.id)
        .where(
            Job.slug == slug,
            Job.is_active == True,
            or_(Job.end_date.is_(None), Job.end_date >= today)
        )
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        return None
    
    job = row[0]
    company = row[1]
    location = row[2]
    
    return {
        'id': job.id,
        'title': job.title,
        'slug': job.slug,
        'job_type': job.job_type,
        'is_remote': job.is_remote,
        'salary': job.salary,
        'experience': job.experience,
        'skills': job.skills,
        'description': job.description,
        'job_url': job.job_url,
        'posted_date': job.posted_date,
        'end_date': job.end_date,
        'view_count': job.view_count,
        'is_active': job.is_active,
        'created_at': job.created_at,
        'updated_at': job.updated_at,
        'company': {
            'id': company.id,
            'name': company.name,
            'slug': company.slug,
            'logo_url': company.logo_url,
            'is_verified': company.is_verified,
        },
        'location': {
            'id': location.id,
            'city': location.city,
            'state': location.state,
            'slug': location.slug,
        } if location else None,
        'category_name': row.category_name,
        'category_slug': row.category_slug,
        'subcategory_name': row.subcategory_name,
        'subcategory_slug': row.subcategory_slug,
    }


async def increment_job_view_count(db: AsyncSession, job_id) -> None:
    """Increment view count for a job."""
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.view_count += 1
            await db.commit()
    except Exception as e:
        logger.error(f"Error incrementing view count for job {job_id}: {str(e)}")
        await db.rollback()


# Import String for JSONB casting
from sqlalchemy import String
