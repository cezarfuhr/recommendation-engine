"""Authentication dependencies for FastAPI"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_db
from .auth import decode_token, verify_token_type
from ..models import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user

    Args:
        current_user: Current user from token

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    # Add is_active field to User model if needed
    # For now, just return the user
    return current_user


# Optional: Role-based access control
def require_role(required_role: str):
    """
    Dependency to require a specific role

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        # Add role field to User model if needed
        user_role = current_user.preferences.get("role", "user")

        if user_role != required_role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return current_user

    return role_checker
