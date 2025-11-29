"""Admin API routes for managing API keys."""
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.auth import verify_admin_secret, get_firestore_client
from app.core.api_key_manager import (
    create_api_key,
    revoke_api_key,
    delete_api_key,
    list_api_keys
)


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_secret)]
)


class CreateAPIKeyRequest(BaseModel):
    """Request model for creating a new API key."""
    user_id: str


class CreateAPIKeyResponse(BaseModel):
    """Response model for API key creation."""
    api_key: str
    user_id: str
    created_at: str
    message: str = "API key created successfully. Save this key - it will not be shown again."


class RevokeAPIKeyRequest(BaseModel):
    """Request model for revoking an API key."""
    api_key: str


class DeleteAPIKeyRequest(BaseModel):
    """Request model for deleting an API key."""
    api_key: str


class APIKeyInfo(BaseModel):
    """API key metadata (without plaintext key)."""
    hash: str
    user_id: str
    created_at: Optional[datetime]
    last_used_at: Optional[datetime]
    active: bool


@router.post("/api-keys", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
    request: CreateAPIKeyRequest,
    db: firestore.AsyncClient = Depends(get_firestore_client)
):
    """
    Create a new API key for a user.
    
    Requires admin authentication via ADMIN_SECRET.
    
    Args:
        request: Contains user_id for the new API key
        db: Firestore async client
        
    Returns:
        The newly created API key (shown only once)
    """
    result = await create_api_key(request.user_id, db)
    
    return CreateAPIKeyResponse(
        api_key=result["api_key"],
        user_id=result["user_id"],
        created_at=result["created_at"]
    )


@router.delete("/api-keys/revoke")
async def revoke_existing_api_key(
    request: RevokeAPIKeyRequest,
    db: firestore.AsyncClient = Depends(get_firestore_client)
):
    """
    Revoke an API key (soft delete - sets active=False).
    
    Requires admin authentication via ADMIN_SECRET.
    
    Args:
        request: Contains the API key to revoke
        db: Firestore async client
        
    Returns:
        Success message
    """
    success = await revoke_api_key(request.api_key, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}


@router.delete("/api-keys/delete")
async def delete_existing_api_key(
    request: DeleteAPIKeyRequest,
    db: firestore.AsyncClient = Depends(get_firestore_client)
):
    """
    Permanently delete an API key from Firestore.
    
    Requires admin authentication via ADMIN_SECRET.
    
    Args:
        request: Contains the API key to delete
        db: Firestore async client
        
    Returns:
        Success message
    """
    success = await delete_api_key(request.api_key, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key deleted successfully"}


@router.get("/api-keys", response_model=List[APIKeyInfo])
async def list_all_api_keys(
    db: firestore.AsyncClient = Depends(get_firestore_client)
):
    """
    List all API keys (without plaintext keys).
    
    Requires admin authentication via ADMIN_SECRET.
    
    Args:
        db: Firestore async client
        
    Returns:
        List of API key metadata
    """
    keys = await list_api_keys(db)
    return keys

