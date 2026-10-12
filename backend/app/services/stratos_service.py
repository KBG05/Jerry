"""Stratos API integration service for job recommendations."""

import httpx
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.core.logging_config import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class StratosService:
    """Service for interacting with Stratos job recommendation API."""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Stratos service.
        
        Args:
            base_url: Base URL of Stratos API (defaults to settings)
            api_key: API key for authentication (defaults to settings)
        """
        self.base_url = base_url or settings.stratos_api_url
        self.api_key = api_key or settings.stratos_api_key
        self.index_name = "JobData"
        
    async def get_job_recommendations(
        self,
        skills: List[str],
        description: str,
        top_k: int = 100,
        page: int = 0,
        size: int = 10
    ) -> List[UUID]:
        """
        Get job recommendations from Stratos API based on user skills and description.
        
        Args:
            skills: List of user skills
            description: User description/bio
            top_k: Number of top results to consider
            page: Page number for pagination
            size: Page size
            
        Returns:
            List of job UUIDs that match the user's profile
        """
        url = f"{self.base_url}/api/v1/indexes/{self.index_name}/search"
        
        headers = {
            "accept": "application/json",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        params = {
            "page": page,
            "size": size
        }
        
        payload = {
            "q": "Recommend jobs for the following user",
            "top_k": top_k,
            "user_context": {
                "skills": skills,
                "description": description
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, params=params, json=payload)
                response.raise_for_status()
                
                data = response.json()
                job_ids = []
                
                # Extract job IDs from hits
                if "hits" in data:
                    for hit in data["hits"]:
                        if "id" in hit:
                            try:
                                job_ids.append(UUID(hit["id"]))
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Invalid job ID format: {hit.get('id')} - {str(e)}")
                                continue
                
                logger.info(f"Retrieved {len(job_ids)} job recommendations from Stratos")
                return job_ids
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Stratos API: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error calling Stratos API: {str(e)}")
            return []
    
    async def get_all_job_recommendations_paginated(
        self,
        skills: List[str],
        description: str,
        top_k: int = 100,
        max_results: int = 100
    ) -> List[UUID]:
        """
        Get all job recommendations by paginating through results.
        
        Args:
            skills: List of user skills
            description: User description
            top_k: Number of top results per request
            max_results: Maximum total results to fetch
            
        Returns:
            List of all job UUIDs across all pages
        """
        all_job_ids = []
        page = 0
        page_size = 10
        
        while len(all_job_ids) < max_results:
            job_ids = await self.get_job_recommendations(
                skills=skills,
                description=description,
                top_k=top_k,
                page=page,
                size=page_size
            )
            
            if not job_ids:
                # No more results
                break
                
            all_job_ids.extend(job_ids)
            
            # If we got fewer results than page_size, we've reached the end
            if len(job_ids) < page_size:
                break
                
            page += 1
        
        # Return only up to max_results
        return all_job_ids[:max_results]


# Singleton instance
_stratos_service: Optional[StratosService] = None


def get_stratos_service() -> StratosService:
    """Get or create Stratos service singleton."""
    global _stratos_service
    if _stratos_service is None:
        _stratos_service = StratosService()
    return _stratos_service
