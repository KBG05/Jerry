"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api import api_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging, get_logger
from app.db import init_db, close_db
from app.middleware import RequestLoggingMiddleware, limiter, rate_limit_exceeded_handler
from app.services.scheduler import start_scheduler, shutdown_scheduler

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting application...")
    logger.info(f"Initializing database connection: {settings.database_url.split('@')[-1]}")
    await init_db()
    
    # Start scheduler
    try:
        start_scheduler()
        logger.info("Background scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Shutdown scheduler
    try:
        shutdown_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
    
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add rate limiter state
app.state.limiter = limiter

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    summary="Health check endpoint",
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {
        "status": "healthy",
        "service": settings.api_title,
        "version": settings.api_version,
    }


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="Root endpoint",
)
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": f"Welcome to {settings.api_title}",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }


# Include API routers
app.include_router(api_router, prefix="/api")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "method": request.method,
            "path": request.url.path,
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        workers=settings.workers_count,
        log_level=settings.log_level.lower(),
    )
