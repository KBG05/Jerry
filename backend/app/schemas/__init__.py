"""Schemas module initialization."""

from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.jerry_auth import JerryAuthCreate, JerryAuthUpdate, JerryAuthResponse
from app.schemas.user_preferences import (
    UserPreferencesCreate,
    UserPreferencesUpdate,
    UserPreferencesResponse,
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "JerryAuthCreate",
    "JerryAuthUpdate",
    "JerryAuthResponse",
    "UserPreferencesCreate",
    "UserPreferencesUpdate",
    "UserPreferencesResponse",
]
