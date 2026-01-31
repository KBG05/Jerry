"""Onboarding API endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User, JerryAuth, UserPreferences
from app.schemas.user import UserCreate, UserResponse
from app.schemas.onboarding import (
    OnboardingStep2Request,
    OnboardingCompleteResponse,
    OnboardingStatusResponse,
    GitHubAuthUrlResponse,
)
from app.exceptions import (
    UserNotFoundException,
    OnboardingIncompleteException,
    DuplicateUserException,
)
from app.services.github_service import get_github_auth_url
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["onboarding"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 1: Register new user",
)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Register a new user (Onboarding Step 1).
    
    Creates a user account with basic information.
    After registration, proceed to GitHub OAuth connection.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise DuplicateUserException("email", user_data.email)
    
    # Create new user
    new_user = User(**user_data.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"User registered successfully: {new_user.id}")
    return new_user


@router.get(
    "/{user_id}/github/auth-url",
    response_model=GitHubAuthUrlResponse,
    summary="Get GitHub OAuth URL",
)
async def get_github_oauth_url(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get GitHub OAuth authorization URL for user.
    
    Frontend should redirect user to this URL to authorize GitHub access.
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UserNotFoundException(str(user_id))
    
    # Generate GitHub auth URL with user_id as state
    auth_url = await get_github_auth_url(state=str(user_id))
    
    return {
        "auth_url": auth_url,
        "state": str(user_id),
        "message": "Redirect user to this URL to authorize GitHub access"
    }


@router.post(
    "/{user_id}/complete-onboarding",
    response_model=OnboardingCompleteResponse,
    summary="Step 2: Complete onboarding",
)
async def complete_onboarding(
    user_id: uuid.UUID,
    onboarding_data: OnboardingStep2Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Complete user onboarding (Step 2).
    
    - Sets user preferences
    - Optionally adds scholar_id
    - Requires GitHub OAuth to be completed first
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UserNotFoundException(str(user_id))
    
    # Verify GitHub OAuth is completed
    result = await db.execute(select(JerryAuth).where(JerryAuth.user_id == user_id))
    auth = result.scalar_one_or_none()
    
    if not auth:
        raise OnboardingIncompleteException(
            "GitHub OAuth not completed. Please connect your GitHub account first."
        )
    
    # Update scholar_id if provided
    if onboarding_data.scholar_id:
        auth.scholar_id = onboarding_data.scholar_id
        await db.commit()
        await db.refresh(auth)
    
    # Check if preferences already exist
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()
    
    if preferences:
        # Update existing preferences
        preferences.is_remote_only = onboarding_data.is_remote_only
        preferences.preferred_locations = onboarding_data.preferred_locations
        preferences.role_categories = onboarding_data.role_categories
    else:
        # Create new preferences
        preferences = UserPreferences(
            user_id=user_id,
            is_remote_only=onboarding_data.is_remote_only,
            preferred_locations=onboarding_data.preferred_locations,
            role_categories=onboarding_data.role_categories,
        )
        db.add(preferences)
    
    await db.commit()
    await db.refresh(preferences)
    
    logger.info(f"Onboarding completed for user: {user_id}")
    
    return {
        "user": user,
        "auth": auth,
        "preferences": preferences,
        "message": "Onboarding completed successfully"
    }


@router.get(
    "/{user_id}/onboarding-status",
    response_model=OnboardingStatusResponse,
    summary="Get onboarding status",
)
async def get_onboarding_status(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get current onboarding status for a user.
    
    Shows which steps are completed and provides relevant data.
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    step1_completed = user is not None
    
    # Check GitHub OAuth
    auth = None
    if user:
        result = await db.execute(select(JerryAuth).where(JerryAuth.user_id == user_id))
        auth = result.scalar_one_or_none()
    
    github_connected = auth is not None
    
    # Check preferences
    preferences = None
    if user:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()
    
    step2_completed = preferences is not None
    
    return {
        "step1_completed": step1_completed,
        "github_connected": github_connected,
        "step2_completed": step2_completed,
        "user": user,
        "auth": auth,
        "preferences": preferences,
    }
