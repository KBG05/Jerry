"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/blankpoint",
        description="Async PostgreSQL database URL",
    )
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="blankpoint")

    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_title: str = Field(default="BlankPoint API")
    api_version: str = Field(default="1.0.0")
    api_description: str = Field(
        default="FastAPI backend with async SQLAlchemy and PostgreSQL"
    )

    # CORS Configuration
    cors_origins: str = Field(default="*", description="Comma-separated origins or '*'")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # Rate Limiting
    rate_limit_per_minute: str = Field(
        default="100/minute", description="Rate limit format: count/period"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", description="json or text")

    # Uvicorn Configuration
    workers_count: int = Field(default=1)
    reload: bool = Field(default=False)

    # Encryption
    encryption_key: str = Field(default="", description="Fernet encryption key for sensitive data")

    # GitHub OAuth
    github_client_id: str = Field(default="", description="GitHub OAuth Client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth Client Secret")
    github_callback_url: str = Field(
        default="http://localhost:8000/api/v1/auth/github/callback",
        description="GitHub OAuth callback URL"
    )

    # Frontend
    frontend_callback_url: str = Field(
        default="http://localhost:3000/onboarding/callback",
        description="Frontend callback URL after OAuth"
    )

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)."""
        return self.database_url.replace("+asyncpg", "").replace("postgresql://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
