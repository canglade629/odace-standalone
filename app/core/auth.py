"""API Key authentication middleware."""
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.cloud import firestore
from app.core.api_key_manager import validate_api_key
from functools import lru_cache

security = HTTPBearer(auto_error=False)


@lru_cache()
def get_firestore_client() -> firestore.AsyncClient:
    """Get cached Firestore async client with explicit project."""
    from app.core.config import get_settings
    settings = get_settings()
    # Explicitly specify project to ensure proper authentication
    return firestore.AsyncClient(project=settings.gcp_project_id)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: firestore.AsyncClient = Depends(get_firestore_client)
) -> str:
    """
    Verify API key from Authorization Bearer token.
    
    Args:
        credentials: Bearer token credentials from Authorization header
        db: Firestore async client
        
    Returns:
        The user_id associated with the validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Please provide Authorization: Bearer header."
        )
    
    api_key = credentials.credentials
    
    # Validate the API key against Firestore
    user_data = await validate_api_key(api_key, db)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key"
        )
    
    return user_data["user_id"]


async def verify_admin_secret(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> bool:
    """
    Verify admin secret for admin endpoints.
    
    Args:
        credentials: Bearer token credentials from Authorization header
        
    Returns:
        True if admin secret is valid
        
    Raises:
        HTTPException: If admin secret is invalid or missing
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin secret is missing. Please provide Authorization: Bearer header."
        )
    
    if credentials.credentials != settings.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret"
        )
    
    return True

