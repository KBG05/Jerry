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
    
    This function finds all active jobs where end_date is not null and
    has passed, then sets is_active=False for those jobs.
    
    Args:
        db: Async database session
        
    Returns:
        Number of jobs deactivated
    """
    today = date.today()
    
    try:
        # First, count how many jobs will be affected
        count_query = select(func.count()).select_from(Job).where(
            Job.is_active == True,
            Job.end_date.isnot(None),
            Job.end_date < today
        )
        result = await db.execute(count_query)
        expired_count = result.scalar() or 0
        
        if expired_count == 0:
            logger.info("No expired jobs found to deactivate")
            return 0
        
        # Perform bulk update to deactivate expired jobs
        update_query = (
            update(Job)
            .where(
                Job.is_active == True,
                Job.end_date.isnot(None),
                Job.end_date < today
            )
            .values(is_active=False)
        )
        await db.execute(update_query)
        await db.commit()
        
        logger.info(f"Deactivated {expired_count} expired jobs")
        
        # Log warning for large batches
        if expired_count > 50:
            logger.warning(f"Large batch of jobs deactivated: {expired_count} jobs expired today")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"Error deactivating expired jobs: {str(e)}")
        await db.rollback()
        raise


async def get_expiring_jobs_count(db: AsyncSession, days: int = 7) -> int:
    """
    Get count of jobs expiring within the next N days.
    
    Useful for sending alerts about upcoming expirations.
    
    Args:
        db: Async database session
        days: Number of days to look ahead (default 7)
        
    Returns:
        Number of jobs expiring within the specified period
    """
    from datetime import timedelta
    
    today = date.today()
    future_date = today + timedelta(days=days)
    
    try:
        count_query = select(func.count()).select_from(Job).where(
            Job.is_active == True,
            Job.end_date.isnot(None),
            Job.end_date >= today,
            Job.end_date <= future_date
        )
        result = await db.execute(count_query)
        return result.scalar() or 0
        
    except Exception as e:
        logger.error(f"Error counting expiring jobs: {str(e)}")
        raise


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
        job.end_date = date.today()
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
