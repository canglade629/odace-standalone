"""API Key management utilities for generating, storing, and validating API keys."""
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from google.cloud import firestore


def generate_api_key() -> str:
    """
    Generate a secure API key with sk_live_ prefix.
    
    Returns:
        A secure API key string (e.g., sk_live_abc123def456...)
    """
    # Generate 32 bytes of random data (256 bits of entropy)
    random_part = secrets.token_urlsafe(32)
    return f"sk_live_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.
    
    Args:
        api_key: The plaintext API key to hash
        
    Returns:
        The SHA-256 hash of the API key as a hexadecimal string
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


async def create_api_key(user_id: str, db: firestore.AsyncClient) -> Dict[str, Any]:
    """
    Generate a new API key and store it in Firestore.
    If the user already has an API key, it will be deleted and replaced.
    
    Args:
        user_id: The user identifier (email or user ID)
        db: Firestore async client
        
    Returns:
        Dictionary containing:
            - api_key: The plaintext API key (SHOW ONLY ONCE)
            - user_id: The user identifier
            - created_at: Timestamp of creation
            - replaced: Boolean indicating if an existing key was replaced
    """
    # Check for existing keys for this user and delete them
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    existing_keys = db.collection("api_keys").where(
        filter=FieldFilter("user_id", "==", user_id)
    ).stream()
    replaced = False
    
    async for doc in existing_keys:
        await doc.reference.delete()
        replaced = True
    
    # Generate the new API key
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    # Prepare document data
    doc_data = {
        "user_id": user_id,
        "created_at": firestore.SERVER_TIMESTAMP,
        "last_used_at": None,
        "active": True
    }
    
    # Store in Firestore using the hash as document ID
    doc_ref = db.collection("api_keys").document(hashed_key)
    await doc_ref.set(doc_data)
    
    return {
        "api_key": api_key,  # Return plaintext only once
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "replaced": replaced
    }


async def validate_api_key(api_key: str, db: firestore.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    Validate an API key against Firestore.
    
    Args:
        api_key: The plaintext API key to validate
        db: Firestore async client
        
    Returns:
        Dictionary with user_id and metadata if valid, None if invalid
    """
    hashed_key = hash_api_key(api_key)
    
    # Look up the key in Firestore
    doc_ref = db.collection("api_keys").document(hashed_key)
    doc = await doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()
    
    # Check if the key is active
    if not data.get("active", False):
        return None
    
    # Update last_used_at timestamp asynchronously (fire and forget)
    try:
        await doc_ref.update({"last_used_at": firestore.SERVER_TIMESTAMP})
    except Exception:
        # Don't fail validation if timestamp update fails
        pass
    
    return {
        "user_id": data.get("user_id"),
        "created_at": data.get("created_at"),
        "last_used_at": data.get("last_used_at")
    }


async def revoke_api_key(api_key: str, db: firestore.AsyncClient) -> bool:
    """
    Revoke an API key by setting active=False.
    
    Args:
        api_key: The plaintext API key to revoke
        db: Firestore async client
        
    Returns:
        True if revoked successfully, False if key not found
    """
    hashed_key = hash_api_key(api_key)
    doc_ref = db.collection("api_keys").document(hashed_key)
    doc = await doc_ref.get()
    
    if not doc.exists:
        return False
    
    await doc_ref.update({"active": False})
    return True


async def delete_api_key(api_key: str, db: firestore.AsyncClient) -> bool:
    """
    Permanently delete an API key from Firestore.
    
    Args:
        api_key: The plaintext API key to delete
        db: Firestore async client
        
    Returns:
        True if deleted successfully, False if key not found
    """
    hashed_key = hash_api_key(api_key)
    doc_ref = db.collection("api_keys").document(hashed_key)
    doc = await doc_ref.get()
    
    if not doc.exists:
        return False
    
    await doc_ref.delete()
    return True


async def list_api_keys(db: firestore.AsyncClient) -> list[Dict[str, Any]]:
    """
    List all API keys (without plaintext keys).
    
    Args:
        db: Firestore async client
        
    Returns:
        List of dictionaries containing key metadata (no plaintext)
    """
    keys = []
    docs = db.collection("api_keys").stream()
    
    async for doc in docs:
        data = doc.to_dict()
        keys.append({
            "hash": doc.id,
            "user_id": data.get("user_id"),
            "created_at": data.get("created_at"),
            "last_used_at": data.get("last_used_at"),
            "active": data.get("active", False)
        })
    
    return keys

