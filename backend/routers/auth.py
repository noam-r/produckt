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
    RegisterRequest, LoginRequest, SessionResponse, MessageResponse, ChangePasswordRequest
)
from backend.schemas.admin import UserResponse, BudgetInfo, UserRoleInfo
from backend.auth.password import hash_password, verify_password
from backend.auth.password_validator import validate_password_or_raise, PasswordValidationError
from backend.auth.session import session_manager
from backend.config import settings
from backend.services.budget_service import BudgetService
from backend.auth.dependencies import get_current_user


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

    # Validate password complexity
    try:
        validate_password_or_raise(request.password)
    except PasswordValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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

    # Set session cookie with security attributes
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,  # Prevent JavaScript access (XSS protection)
        secure=settings.environment == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        max_age=settings.session_timeout_minutes * 60  # Convert minutes to seconds
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
        expires_at=session.expires_at,
        force_password_change=user.force_password_change
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

    # Set session cookie with security attributes
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,  # Prevent JavaScript access (XSS protection)
        secure=settings.environment == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        max_age=settings.session_timeout_minutes * 60  # Convert minutes to seconds
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
        expires_at=session.expires_at,
        force_password_change=user.force_password_change
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
def get_session(session_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
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

    # Fetch user from database to get current force_password_change flag
    user = db.query(User).filter(User.id == session.user_id).first()
    force_password_change = user.force_password_change if user else False

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        email=session.email,
        name=session.name,
        role=session.role,
        roles=session.roles,
        organization_id=session.organization_id,
        organization_name=session.organization_name,
        expires_at=session.expires_at,
        force_password_change=force_password_change
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    session_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Change user password.

    Requires authentication. Validates current password and password complexity.
    """
    # Verify session
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

    # Get user from database
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password complexity
    try:
        validate_password_or_raise(request.new_password)
    except PasswordValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Prevent reusing the same password
    if verify_password(request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Update password and clear force_password_change flag
    user.password_hash = hash_password(request.new_password)
    user.force_password_change = False
    db.commit()

    return MessageResponse(message="Password changed successfully")


@router.get("/profile", response_model=UserResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile including budget information.
    
    Returns detailed user information with budget status.
    """
    # Get user roles
    roles = [
        UserRoleInfo(
            id=ur.role.id,
            name=ur.role.name,
            description=ur.role.description
        )
        for ur in current_user.user_roles
    ]

    # Get budget information with warnings
    budget_service = BudgetService(db)
    try:
        budget_status_with_warnings = budget_service.get_budget_status_with_warnings(current_user.id)
        budget_info = BudgetInfo(
            monthly_budget_usd=budget_status_with_warnings["budget_limit"],
            current_spending_usd=budget_status_with_warnings["current_spending"],
            remaining_budget_usd=budget_status_with_warnings["remaining_budget"],
            utilization_percentage=budget_status_with_warnings["utilization_percentage"],
            budget_updated_at=current_user.budget_updated_at,
            budget_updated_by=current_user.budget_updated_by,
            has_warning=budget_status_with_warnings["has_warning"],
            warning_message=budget_status_with_warnings["warning_message"],
            is_over_budget=budget_status_with_warnings["is_over_budget"],
            is_near_limit=budget_status_with_warnings["is_near_limit"]
        )
    except Exception:
        # If budget service fails, return None for budget info
        budget_info = None

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        force_password_change=current_user.force_password_change,
        roles=roles,
        budget=budget_info,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login_at=current_user.last_login_at
    )
