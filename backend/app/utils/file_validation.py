"""File validation utilities."""

from fastapi import UploadFile, HTTPException, status

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Maximum resume file size: 2MB
MAX_RESUME_SIZE = 2 * 1024 * 1024  # 2MB in bytes

# Allowed PDF MIME types
ALLOWED_PDF_MIME_TYPES = [
    "application/pdf",
    "application/x-pdf",
]


async def validate_pdf_file(file: UploadFile) -> None:
    """
    Validate PDF file for resume upload.
    
    Checks:
    - File extension is .pdf
    - MIME type is application/pdf
    - File size is <= 2MB
    
    Args:
        file: Uploaded file to validate
        
    Raises:
        HTTPException: If validation fails
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed. Please upload a .pdf file"
        )
    
    # Check MIME type
    if file.content_type not in ALLOWED_PDF_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Only PDF files are allowed"
        )
    
    # Check file size
    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0)  # Reset file pointer
    
    if file_size > MAX_RESUME_SIZE:
        size_in_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({size_in_mb:.2f}MB) exceeds maximum allowed size of 2MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )
    
    logger.info(f"PDF file validation passed: {file.filename}, size: {file_size} bytes")
