"""File upload and management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from app.core.auth import verify_api_key
from app.core.models import FileUploadResponse
from app.core.config import get_settings
from app.utils.gcs_ops import get_gcs_operations
from app.core.rate_limiter import limiter
from datetime import datetime

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("60/minute")
async def upload_file(
    request: Request,
    domain: str,
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Upload a file to the raw data folder in GCS.
    
    Args:
        domain: Domain/folder name (e.g., 'accueillants', 'geo', 'logement')
        file: File to upload
        api_key: API key for authentication
        
    Returns:
        File upload response with destination path
    """
    settings = get_settings()
    gcs = get_gcs_operations()
    
    try:
        # Construct destination path
        destination = f"{settings.get_raw_path(domain)}/{file.filename}"
        
        # Upload file
        gcs.upload_file(file.file, destination)
        
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        
        return FileUploadResponse(
            filename=file.filename,
            destination=destination,
            size_bytes=size,
            uploaded_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/list")
@limiter.limit("60/minute")
async def list_files(
    request: Request,
    domain: str = None,
    api_key: str = Depends(verify_api_key)
):
    """
    List files in raw data storage.
    
    Args:
        domain: Optional domain filter
        api_key: API key for authentication
        
    Returns:
        List of files
    """
    settings = get_settings()
    gcs = get_gcs_operations()
    
    try:
        if domain:
            prefix = settings.get_raw_path(domain).replace(f"gs://{settings.gcs_bucket}/", "")
        else:
            prefix = settings.gcs_raw_prefix
        
        files = gcs.list_files(prefix)
        
        return {
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")

