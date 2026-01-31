"""Rate limiting middleware using SlowAPI."""

from typing import Union

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key from request.
    Uses client IP address as the key.
    """
    client_ip = get_remote_address(request)
    logger.debug(f"Rate limit key generated for IP: {client_ip}")
    return client_ip


# Initialize rate limiter
settings = get_settings()
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[settings.rate_limit_per_minute],
    storage_uri="memory://",  # In-memory storage (use Redis for distributed systems)
)


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Custom handler for rate limit exceeded errors."""
    client_ip = get_remote_address(request)
    
    logger.warning(
        f"Rate limit exceeded for {request.method} {request.url.path}",
        extra={
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
        },
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc),
        },
    )
