"""Database models."""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


class JerryAuth(Base):
    """Jerry authentication model."""

    __tablename__ = "jerry_auth"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True, 
        index=True
    )
    github_access_token: Mapped[str] = mapped_column(String(255), nullable=False)
    scholar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation of JerryAuth."""
        return f"<JerryAuth(user_id={self.user_id}, scholar_id={self.scholar_id})>"


class UserPreferences(Base):
    """User preferences model."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True, 
        index=True
    )
    is_remote_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_locations: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)
    role_categories: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        """String representation of UserPreferences."""
        return f"<UserPreferences(user_id={self.user_id}, is_remote_only={self.is_remote_only})>"
