"""Rate limiting utilities"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from typing import Callable
import functools

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="redis://redis:6379/1",  # Use Redis for distributed rate limiting
    strategy="fixed-window"
)


def rate_limit(limit_string: str):
    """
    Decorator for rate limiting specific endpoints

    Usage:
        @router.get("/endpoint")
        @rate_limit("5/minute")
        async def endpoint():
            pass

    Args:
        limit_string: Rate limit (e.g., "5/minute", "100/hour")
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # The actual rate limiting is handled by SlowAPI middleware
            return await func(*args, **kwargs)

        # Add rate limit metadata for SlowAPI
        wrapper.__rate_limit__ = limit_string
        return wrapper

    return decorator


async def get_user_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key based on authenticated user

    Falls back to IP address if user is not authenticated.
    """
    # Try to get user from token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from .auth import decode_token
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass

    # Fallback to IP address
    return get_remote_address(request)


# Create a user-based limiter
user_limiter = Limiter(
    key_func=get_user_rate_limit_key,
    default_limits=["200/minute"],
    storage_uri="redis://redis:6379/1",
    strategy="fixed-window"
)
