"""User schemas."""

import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base User schema."""

    name: str = Field(..., min_length=1, max_length=32)
    phone_number: str = Field(..., max_length=20)
    email: EmailStr
    gender: str = Field(..., max_length=10)
    dob: date
    location: str = Field(..., max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: Optional[str] = Field(None, min_length=1, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    gender: Optional[str] = Field(None, max_length=10)
    dob: Optional[date] = None
    location: Optional[str] = Field(None, max_length=255)


class UserResponse(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
