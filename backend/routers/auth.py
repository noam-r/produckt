"""
Authentication endpoints for user registration, login, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Response
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from backend.database import get_db
from backend.models import User, Organization, UserRoleEnum
from backend.models.user_role import UserRole as UserRoleAssociation
from backend.schemas.auth import (
    RegisterRequest, LoginRequest, SessionResponse, MessageResponse
)
from backend.auth.password import hash_password, verify_password
from backend.auth.session import session_manager


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user and optionally create or join an organization.

    - If `organization_name` is provided, creates a new organization
    - If `organization_id` is provided, joins an existing organization
    - If neither is provided, raises a 400 error
    - User is created with PRODUCT_MANAGER role if creating new org, CONTRIBUTOR if joining
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Determine organization
    organization = None
    user_role = UserRoleEnum.CONTRIBUTOR  # Default role for joining existing org

    if request.organization_name:
        # Create new organization
        organization = Organization(name=request.organization_name)
        db.add(organization)
        db.flush()  # Get the ID without committing
        user_role = UserRoleEnum.PRODUCT_MANAGER  # Creator gets PM role

    elif request.organization_id:
        # Join existing organization
        organization = db.query(Organization).filter(
            Organization.id == request.organization_id
        ).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either organization_name or organization_id"
        )

    # Hash password
    password_hash = hash_password(request.password)

    # Create user
    user = User(
        email=request.email,
        password_hash=password_hash,
        name=request.name,
        role=user_role,
        organization_id=organization.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(organization)

    # Create session (new users don't have many-to-many roles yet, just legacy role)
    session = session_manager.create_session(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        organization_id=organization.id,
        organization_name=organization.name,
        roles=[]  # Empty roles for new users
    )

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=86400  # 24 hours in seconds
    )

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        email=session.email,
        name=session.name,
        role=session.role,
        roles=session.roles,
        organization_id=session.organization_id,
        organization_name=session.organization_name,
        expires_at=session.expires_at
    )


@router.post("/login", response_model=SessionResponse)
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and create a session.

    Returns session information and sets a session cookie.
    """
    # Find user by email and eagerly load roles
    user = db.query(User).filter(User.email == request.email).options(
        joinedload(User.user_roles).joinedload(UserRoleAssociation.role)
    ).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Get organization
    organization = db.query(Organization).filter(
        Organization.id == user.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User organization not found"
        )

    # Update last login
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Get user role names
    role_names = [ur.role.name for ur in user.user_roles]

    # Create session with roles
    session = session_manager.create_session(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,  # Legacy single role
        organization_id=organization.id,
        organization_name=organization.name,
        roles=role_names  # Multiple roles for RBAC
    )

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=86400  # 24 hours in seconds
    )

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        email=session.email,
        name=session.name,
        role=session.role,
        roles=session.roles,
        organization_id=session.organization_id,
        organization_name=session.organization_name,
        expires_at=session.expires_at
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    session_id: Optional[str] = Cookie(None)
):
    """
    Logout a user by deleting their session.

    Removes the session cookie and invalidates the session.
    """
    if session_id:
        session_manager.delete_session(session_id)

    # Clear session cookie
    response.delete_cookie(key="session_id")

    return MessageResponse(message="Logged out successfully")


@router.get("/session", response_model=SessionResponse)
def get_session(session_id: Optional[str] = Cookie(None)):
    """
    Get the current session information.

    Returns 401 if no valid session exists.
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

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        email=session.email,
        name=session.name,
        role=session.role,
        roles=session.roles,
        organization_id=session.organization_id,
        organization_name=session.organization_name,
        expires_at=session.expires_at
    )
