"""Database models."""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, Date, Boolean, Integer, ForeignKey, func, text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


__all__ = [
    "User", 
    "JerryAuth", 
    "UserPreferences", 
    "JobCategory", 
    "JobSubCategory",
    "Location",
    "Company",
    "Job",
]


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
    github_access_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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
    resume_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resume_uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        """String representation of UserPreferences."""
        return f"<UserPreferences(user_id={self.user_id}, is_remote_only={self.is_remote_only})>"


class JobCategory(Base):
    """Job category model."""

    __tablename__ = "job_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        """String representation of JobCategory."""
        return f"<JobCategory(id={self.id}, name='{self.name}', slug='{self.slug}', count={self.count})>"


class JobSubCategory(Base):
    """Job sub-category model."""

    __tablename__ = "job_sub_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        """String representation of JobSubCategory."""
        return f"<JobSubCategory(id={self.id}, category_id={self.category_id}, name='{self.name}', slug='{self.slug}', count={self.count})>"


class Location(Base):
    """Location model for job locations."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        """String representation of Location."""
        return f"<Location(id={self.id}, city='{self.city}', state='{self.state}', slug='{self.slug}')>"


class Company(Base):
    """Company model for job companies (scraped data)."""

    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint('name', 'website', name='uq_company_name_website'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation of Company."""
        return f"<Company(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Job(Base):
    """Job model for job listings (scraped data)."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index('idx_job_active_end_date', 'is_active', 'end_date'),
        Index('idx_job_filters', 'is_active', 'category_id', 'is_remote', 'posted_date'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("job_sub_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # fulltime, contract, internship
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    salary: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Scraped text as-is
    experience: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Scraped text as-is
    skills: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)  # List of skill strings
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[Optional[List]] = mapped_column(JSONB, nullable=True)
    job_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posted_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation of Job."""
        return f"<Job(id={self.id}, title='{self.title}', slug='{self.slug}', is_active={self.is_active})>"
