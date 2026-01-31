"""Onboarding schemas."""

import uuid
from typing import Optional, List

from pydantic import BaseModel, Field
from fastapi import UploadFile

from app.schemas.user import UserResponse
from app.schemas.jerry_auth import JerryAuthResponse
from app.schemas.user_preferences import UserPreferencesResponse


class OnboardingStep2Request(BaseModel):
    """Request schema for completing onboarding step 2."""
    
    class Config:
        arbitrary_types_allowed = True

    resume: UploadFile = Field(..., description="Resume PDF file (required, max 2MB)")
    is_remote_only: bool = Field(..., description="Whether user prefers remote-only positions")
    preferred_locations: List[str] = Field(..., description="List of preferred work locations")
    role_categories: List[int] = Field(..., description="List of preferred role category IDs")
    scholar_id: Optional[str] = Field(None, max_length=255, description="Google Scholar ID (optional)")


class GitHubAuthUrlResponse(BaseModel):
    """Response schema for GitHub auth URL."""

    auth_url: str = Field(..., description="GitHub OAuth authorization URL")
    state: str = Field(..., description="State parameter (user_id) for OAuth flow")
    message: str = Field(default="Redirect user to this URL to authorize GitHub access")


class OnboardingCompleteResponse(BaseModel):
    """Response schema for completed onboarding."""

    user: UserResponse
    auth: Optional[JerryAuthResponse] = None
    preferences: UserPreferencesResponse
    has_resume: bool = Field(..., description="Whether resume was uploaded")
    message: str = Field(default="Onboarding completed successfully")


class OnboardingStatusResponse(BaseModel):
    """Response schema for onboarding status check."""

    step1_completed: bool = Field(..., description="Whether user registration is complete")
    github_connected: bool = Field(..., description="Whether GitHub OAuth is connected")
    step2_completed: bool = Field(..., description="Whether preferences are set")
    resume_uploaded: bool = Field(..., description="Whether resume is uploaded")
    user: Optional[UserResponse] = Field(None, description="User data if exists")
    auth: Optional[JerryAuthResponse] = Field(None, description="Auth data if exists")
    preferences: Optional[UserPreferencesResponse] = Field(None, description="Preferences if exists")
