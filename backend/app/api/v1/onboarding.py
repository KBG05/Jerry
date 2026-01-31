"""Onboarding API endpoints."""

import uuid
import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse
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
from app.services.r2_service import upload_resume, delete_resume, get_resume_presigned_url, R2ServiceError
from app.utils.file_validation import validate_pdf_file
from app.core.config import get_settings
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
    response_class=RedirectResponse,
    summary="Get GitHub OAuth URL",
)
async def get_github_oauth_url(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Redirect user to GitHub OAuth authorization page.
    
    User will be redirected to GitHub to authorize access.
    After authorization, GitHub will redirect back to the callback URL.
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UserNotFoundException(str(user_id))
    
    # Generate GitHub auth URL with user_id as state
    auth_url = await get_github_auth_url(state=str(user_id))
    
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/{user_id}/complete-onboarding",
    response_model=OnboardingCompleteResponse,
    summary="Step 2: Complete onboarding",
)
async def complete_onboarding(
    user_id: uuid.UUID,
    resume: UploadFile = File(..., description="Resume PDF file (required, max 2MB)"),
    is_remote_only: bool = Form(...),
    preferred_locations: str = Form(..., description="JSON array of preferred locations"),
    role_categories: str = Form(..., description="JSON array of role category IDs"),
    scholar_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Complete user onboarding (Step 2).
    
    - Uploads resume (required, PDF, max 2MB)
    - Sets user preferences (required)
    - Optionally adds scholar_id
    - GitHub required only for tech roles (configurable via env)
    """
    settings = get_settings()
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UserNotFoundException(str(user_id))
    
    # Parse JSON arrays from form data
    try:
        preferred_locations_list = json.loads(preferred_locations)
        role_categories_list = json.loads(role_categories)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format: {str(e)}"
        )
    
    # Validate using schema
    try:
        validated_data = OnboardingStep2Request(
            resume=resume,
            is_remote_only=is_remote_only,
            preferred_locations=preferred_locations_list,
            role_categories=role_categories_list,
            scholar_id=scholar_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid onboarding data: {str(e)}"
        )
    
    # Check if GitHub is required for selected role categories
    github_required_cats = set(settings.github_required_categories)
    selected_cats = set(validated_data.role_categories)
    github_required = bool(github_required_cats & selected_cats)
    
    # Verify GitHub OAuth if required for selected roles
    auth = None
    if github_required:
        result = await db.execute(select(JerryAuth).where(JerryAuth.user_id == user_id))
        auth = result.scalar_one_or_none()
        
        if not auth or not auth.github_access_token:
            raise OnboardingIncompleteException(
                "GitHub OAuth is required for the selected role categories. Please connect your GitHub account first."
            )
    else:
        # GitHub optional - check if exists
        result = await db.execute(select(JerryAuth).where(JerryAuth.user_id == user_id))
        auth = result.scalar_one_or_none()
    
    # Update scholar_id if provided and auth exists
    if validated_data.scholar_id and auth:
        auth.scholar_id = validated_data.scholar_id
        await db.commit()
        await db.refresh(auth)
    
    # Validate resume file
    await validate_pdf_file(validated_data.resume)
    
    # Check if preferences already exist
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()
    
    try:
        # Upload resume to R2
        resume_path = await upload_resume(user_id, validated_data.resume)
        
        if preferences:
            # Update existing preferences
            preferences.is_remote_only = validated_data.is_remote_only
            preferences.preferred_locations = validated_data.preferred_locations
            preferences.role_categories = validated_data.role_categories
            preferences.resume_path = resume_path
            preferences.resume_uploaded_at = datetime.utcnow()
        else:
            # Create new preferences
            preferences = UserPreferences(
                user_id=user_id,
                is_remote_only=validated_data.is_remote_only,
                preferred_locations=validated_data.preferred_locations,
                role_categories=validated_data.role_categories,
                resume_path=resume_path,
                resume_uploaded_at=datetime.utcnow(),
            )
            db.add(preferences)
        
        await db.commit()
        await db.refresh(preferences)
        
        logger.info(f"Onboarding completed for user: {user_id}")
        
        return {
            "user": user,
            "auth": auth,
            "preferences": preferences,
            "has_resume": True,
            "message": "Onboarding completed successfully"
        }
        
    except R2ServiceError as e:
        logger.error(f"R2 upload failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume: {str(e)}"
        )


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
    
    github_connected = auth is not None and auth.github_access_token is not None
    
    # Check preferences
    preferences = None
    resume_uploaded = False
    if user:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()
        if preferences:
            resume_uploaded = preferences.resume_path is not None
    
    step2_completed = preferences is not None and resume_uploaded
    
    return {
        "step1_completed": step1_completed,
        "github_connected": github_connected,
        "step2_completed": step2_completed,
        "resume_uploaded": resume_uploaded,
        "user": user,
        "auth": auth,
        "preferences": preferences,
    }


@router.get(
    "/{user_id}/resume",
    summary="Get resume download URL",
)
async def get_resume_url(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get pre-signed URL for downloading user's resume.
    
    Returns a temporary URL that expires after configured time (default 15 minutes).
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UserNotFoundException(str(user_id))
    
    # Check if preferences exist with resume
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()
    
    if not preferences or not preferences.resume_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found for this user"
        )
    
    try:
        # Generate pre-signed URL
        download_url = get_resume_presigned_url(user_id)
        
        return {
            "download_url": download_url,
            "resume_path": preferences.resume_path,
            "uploaded_at": preferences.resume_uploaded_at,
            "expires_in": get_settings().r2_presigned_url_expiry,
        }
        
    except R2ServiceError as e:
        logger.error(f"Failed to generate resume URL for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.delete(
    "/{user_id}/resume",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user's resume",
)
async def delete_user_resume(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user's resume from storage and database.
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UserNotFoundException(str(user_id))
    
    # Check if preferences exist with resume
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()
    
    if not preferences or not preferences.resume_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found for this user"
        )
    
    try:
        # Delete from R2
        delete_resume(user_id)
        
        # Update database
        preferences.resume_path = None
        preferences.resume_uploaded_at = None
        await db.commit()
        
        logger.info(f"Resume deleted for user: {user_id}")
        
    except R2ServiceError as e:
        logger.error(f"Failed to delete resume for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(e)}"
        )
