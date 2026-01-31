"""Location schemas."""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    """Base Location schema."""

    city: str = Field(..., max_length=100, description="City name")
    state: str = Field(..., max_length=100, description="State name or abbreviation")


class LocationCreate(LocationBase):
    """Schema for creating a Location."""

    pass


class LocationUpdate(BaseModel):
    """Schema for updating a Location."""

    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


class LocationResponse(LocationBase):
    """Schema for Location response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    count: int = Field(default=0, description="Number of jobs in this location")
