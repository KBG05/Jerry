"""Jerry Auth schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class JerryAuthBase(BaseModel):
    """Base Jerry Auth schema."""

    github_access_token: str = Field(..., max_length=255)
    scholar_id: Optional[str] = Field(None, max_length=255)


class JerryAuthCreate(JerryAuthBase):
    """Schema for creating Jerry Auth."""

    user_id: uuid.UUID


class JerryAuthUpdate(BaseModel):
    """Schema for updating Jerry Auth."""

    github_access_token: Optional[str] = Field(None, max_length=255)
    scholar_id: Optional[str] = Field(None, max_length=255)


class JerryAuthResponse(JerryAuthBase):
    """Schema for Jerry Auth response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: uuid.UUID
    last_updated_at: datetime
