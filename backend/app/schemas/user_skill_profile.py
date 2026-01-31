"""User Skill Profile schemas."""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class UserSkillProfileBase(BaseModel):
    """Base User Skill Profile schema."""

    skills: Optional[List[str]] = Field(default=None, description="List of user skills")
    description: Optional[str] = Field(default=None, description="User profile description")


class UserSkillProfileCreate(UserSkillProfileBase):
    """Schema for creating User Skill Profile."""

    user_id: uuid.UUID


class UserSkillProfileUpdate(BaseModel):
    """Schema for updating User Skill Profile."""

    skills: Optional[List[str]] = None
    description: Optional[str] = None


class UserSkillProfileResponse(UserSkillProfileBase):
    """Schema for User Skill Profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
