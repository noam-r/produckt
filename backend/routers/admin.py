"""
Admin endpoints for user management and system configuration.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.rbac import require_admin
from backend.models.user import User
from backend.repositories.user_repository import UserRepository
from backend.repositories.role_repository import RoleRepository
from backend.repositories.user_role_repository import UserRoleRepository
from backend.repositories.analytics import AnalyticsRepository
from backend.services.audit_logger import AuditLogger
from backend.schemas.admin import (
    UserResponse,
    UserListResponse,
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserRequest,
    ChangePasswordRequest,
    ChangePasswordResponse,
    RoleResponse,
    UserRoleInfo,
)


router = APIRouter(prefix="/admin", tags=["Admin"])


# Helper function to convert User model to UserResponse with roles
def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse with role information."""
    roles = [
        UserRoleInfo(
            id=ur.role.id,
            name=ur.role.name,
            description=ur.role.description
        )
        for ur in user.user_roles
    ]

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        roles=roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )


# Role endpoints
@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all available roles."""
    role_repo = RoleRepository(db)
    roles = role_repo.get_all()
    return roles


# User management endpoints
@router.get("/users", response_model=UserListResponse)
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users in the organization."""
    user_repo = UserRepository(db)
    users = user_repo.get_all(current_user.organization_id)

    user_responses = [user_to_response(user) for user in users]

    return UserListResponse(
        users=user_responses,
        total=len(user_responses)
    )


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get a specific user by ID."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id, current_user.organization_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user_to_response(user)


@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user.

    Admin can either provide a password or request a randomly generated one.
    """
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    user_role_repo = UserRoleRepository(db)
    audit_logger = AuditLogger(db)

    # Check if email already exists
    existing_user = user_repo.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate password requirements
    if not request.generate_password and not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either password or set generate_password=true"
        )

    # Generate or use provided password
    password = (
        UserRepository.generate_random_password()
        if request.generate_password
        else request.password
    )

    # Create user
    user = user_repo.create(
        email=request.email,
        password=password,
        name=request.name,
        organization_id=current_user.organization_id,
        is_active=request.is_active
    )

    # Assign roles
    if request.role_ids:
        # Validate all role IDs exist
        for role_id in request.role_ids:
            role = role_repo.get_by_id(role_id)
            if not role:
                # Rollback user creation
                user_repo.delete(user.id, current_user.organization_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role ID {role_id} not found"
                )

        # Assign roles
        user_role_repo.set_user_roles(user.id, request.role_ids)

        # Refresh user to get updated roles
        db.refresh(user)

    # Get role names for audit log
    role_names = [ur.role.name for ur in user.user_roles]

    # Log user creation
    audit_logger.log_user_creation(
        user_id=user.id,
        email=user.email,
        name=user.name,
        roles=role_names,
        actor_id=current_user.id,
        organization_id=current_user.organization_id
    )

    return CreateUserResponse(
        user=user_to_response(user),
        generated_password=password if request.generate_password else None
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user details."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    user_role_repo = UserRoleRepository(db)
    audit_logger = AuditLogger(db)

    # Get existing user
    user = user_repo.get_by_id(user_id, current_user.organization_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Track changes for audit log
    changes = {}

    # Update basic fields
    if request.email and request.email != user.email:
        # Check if new email is already taken
        existing_user = user_repo.get_by_email(request.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        changes["email"] = {"old": user.email, "new": request.email}

    if request.name and request.name != user.name:
        changes["name"] = {"old": user.name, "new": request.name}

    if request.is_active is not None and request.is_active != user.is_active:
        changes["is_active"] = {"old": user.is_active, "new": request.is_active}

    # Update user
    updated_user = user_repo.update(
        user_id=user_id,
        organization_id=current_user.organization_id,
        email=request.email,
        name=request.name,
        is_active=request.is_active
    )

    # Update roles if provided
    if request.role_ids is not None:
        # Validate all role IDs exist
        for role_id in request.role_ids:
            role = role_repo.get_by_id(role_id)
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role ID {role_id} not found"
                )

        # Get old roles
        old_roles = set(ur.role.name for ur in user.user_roles)

        # Set new roles
        user_role_repo.set_user_roles(user_id, request.role_ids)

        # Refresh user to get updated roles
        db.refresh(updated_user)

        # Get new roles
        new_roles = set(ur.role.name for ur in updated_user.user_roles)

        # Calculate role changes
        added_roles = list(new_roles - old_roles)
        removed_roles = list(old_roles - new_roles)

        if added_roles or removed_roles:
            changes["roles"] = {
                "added": added_roles,
                "removed": removed_roles
            }

            # Log role changes separately
            audit_logger.log_role_assignment(
                user_id=user_id,
                added_roles=added_roles,
                removed_roles=removed_roles,
                actor_id=current_user.id,
                organization_id=current_user.organization_id
            )

    # Log user update if there were changes
    if changes:
        audit_logger.log_user_update(
            user_id=user_id,
            changes=changes,
            actor_id=current_user.id,
            organization_id=current_user.organization_id
        )

    return user_to_response(updated_user)


@router.post("/users/{user_id}/change-password", response_model=ChangePasswordResponse)
def change_user_password(
    user_id: UUID,
    request: ChangePasswordRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Change a user's password (admin only)."""
    user_repo = UserRepository(db)
    audit_logger = AuditLogger(db)

    # Get user
    user = user_repo.get_by_id(user_id, current_user.organization_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate password requirements
    if not request.generate_password and not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either password or set generate_password=true"
        )

    # Generate or use provided password
    password = (
        UserRepository.generate_random_password()
        if request.generate_password
        else request.password
    )

    # Change password
    user_repo.change_password(
        user_id=user_id,
        organization_id=current_user.organization_id,
        new_password=password
    )

    # Log password change
    audit_logger.log_password_change(
        user_id=user_id,
        changed_by_admin=True,
        actor_id=current_user.id,
        organization_id=current_user.organization_id
    )

    return ChangePasswordResponse(
        message="Password changed successfully",
        generated_password=password if request.generate_password else None
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user."""
    user_repo = UserRepository(db)
    audit_logger = AuditLogger(db)

    # Get user before deletion for audit log
    user = user_repo.get_by_id(user_id, current_user.organization_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Delete user
    success = user_repo.delete(user_id, current_user.organization_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Log user deletion
    audit_logger.log_user_deletion(
        user_id=user_id,
        email=user.email,
        actor_id=current_user.id,
        organization_id=current_user.organization_id
    )

    return None


# Analytics endpoints
@router.get("/analytics/overview")
def get_analytics_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to look back")
):
    """
    Get overall LLM usage analytics overview.

    Returns total statistics for the last N days.
    """
    analytics_repo = AnalyticsRepository(db)
    start_date = datetime.utcnow() - timedelta(days=days)

    total_stats = analytics_repo.get_total_stats(
        organization_id=current_user.organization_id,
        start_date=start_date
    )

    error_stats = analytics_repo.get_error_stats(
        organization_id=current_user.organization_id,
        start_date=start_date
    )

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "total_stats": total_stats,
        "error_stats": error_stats
    }


@router.get("/analytics/by-user")
def get_analytics_by_user(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(50, description="Maximum number of users to return")
):
    """
    Get LLM usage analytics broken down by user.

    Returns usage and cost for each user, ordered by total cost descending.
    """
    analytics_repo = AnalyticsRepository(db)
    start_date = datetime.utcnow() - timedelta(days=days)

    user_stats = analytics_repo.get_usage_by_user(
        organization_id=current_user.organization_id,
        start_date=start_date,
        limit=limit
    )

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "users": user_stats
    }


@router.get("/analytics/by-agent")
def get_analytics_by_agent(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to look back")
):
    """
    Get LLM usage analytics broken down by agent/action type.

    Returns usage and cost for each agent, ordered by total cost descending.
    """
    analytics_repo = AnalyticsRepository(db)
    start_date = datetime.utcnow() - timedelta(days=days)

    agent_stats = analytics_repo.get_usage_by_agent(
        organization_id=current_user.organization_id,
        start_date=start_date
    )

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "agents": agent_stats
    }


@router.get("/analytics/by-model")
def get_analytics_by_model(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to look back")
):
    """
    Get LLM usage analytics broken down by model.

    Returns usage and cost for each model, ordered by total cost descending.
    """
    analytics_repo = AnalyticsRepository(db)
    start_date = datetime.utcnow() - timedelta(days=days)

    model_stats = analytics_repo.get_usage_by_model(
        organization_id=current_user.organization_id,
        start_date=start_date
    )

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "models": model_stats
    }


@router.get("/analytics/over-time")
def get_analytics_over_time(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to look back"),
    granularity: str = Query("day", description="Time bucket size: hour, day, week, month")
):
    """
    Get LLM usage analytics over time for trend visualization.

    Returns time-series data with call counts and costs.
    """
    analytics_repo = AnalyticsRepository(db)
    start_date = datetime.utcnow() - timedelta(days=days)

    time_series = analytics_repo.get_usage_over_time(
        organization_id=current_user.organization_id,
        start_date=start_date,
        granularity=granularity
    )

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "granularity": granularity,
        "data": time_series
    }
