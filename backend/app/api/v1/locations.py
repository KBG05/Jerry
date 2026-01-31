"""Locations API endpoints."""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Location
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.pagination import PaginationParams, PaginatedResponse
from app.utils.slug import generate_location_slug, generate_unique_slug
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/locations", tags=["locations"])


@router.get(
    "",
    response_model=PaginatedResponse[LocationResponse],
    summary="List all locations",
)
async def list_locations(
    search: Optional[str] = Query(None, max_length=100, description="Search by city or state"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all locations with optional search and pagination."""
    query = select(Location)
    count_query = select(func.count()).select_from(Location)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Location.city.ilike(search_term)) | (Location.state.ilike(search_term))
        )
        count_query = count_query.where(
            (Location.city.ilike(search_term)) | (Location.state.ilike(search_term))
        )
    
    # Get total count
    result = await db.execute(count_query)
    total = result.scalar() or 0
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(Location.city).offset(offset).limit(limit)
    
    result = await db.execute(query)
    locations = result.scalars().all()
    
    return PaginatedResponse.create(
        items=locations, #type: ignore
        total=total,
        page=page,
        page_size=limit,
    )


@router.get(
    "/{slug}",
    response_model=LocationResponse,
    summary="Get location by slug",
)
async def get_location_by_slug(
    slug: str = Path(..., description="Location slug (e.g., san-francisco-ca)"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific location by its slug."""
    result = await db.execute(
        select(Location).where(Location.slug == slug)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location not found: {slug}"
        )
    
    return location


# Admin endpoints
admin_router = APIRouter(prefix="/admin/locations", tags=["admin-locations"])


@admin_router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new location",
)
async def create_location(
    location_data: LocationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new location."""
    # Generate slug
    slug = generate_location_slug(location_data.city, location_data.state)
    
    # Check if slug already exists
    result = await db.execute(
        select(Location).where(Location.slug == slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location with slug '{slug}' already exists"
        )
    
    location = Location(
        city=location_data.city,
        state=location_data.state,
        slug=slug,
        count=0,
    )
    db.add(location)
    await db.commit()
    await db.refresh(location)
    
    logger.info(f"Created location: {location.city}, {location.state}")
    return location


@admin_router.put(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Update a location",
)
async def update_location(
    location_id: int = Path(..., description="Location ID"),
    location_data: LocationUpdate = None,#type: ignore
    db: AsyncSession = Depends(get_db),
):
    """Update an existing location."""
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Update fields if provided
    if location_data.city is not None:
        location.city = location_data.city
    if location_data.state is not None:
        location.state = location_data.state
    
    # Regenerate slug if city or state changed
    if location_data.city is not None or location_data.state is not None:
        new_slug = generate_location_slug(location.city, location.state)
        # Check if new slug conflicts with another location
        result = await db.execute(
            select(Location).where(
                Location.slug == new_slug,
                Location.id != location_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with slug '{new_slug}' already exists"
            )
        location.slug = new_slug
    
    await db.commit()
    await db.refresh(location)
    
    logger.info(f"Updated location: {location.city}, {location.state}")
    return location


@admin_router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a location",
)
async def delete_location(
    location_id: int = Path(..., description="Location ID"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a location."""
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    await db.delete(location)
    await db.commit()
    
    logger.info(f"Deleted location: {location.city}, {location.state}")


@admin_router.post(
    "/bulk",
    response_model=dict,
    summary="Bulk create locations",
)
async def bulk_create_locations(
    locations: List[LocationCreate],
    db: AsyncSession = Depends(get_db),
):
    """Bulk create locations (skip existing)."""
    created = 0
    skipped = 0
    
    for loc_data in locations:
        slug = generate_location_slug(loc_data.city, loc_data.state)
        
        # Check if exists
        result = await db.execute(
            select(Location).where(Location.slug == slug)
        )
        if result.scalar_one_or_none():
            skipped += 1
            continue
        
        location = Location(
            city=loc_data.city,
            state=loc_data.state,
            slug=slug,
            count=0,
        )
        db.add(location)
        created += 1
    
    await db.commit()
    
    logger.info(f"Bulk created {created} locations, skipped {skipped}")
    return {"created": created, "skipped": skipped}
