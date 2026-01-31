"""Cloudflare R2 storage service for resume uploads."""

import uuid
from typing import Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class R2ServiceError(Exception):
    """R2 service related errors."""
    pass


def get_s3_client():
    """
    Get S3 client configured for Cloudflare R2.
    
    Returns:
        boto3 S3 client
    """
    settings = get_settings()
    
    if not settings.r2_account_id or not settings.r2_access_key_id or not settings.r2_secret_access_key:
        raise R2ServiceError("R2 credentials not configured")
    
    try:
        client = boto3.client(
            's3',
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name=settings.r2_region,
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize R2 client: {str(e)}")
        raise R2ServiceError(f"Failed to initialize R2 client: {str(e)}")


def get_resume_key(user_id: uuid.UUID) -> str:
    """
    Get the S3 object key for a user's resume.
    
    Args:
        user_id: User's UUID
        
    Returns:
        S3 object key (path)
    """
    return f"resumes/{user_id}.pdf"


async def upload_resume(user_id: uuid.UUID, file: UploadFile) -> str:
    """
    Upload resume to Cloudflare R2.
    
    Args:
        user_id: User's UUID
        file: Resume file to upload
        
    Returns:
        S3 object key (path) of uploaded file
        
    Raises:
        R2ServiceError: If upload fails
    """
    settings = get_settings()
    client = get_s3_client()
    resume_key = get_resume_key(user_id)
    
    try:
        # Read file content
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Upload to R2
        client.put_object(
            Bucket=settings.r2_bucket_name,
            Key=resume_key,
            Body=file_content,
            ContentType='application/pdf',
            Metadata={
                'user_id': str(user_id),
                'original_filename': file.filename or 'resume.pdf'
            }
        )
        
        logger.info(f"Resume uploaded successfully for user: {user_id}")
        return resume_key
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to upload resume for user {user_id}: {str(e)}")
        raise R2ServiceError(f"Failed to upload resume: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error uploading resume for user {user_id}: {str(e)}")
        raise R2ServiceError(f"Unexpected error: {str(e)}")


def delete_resume(user_id: uuid.UUID) -> bool:
    """
    Delete resume from Cloudflare R2.
    
    Args:
        user_id: User's UUID
        
    Returns:
        True if deleted successfully, False if file doesn't exist
        
    Raises:
        R2ServiceError: If deletion fails
    """
    settings = get_settings()
    client = get_s3_client()
    resume_key = get_resume_key(user_id)
    
    try:
        # Check if file exists first
        if not resume_exists(user_id):
            logger.info(f"Resume not found for user {user_id}, nothing to delete")
            return False
        
        # Delete from R2
        client.delete_object(
            Bucket=settings.r2_bucket_name,
            Key=resume_key
        )
        
        logger.info(f"Resume deleted successfully for user: {user_id}")
        return True
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to delete resume for user {user_id}: {str(e)}")
        raise R2ServiceError(f"Failed to delete resume: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting resume for user {user_id}: {str(e)}")
        raise R2ServiceError(f"Unexpected error: {str(e)}")


def get_resume_presigned_url(user_id: uuid.UUID, expiry: Optional[int] = None) -> str:
    """
    Generate a pre-signed URL for downloading resume.
    
    Args:
        user_id: User's UUID
        expiry: URL expiry time in seconds (defaults to settings value)
        
    Returns:
        Pre-signed URL
        
    Raises:
        R2ServiceError: If URL generation fails
    """
    settings = get_settings()
    client = get_s3_client()
    resume_key = get_resume_key(user_id)
    
    if expiry is None:
        expiry = settings.r2_presigned_url_expiry
    
    try:
        # Check if file exists
        if not resume_exists(user_id):
            raise R2ServiceError(f"Resume not found for user {user_id}")
        
        # Generate pre-signed URL
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.r2_bucket_name,
                'Key': resume_key,
            },
            ExpiresIn=expiry
        )
        
        logger.info(f"Generated pre-signed URL for user {user_id}")
        return url
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to generate pre-signed URL for user {user_id}: {str(e)}")
        raise R2ServiceError(f"Failed to generate download URL: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error generating URL for user {user_id}: {str(e)}")
        raise R2ServiceError(f"Unexpected error: {str(e)}")


def resume_exists(user_id: uuid.UUID) -> bool:
    """
    Check if resume exists in R2 for a user.
    
    Args:
        user_id: User's UUID
        
    Returns:
        True if resume exists, False otherwise
    """
    settings = get_settings()
    client = get_s3_client()
    resume_key = get_resume_key(user_id)
    
    try:
        client.head_object(
            Bucket=settings.r2_bucket_name,
            Key=resume_key
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        logger.error(f"Error checking resume existence for user {user_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking resume for user {user_id}: {str(e)}")
        return False
