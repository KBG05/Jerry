"""Scheduler service for background tasks."""

import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.database import get_session_factory
from app.services.job_expiration_service import deactivate_expired_jobs, get_expiring_jobs_count

logger = get_logger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def cleanup_expired_jobs_task():
    """
    Scheduled task to cleanup expired jobs.
    
    Runs daily at configured time (default: 00:00 UTC).
    """
    logger.info("Starting scheduled job cleanup task")
    
    try:
        session_factory = get_session_factory()
        async with session_factory() as db:
            # Deactivate expired jobs
            deactivated_count = await deactivate_expired_jobs(db)
            logger.info(f"Scheduled cleanup completed: {deactivated_count} jobs deactivated")
            
            # Check for jobs expiring soon (next 7 days)
            expiring_soon = await get_expiring_jobs_count(db, days=7)
            if expiring_soon > 0:
                logger.info(f"Jobs expiring in next 7 days: {expiring_soon}")
                
    except Exception as e:
        logger.error(f"Error in scheduled job cleanup task: {str(e)}")


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def start_scheduler():
    """
    Initialize and start the background scheduler.
    
    Schedules:
    - Job cleanup: Daily at configured hour (default: 00:00 UTC)
    """
    global _scheduler
    
    settings = get_settings()
    
    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled via configuration")
        return
    
    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    try:
        _scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        
        # Add job cleanup task
        _scheduler.add_job(
            cleanup_expired_jobs_task,
            CronTrigger(
                hour=settings.job_cleanup_hour,
                minute=0,
                timezone=settings.scheduler_timezone
            ),
            id="cleanup_expired_jobs",
            name="Cleanup Expired Jobs",
            replace_existing=True,
        )
        
        _scheduler.start()
        logger.info(
            f"Scheduler started. Job cleanup scheduled at {settings.job_cleanup_hour}:00 "
            f"{settings.scheduler_timezone}"
        )
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
        _scheduler = None
        raise


def shutdown_scheduler():
    """Shutdown the background scheduler gracefully."""
    global _scheduler
    
    if _scheduler is None:
        logger.info("Scheduler not running, nothing to shutdown")
        return
    
    try:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")
    finally:
        _scheduler = None


async def run_cleanup_now() -> int:
    """
    Manually trigger job cleanup (for admin endpoint).
    
    Returns:
        Number of jobs deactivated
    """
    logger.info("Manual job cleanup triggered")
    
    try:
        session_factory = get_session_factory()
        async with session_factory() as db:
            deactivated_count = await deactivate_expired_jobs(db)
            logger.info(f"Manual cleanup completed: {deactivated_count} jobs deactivated")
            return deactivated_count
            
    except Exception as e:
        logger.error(f"Error in manual job cleanup: {str(e)}")
        raise
