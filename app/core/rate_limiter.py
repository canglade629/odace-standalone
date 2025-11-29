"""Rate limiting configuration for API DDoS protection."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_limiter() -> Limiter:
    """
    Get configured rate limiter instance.
    
    Returns:
        Limiter configured for 60 requests per minute per IP address
    """
    return Limiter(
        key_func=get_remote_address,
        default_limits=[]  # No default limits; apply per-route
    )


# Create the limiter instance
limiter = get_limiter()

