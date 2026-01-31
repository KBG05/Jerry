"""Companies API endpoints."""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Company, Location
from app.schemas.company import (
    CompanyCreate, 
    CompanyUpdate, 
    CompanyResponse, 
    CompanyListResponse,
    CompanyBulkUpsertRequest,
    CompanyBulkUpsertResponse,
)
from app.schemas.pagination import PaginationParams, PaginatedResponse
from app.utils.slug import generate_slug, generate_unique_slug
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/companies", tags=["companies"])


@router.get(
    "",
    response_model=PaginatedResponse[CompanyListResponse],
    summary="List all companies",
)
async def list_companies(
    search: Optional[str] = Query(None, max_length=255, description="Search by company name"),
    location_slug: Optional[str] = Query(None, max_length=255, description="Filter by location slug"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all companies with optional filters and pagination."""
    query = select(Company)
    count_query = select(func.count()).select_from(Company)
    conditions = []
    
    if search:
        search_term = f"%{search}%"
        conditions.append(Company.name.ilike(search_term))
    
    if location_slug:
        # Join with location
        query = query.join(Location, Company.location_id == Location.id)
        count_query = count_query.join(Location, Company.location_id == Location.id)
        conditions.append(Location.slug == location_slug)
    
    if is_verified is not None:
        conditions.append(Company.is_verified == is_verified)
    
    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)
    
    # Get total count
    result = await db.execute(count_query)
    total = result.scalar() or 0
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(Company.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    companies = result.scalars().all()
    
    return PaginatedResponse.create(
        items=companies, #type: ignore
        total=total,
        page=page,
        page_size=limit,
    )


@router.get(
    "/{slug}",
    response_model=CompanyResponse,
    summary="Get company by slug",
)
async def get_company_by_slug(
    slug: str = Path(..., description="Company slug"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific company by its slug."""
    result = await db.execute(
        select(Company).where(Company.slug == slug)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company not found: {slug}"
        )
    
    return company


# Admin endpoints
admin_router = APIRouter(prefix="/admin/companies", tags=["admin-companies"])


@admin_router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company",
)
async def create_company(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new company."""
    # Generate slug
    base_slug = generate_slug(company_data.name)
    
    # Check for unique slug
    async def slug_exists(slug: str) -> bool:
        result = await db.execute(
            select(Company).where(Company.slug == slug)
        )
        return result.scalar_one_or_none() is not None
    
    slug = await generate_unique_slug(company_data.name, slug_exists)
    
    company = Company(
        name=company_data.name,
        slug=slug,
        logo_url=company_data.logo_url,
        website=company_data.website,
        description=company_data.description,
        location_id=company_data.location_id,
        is_verified=company_data.is_verified,
        scraped_at=datetime.utcnow(),
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    
    logger.info(f"Created company: {company.name}")
    return company


@admin_router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Update a company",
)
async def update_company(
    company_id: uuid.UUID = Path(..., description="Company UUID"),
    company_data: CompanyUpdate = None,#type: ignore
    db: AsyncSession = Depends(get_db),
):
    """Update an existing company."""
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Update fields if provided
    if company_data.name is not None:
        company.name = company_data.name
        # Regenerate slug
        async def slug_exists(slug: str) -> bool:
            result = await db.execute(
                select(Company).where(
                    Company.slug == slug,
                    Company.id != company_id
                )
            )
            return result.scalar_one_or_none() is not None
        
        company.slug = await generate_unique_slug(company_data.name, slug_exists)
    
    if company_data.logo_url is not None:
        company.logo_url = company_data.logo_url
    if company_data.website is not None:
        company.website = company_data.website
    if company_data.description is not None:
        company.description = company_data.description
    if company_data.location_id is not None:
        company.location_id = company_data.location_id
    if company_data.is_verified is not None:
        company.is_verified = company_data.is_verified
    
    await db.commit()
    await db.refresh(company)
    
    logger.info(f"Updated company: {company.name}")
    return company


@admin_router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
)
async def delete_company(
    company_id: uuid.UUID = Path(..., description="Company UUID"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a company and all its jobs."""
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    await db.delete(company)
    await db.commit()
    
    logger.info(f"Deleted company: {company.name}")


@admin_router.post(
    "/bulk-upsert",
    response_model=CompanyBulkUpsertResponse,
    summary="Bulk upsert companies (for scraper)",
)
async def bulk_upsert_companies(
    request: CompanyBulkUpsertRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk create or update companies.
    
    Used by scraper to efficiently update company data.
    Upsert is based on (name, website) unique constraint.
    """
    created = 0
    updated = 0
    failed = 0
    errors = []
    
    for item in request.companies:
        try:
            # Find existing company by name and website
            query = select(Company).where(Company.name == item.name)
            if item.website:
                query = query.where(Company.website == item.website)
            
            result = await db.execute(query)
            existing = result.scalar_one_or_none()
            
            # Handle location if provided
            location_id = None
            if item.location_city and item.location_state:
                from app.utils.slug import generate_location_slug
                location_slug = generate_location_slug(item.location_city, item.location_state)
                loc_result = await db.execute(
                    select(Location).where(Location.slug == location_slug)
                )
                location = loc_result.scalar_one_or_none()
                
                if not location:
                    # Create location
                    location = Location(
                        city=item.location_city,
                        state=item.location_state,
                        slug=location_slug,
                        count=0,
                    )
                    db.add(location)
                    await db.flush()
                
                location_id = location.id
            
            if existing:
                # Update existing company
                if item.logo_url:
                    existing.logo_url = item.logo_url
                if item.description:
                    existing.description = item.description
                if location_id:
                    existing.location_id = location_id
                existing.scraped_at = datetime.utcnow()
                updated += 1
            else:
                # Create new company
                async def slug_exists(slug: str) -> bool:
                    result = await db.execute(
                        select(Company).where(Company.slug == slug)
                    )
                    return result.scalar_one_or_none() is not None
                
                slug = await generate_unique_slug(item.name, slug_exists)
                
                company = Company(
                    name=item.name,
                    slug=slug,
                    logo_url=item.logo_url,
                    website=item.website,
                    description=item.description,
                    location_id=location_id,
                    is_verified=False,
                    scraped_at=datetime.utcnow(),
                )
                db.add(company)
                created += 1
                
        except Exception as e:
            failed += 1
            errors.append(f"Failed to process company '{item.name}': {str(e)}")
            logger.error(f"Error upserting company {item.name}: {str(e)}")
    
    await db.commit()
    
    logger.info(f"Bulk upsert completed: {created} created, {updated} updated, {failed} failed")
    
    return CompanyBulkUpsertResponse(
        created=created,
        updated=updated,
        failed=failed,
        errors=errors,
    )
