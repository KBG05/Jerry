"""User Preferences schemas."""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class UserPreferencesBase(BaseModel):
    """Base User Preferences schema."""

    is_remote_only: bool = Field(default=False)
    preferred_locations: Optional[List[str]] = None
    role_categories: Optional[List[str]] = None


class UserPreferencesCreate(UserPreferencesBase):
    """Schema for creating User Preferences."""

    user_id: uuid.UUID


class UserPreferencesUpdate(BaseModel):
    """Schema for updating User Preferences."""

    is_remote_only: Optional[bool] = None
    preferred_locations: Optional[List[str]] = None
    role_categories: Optional[List[str]] = None


class UserPreferencesResponse(UserPreferencesBase):
    """Schema for User Preferences response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: uuid.UUID
    resume_path: Optional[str] = None
    resume_uploaded_at: Optional[datetime] = None

    @property
    def has_resume(self) -> bool:
        """Check if user has uploaded a resume."""
        return self.resume_path is not None
