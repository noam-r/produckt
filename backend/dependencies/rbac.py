"""
Role-Based Access Control (RBAC) dependencies.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User


def require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to require admin role.

    Raises:
        HTTPException: 403 if user doesn't have admin role

    Returns:
        The current user if they have admin role
    """
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def require_any_role(*roles: str):
    """
    Dependency factory to require any of the specified roles.

    Usage:
        @router.get("/endpoint")
        def endpoint(user: User = Depends(require_any_role("admin", "technical"))):
            ...

    Args:
        *roles: Role names that are allowed

    Returns:
        Dependency function that checks for required roles
    """
    def check_roles(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if not current_user.has_any_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following roles is required: {', '.join(roles)}"
            )
        return current_user

    return check_roles


def require_all_roles(*roles: str):
    """
    Dependency factory to require all of the specified roles.

    Usage:
        @router.get("/endpoint")
        def endpoint(user: User = Depends(require_all_roles("admin", "technical"))):
            ...

    Args:
        *roles: Role names that are all required

    Returns:
        Dependency function that checks for required roles
    """
    def check_roles(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_roles = set(current_user.role_names)
        required_roles = set(roles)
        if not required_roles.issubset(user_roles):
            missing_roles = required_roles - user_roles
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(missing_roles)}"
            )
        return current_user

    return check_roles
