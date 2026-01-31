"""Job Categories API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import JobCategory, JobSubCategory
from app.schemas.job_category import (
    JobCategoryCreate,
    JobCategoryUpdate,
    JobCategoryResponse,
)
from app.schemas.job_sub_category import (
    JobSubCategoryCreate,
    JobSubCategoryUpdate,
    JobSubCategoryResponse,
)
from app.utils.slug import generate_slug, generate_unique_slug
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/job-categories", tags=["job-categories"])


@router.post(
    "",
    response_model=JobCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job category",
)
async def create_job_category(
    category_data: JobCategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> JobCategory:
    """Create a new job category."""
    # Check if category name already exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.name == category_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category_data.name}' already exists"
        )
    
    # Generate slug if not provided
    slug = category_data.slug
    if not slug:
        async def slug_exists(s: str) -> bool:
            result = await db.execute(
                select(JobCategory).where(JobCategory.slug == s)
            )
            return result.scalar_one_or_none() is not None
        
        slug = await generate_unique_slug(category_data.name, slug_exists)
    else:
        # Check if slug already exists
        result = await db.execute(
            select(JobCategory).where(JobCategory.slug == slug)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{slug}' already exists"
            )
    
    new_category = JobCategory(
        name=category_data.name,
        slug=slug,
        count=category_data.count,
    )
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    
    logger.info(f"Job category created: {new_category.id} - {new_category.name} ({new_category.slug})")
    return new_category


@router.get(
    "",
    response_model=List[JobCategoryResponse],
    summary="Get all job categories",
)
async def get_job_categories(
    db: AsyncSession = Depends(get_db),
) -> List[JobCategory]:
    """Get all job categories."""
    result = await db.execute(select(JobCategory).order_by(JobCategory.name))
    categories = result.scalars().all()
    return list(categories)


@router.get(
    "/slug/{slug}",
    response_model=JobCategoryResponse,
    summary="Get job category by slug",
)
async def get_job_category_by_slug(
    slug: str = Path(..., description="Category slug"),
    db: AsyncSession = Depends(get_db),
) -> JobCategory:
    """Get a specific job category by slug."""
    result = await db.execute(
        select(JobCategory).where(JobCategory.slug == slug)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job category with slug '{slug}' not found"
        )
    
    return category


@router.get(
    "/{category_id}",
    response_model=JobCategoryResponse,
    summary="Get job category by ID",
)
async def get_job_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobCategory:
    """Get a specific job category by ID."""
    result = await db.execute(
        select(JobCategory).where(JobCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job category with ID {category_id} not found"
        )
    
    return category


@router.put(
    "/{category_id}",
    response_model=JobCategoryResponse,
    summary="Update job category",
)
async def update_job_category(
    category_id: int,
    category_data: JobCategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobCategory:
    """Update a job category."""
    result = await db.execute(
        select(JobCategory).where(JobCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job category with ID {category_id} not found"
        )
    
    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    
    # Handle slug update
    if 'slug' in update_data and update_data['slug']:
        new_slug = update_data['slug']
        # Check if new slug conflicts with another category
        result = await db.execute(
            select(JobCategory).where(
                JobCategory.slug == new_slug,
                JobCategory.id != category_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{new_slug}' already exists"
            )
    
    # If name is being updated but not slug, regenerate slug
    if 'name' in update_data and 'slug' not in update_data:
        async def slug_exists(s: str) -> bool:
            result = await db.execute(
                select(JobCategory).where(
                    JobCategory.slug == s,
                    JobCategory.id != category_id
                )
            )
            return result.scalar_one_or_none() is not None
        
        update_data['slug'] = await generate_unique_slug(update_data['name'], slug_exists)
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await db.commit()
    await db.refresh(category)
    
    logger.info(f"Job category updated: {category.id} - {category.name} ({category.slug})")
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job category",
)
async def delete_job_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a job category (will cascade delete sub-categories)."""
    result = await db.execute(
        select(JobCategory).where(JobCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job category with ID {category_id} not found"
        )
    
    await db.delete(category)
    await db.commit()
    
    logger.info(f"Job category deleted: {category_id}")


# Sub-category endpoints
@router.post(
    "/{category_id}/sub-categories",
    response_model=JobSubCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job sub-category",
)
async def create_job_sub_category(
    category_id: int,
    sub_category_data: JobSubCategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> JobSubCategory:
    """Create a new job sub-category under a category."""
    # Verify parent category exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.id == category_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent category with ID {category_id} not found"
        )
    
    # Generate slug if not provided
    slug = sub_category_data.slug
    if not slug:
        slug = generate_slug(sub_category_data.name)
    
    new_sub_category = JobSubCategory(
        category_id=category_id,
        name=sub_category_data.name,
        slug=slug,
        count=sub_category_data.count,
    )
    db.add(new_sub_category)
    await db.commit()
    await db.refresh(new_sub_category)
    
    logger.info(f"Job sub-category created: {new_sub_category.id} - {new_sub_category.name} ({new_sub_category.slug})")
    return new_sub_category


@router.get(
    "/{category_id}/sub-categories",
    response_model=List[JobSubCategoryResponse],
    summary="Get all sub-categories for a category",
)
async def get_job_sub_categories(
    category_id: int,
    db: AsyncSession = Depends(get_db),
) -> List[JobSubCategory]:
    """Get all sub-categories for a specific category."""
    # Verify parent category exists
    result = await db.execute(
        select(JobCategory).where(JobCategory.id == category_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent category with ID {category_id} not found"
        )
    
    result = await db.execute(
        select(JobSubCategory)
        .where(JobSubCategory.category_id == category_id)
        .order_by(JobSubCategory.name)
    )
    sub_categories = result.scalars().all()
    return list(sub_categories)


@router.get(
    "/sub-categories/{sub_category_id}",
    response_model=JobSubCategoryResponse,
    summary="Get sub-category by ID",
)
async def get_job_sub_category(
    sub_category_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobSubCategory:
    """Get a specific job sub-category by ID."""
    result = await db.execute(
        select(JobSubCategory).where(JobSubCategory.id == sub_category_id)
    )
    sub_category = result.scalar_one_or_none()
    
    if not sub_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job sub-category with ID {sub_category_id} not found"
        )
    
    return sub_category


@router.put(
    "/sub-categories/{sub_category_id}",
    response_model=JobSubCategoryResponse,
    summary="Update job sub-category",
)
async def update_job_sub_category(
    sub_category_id: int,
    sub_category_data: JobSubCategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobSubCategory:
    """Update a job sub-category."""
    result = await db.execute(
        select(JobSubCategory).where(JobSubCategory.id == sub_category_id)
    )
    sub_category = result.scalar_one_or_none()
    
    if not sub_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job sub-category with ID {sub_category_id} not found"
        )
    
    # Update fields
    update_data = sub_category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub_category, field, value)
    
    await db.commit()
    await db.refresh(sub_category)
    
    logger.info(f"Job sub-category updated: {sub_category.id} - {sub_category.name}")
    return sub_category


@router.delete(
    "/sub-categories/{sub_category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job sub-category",
)
async def delete_job_sub_category(
    sub_category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a job sub-category."""
    result = await db.execute(
        select(JobSubCategory).where(JobSubCategory.id == sub_category_id)
    )
    sub_category = result.scalar_one_or_none()
    
    if not sub_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job sub-category with ID {sub_category_id} not found"
        )
    
    await db.delete(sub_category)
    await db.commit()
    
    logger.info(f"Job sub-category deleted: {sub_category_id}")
