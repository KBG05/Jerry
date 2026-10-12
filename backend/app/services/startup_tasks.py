"""Startup tasks for job matching and eligibility."""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.db import get_db
from app.models.models import User, UserSkillProfile, UserEligibleJob
from app.services.stratos_service import get_stratos_service

logger = get_logger(__name__)


async def sync_user_eligible_jobs():
    """
    Sync eligible jobs for all users with skill profiles.
    
    This function:
    1. Fetches all users with skill profiles
    2. For each user, queries Stratos API for job recommendations
    3. Clears existing eligible jobs for the user
    4. Inserts new eligible jobs based on Stratos recommendations
    """
    logger.info("Starting user eligible jobs sync...")
    
    stratos_service = get_stratos_service()
    
    try:
        async for db in get_db():
            # Get all users with skill profiles
            result = await db.execute(
                select(User.id, UserSkillProfile.skills, UserSkillProfile.description)
                .join(UserSkillProfile, User.id == UserSkillProfile.user_id)
                .where(UserSkillProfile.skills.isnot(None))  # Only users with skills
            )
            
            users_with_profiles = result.all()
            
            if not users_with_profiles:
                logger.info("No users with skill profiles found")
                return
            
            logger.info(f"Found {len(users_with_profiles)} users with skill profiles")
            
            total_jobs_assigned = 0
            successful_users = 0
            
            for user_id, skills, description in users_with_profiles:
                try:
                    # Skip if no skills
                    if not skills:
                        logger.warning(f"User {user_id} has empty skills list, skipping")
                        continue
                    
                    # Use description or empty string
                    user_desc = description or ""
                    
                    logger.info(f"Processing user {user_id} with {len(skills)} skills")
                    
                    # Get job recommendations from Stratos
                    job_ids = await stratos_service.get_all_job_recommendations_paginated(
                        skills=skills,
                        description=user_desc,
                        top_k=100,
                        max_results=100
                    )
                    
                    if not job_ids:
                        logger.warning(f"No job recommendations found for user {user_id}")
                        continue
                    
                    logger.info(f"Found {len(job_ids)} job recommendations for user {user_id}")
                    
                    # Delete existing eligible jobs for this user
                    await db.execute(
                        delete(UserEligibleJob).where(UserEligibleJob.user_id == user_id)
                    )
                    
                    # Insert new eligible jobs
                    for job_id in job_ids:
                        eligible_job = UserEligibleJob(
                            user_id=user_id,
                            job_id=job_id,
                            match_score=None  # Stratos doesn't provide score yet
                        )
                        db.add(eligible_job)
                    
                    await db.commit()
                    
                    total_jobs_assigned += len(job_ids)
                    successful_users += 1
                    
                    logger.info(f"Successfully assigned {len(job_ids)} jobs to user {user_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing user {user_id}: {str(e)}")
                    await db.rollback()
                    continue
            
            logger.info(
                f"User eligible jobs sync complete. "
                f"Processed {successful_users}/{len(users_with_profiles)} users, "
                f"assigned {total_jobs_assigned} total job matches"
            )
            
    except Exception as e:
        logger.error(f"Critical error during user eligible jobs sync: {str(e)}")
        raise
