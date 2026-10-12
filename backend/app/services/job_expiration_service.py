"""Job expiration service for deactivating expired jobs."""

from datetime import date
from typing import Optional

from sqlalchemy import update, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Job
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def deactivate_expired_jobs(db: AsyncSession) -> int:
    """
    Deactivate all jobs that have passed their end_date.
    
    CURRENTLY DISABLED: end_date is now a string field, not a date.
    Date comparison logic needs to be reimplemented if expiration is needed.
    
    Args:
        db: Async database session
        
    Returns:
        Number of jobs deactivated (always 0 for now)
    """
    logger.info("Job expiration check disabled - end_date is a string field")
    return 0
    
    # TODO: Implement string-based date comparison if needed
    # today = date.today()
    # try:
    #     # Parse end_date strings and compare
    #     pass
    # except Exception as e:
    #     logger.error(f"Error deactivating expired jobs: {str(e)}")
    #     await db.rollback()
    #     raise


async def get_expiring_jobs_count(db: AsyncSession, days: int = 7) -> int:
    """
    Get count of jobs expiring within the next N days.
    
    CURRENTLY DISABLED: end_date is now a string field, not a date.
    
    Args:
        db: Async database session
        days: Number of days to look ahead (default 7)
        
    Returns:
        Number of jobs expiring within the specified period (always 0 for now)
    """
    logger.info("Expiring jobs count disabled - end_date is a string field")
    return 0


async def deactivate_job(db: AsyncSession, job_id) -> bool:
    """
    Manually deactivate a single job.
    
    Args:
        db: Async database session
        job_id: UUID of the job to deactivate
        
    Returns:
        True if job was deactivated, False if job not found
    """
    try:
        result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            logger.warning(f"Job not found for deactivation: {job_id}")
            return False
        
        if not job.is_active:
            logger.info(f"Job already inactive: {job_id}")
            return True
        
        job.is_active = False
        # job.end_date = date.today()
        await db.commit()
        
        logger.info(f"Manually deactivated job: {job_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deactivating job {job_id}: {str(e)}")
        await db.rollback()
        raise


async def bulk_deactivate_jobs(
    db: AsyncSession, 
    job_ids: Optional[list] = None,
    company_id: Optional[str] = None,
    category_id: Optional[int] = None
) -> int:
    """
    Bulk deactivate jobs by IDs or filters.
    
    Args:
        db: Async database session
        job_ids: Optional list of job UUIDs to deactivate
        company_id: Optional company UUID to deactivate all jobs for
        category_id: Optional category ID to deactivate all jobs for
        
    Returns:
        Number of jobs deactivated
    """
    try:
        # Build base query
        conditions = [Job.is_active == True]
        
        if job_ids:
            conditions.append(Job.id.in_(job_ids))
        if company_id:
            conditions.append(Job.company_id == company_id)
        if category_id:
            conditions.append(Job.category_id == category_id)
        
        # Count affected jobs
        count_query = select(func.count()).select_from(Job).where(*conditions)
        result = await db.execute(count_query)
        affected_count = result.scalar() or 0
        
        if affected_count == 0:
            logger.info("No jobs found matching bulk deactivation criteria")
            return 0
        
        # Perform bulk update
        update_query = (
            update(Job)
            .where(*conditions)
            .values(is_active=False, end_date=date.today())
        )
        await db.execute(update_query)
        await db.commit()
        
        logger.info(f"Bulk deactivated {affected_count} jobs")
        return affected_count
        
    except Exception as e:
        logger.error(f"Error in bulk job deactivation: {str(e)}")
        await db.rollback()
        raise
