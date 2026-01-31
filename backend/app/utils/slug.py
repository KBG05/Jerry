"""Slug generation utilities."""

import re
import uuid
from typing import Optional, Callable, Awaitable
from unidecode import unidecode


def generate_slug(text: str) -> str:
    """
    Generate URL-friendly slug from text.
    
    Args:
        text: The text to convert to a slug
        
    Returns:
        URL-friendly slug string
        
    Example:
        >>> generate_slug("Software Engineering")
        'software-engineering'
        >>> generate_slug("Data Science & Analytics")
        'data-science-analytics'
    """
    # Transliterate unicode to ASCII
    text = unidecode(text).lower()
    # Remove non-alphanumeric characters except spaces and hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces and multiple hyphens with single hyphen
    text = re.sub(r'[-\s]+', '-', text)
    # Remove leading/trailing hyphens
    return text.strip('-')


def generate_location_slug(city: str, state: str) -> str:
    """
    Generate slug for location in format city-state.
    
    Args:
        city: City name
        state: State name or abbreviation
        
    Returns:
        Location slug in format 'city-state'
        
    Example:
        >>> generate_location_slug("San Francisco", "CA")
        'san-francisco-ca'
        >>> generate_location_slug("New York", "NY")
        'new-york-ny'
    """
    city_slug = generate_slug(city)
    state_slug = generate_slug(state)
    return f"{city_slug}-{state_slug}"


def generate_job_slug(title: str, company_name: str, job_id: uuid.UUID) -> str:
    """
    Generate slug for job posting.
    
    Format: {title-slug}-{company-slug}-{short-id}
    
    Args:
        title: Job title
        company_name: Company name
        job_id: Job UUID
        
    Returns:
        Job slug string
        
    Example:
        >>> generate_job_slug("Senior Software Engineer", "Stripe", uuid.UUID('550e8400-e29b-41d4-a716-446655440000'))
        'senior-software-engineer-stripe-550e84'
    """
    title_slug = generate_slug(title)
    company_slug = generate_slug(company_name)
    # Use first 6 characters of UUID for short ID
    short_id = str(job_id).replace('-', '')[:6]
    return f"{title_slug}-{company_slug}-{short_id}"


async def generate_unique_slug(
    base_text: str,
    check_exists_fn: Callable[[str], Awaitable[bool]],
    max_attempts: int = 100
) -> str:
    """
    Generate a unique slug by appending numeric suffix if needed.
    
    Args:
        base_text: The text to convert to a slug
        check_exists_fn: Async function that returns True if slug exists
        max_attempts: Maximum number of suffix attempts
        
    Returns:
        Unique slug string
        
    Raises:
        ValueError: If unique slug cannot be generated within max_attempts
        
    Example:
        async def slug_exists(slug):
            # Check database
            return await db.query(Model).filter(Model.slug == slug).first() is not None
            
        unique_slug = await generate_unique_slug("software-engineer", slug_exists)
        # Returns "software-engineer" if available, else "software-engineer-2", etc.
    """
    base_slug = generate_slug(base_text)
    
    # Try the base slug first
    if not await check_exists_fn(base_slug):
        return base_slug
    
    # Try with numeric suffixes
    for i in range(2, max_attempts + 2):
        candidate_slug = f"{base_slug}-{i}"
        if not await check_exists_fn(candidate_slug):
            return candidate_slug
    
    raise ValueError(f"Could not generate unique slug for '{base_text}' after {max_attempts} attempts")


def parse_location_slug(slug: str) -> tuple[str, str]:
    """
    Parse location slug back to city and state parts.
    
    Note: This is a best-effort parse and may not perfectly reconstruct
    the original city/state names.
    
    Args:
        slug: Location slug in format 'city-state'
        
    Returns:
        Tuple of (city_part, state_part)
        
    Example:
        >>> parse_location_slug("san-francisco-ca")
        ('san-francisco', 'ca')
        >>> parse_location_slug("new-york-ny")
        ('new-york', 'ny')
    """
    # Assume last part after hyphen is state (works for abbreviated states)
    parts = slug.rsplit('-', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return slug, ''
