"""
Authentication dependencies for protecting routes.
"""

from fastapi import Cookie, HTTPException, status, Depends
from typing import Optional
from sqlalchemy.orm import Session

from backend.auth.session import session_manager, Session as SessionData
from backend.database import get_db
from backend.models import User, UserRoleEnum


def get_current_session(session_id: Optional[str] = Cookie(None)) -> SessionData:
    """
    Dependency to get the current authenticated session.

    Raises 401 if no valid session exists.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return session


def get_current_user(
    session: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the database.

    Raises 401 if session is invalid or user doesn't exist.
    """
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


def require_role(*allowed_roles: UserRole):
    """
    Create a dependency that requires the user to have one of the specified roles.

    Usage:
        @router.get("/admin")
        def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(r.value for r in allowed_roles)}"
            )
        return user

    return role_checker


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires ADMIN role.

    Convenience wrapper around require_role(UserRole.ADMIN).
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def require_product_manager(user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires PRODUCT_MANAGER or ADMIN role.

    Product managers and admins have elevated permissions.
    """
    if user.role not in [UserRoleEnum.PRODUCT_MANAGER, UserRoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Product Manager or Admin access required"
        )
    return user
