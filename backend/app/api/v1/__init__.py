"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import onboarding, github_auth, job_categories, jobs, locations, companies

api_router = APIRouter(prefix="/v1")

# Include all v1 routers
api_router.include_router(onboarding.router)
api_router.include_router(github_auth.router)
api_router.include_router(job_categories.router)
api_router.include_router(jobs.router)
api_router.include_router(locations.router)
api_router.include_router(companies.router)

# Include admin routers
api_router.include_router(jobs.admin_router)
api_router.include_router(locations.admin_router)
api_router.include_router(companies.admin_router)
