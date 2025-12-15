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
from backend.services.budget_service import BudgetService
from backend.auth.session import session_manager
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
    BudgetInfo,
    UpdateBudgetRequest,
    UpdateBudgetResponse,
    BudgetOverviewResponse,
    SpendingTrendsResponse,
    BudgetAlertsResponse,
)


router = APIRouter(prefix="/admin", tags=["Admin"])


# Helper function to convert User model to UserResponse with roles
def user_to_response(user: User, db: Session) -> UserResponse:
    """Convert User model to UserResponse with role and budget information."""
    roles = [
        UserRoleInfo(
            id=ur.role.id,
            name=ur.role.name,
            description=ur.role.description
        )
        for ur in user.user_roles
    ]

    # Get budget information with warnings
    budget_service = BudgetService(db)
    try:
        budget_status_with_warnings = budget_service.get_budget_status_with_warnings(user.id)
        budget_info = BudgetInfo(
            monthly_budget_usd=budget_status_with_warnings["budget_limit"],
            current_spending_usd=budget_status_with_warnings["current_spending"],
            remaining_budget_usd=budget_status_with_warnings["remaining_budget"],
            utilization_percentage=budget_status_with_warnings["utilization_percentage"],
            budget_updated_at=user.budget_updated_at,
            budget_updated_by=user.budget_updated_by,
            has_warning=budget_status_with_warnings["has_warning"],
            warning_message=budget_status_with_warnings["warning_message"],
            is_over_budget=budget_status_with_warnings["is_over_budget"],
            is_near_limit=budget_status_with_warnings["is_near_limit"]
        )
    except Exception:
        # If budget service fails, return None for budget info
        budget_info = None

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        roles=roles,
        budget=budget_info,
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

    user_responses = [user_to_response(user, db) for user in users]

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

    return user_to_response(user, db)


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
        user=user_to_response(user, db),
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

    # Track if we need to invalidate sessions after DB update
    should_invalidate_sessions = False
    
    if request.is_active is not None and request.is_active != user.is_active:
        changes["is_active"] = {"old": user.is_active, "new": request.is_active}
        
        # Mark for session invalidation AFTER database update
        if request.is_active is False:
            should_invalidate_sessions = True

    if request.force_password_change is not None and request.force_password_change != user.force_password_change:
        changes["force_password_change"] = {"old": user.force_password_change, "new": request.force_password_change}

    # Update user in database FIRST
    updated_user = user_repo.update(
        user_id=user_id,
        organization_id=current_user.organization_id,
        email=request.email,
        name=request.name,
        is_active=request.is_active,
        force_password_change=request.force_password_change
    )
    
    # AFTER database is updated, invalidate sessions
    if should_invalidate_sessions:
        deleted_sessions = session_manager.delete_user_sessions(user_id)
        changes["sessions_invalidated"] = deleted_sessions

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

    return user_to_response(updated_user, db)


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


@router.put("/users/{user_id}/budget", response_model=UpdateBudgetResponse)
def update_user_budget(
    user_id: UUID,
    request: UpdateBudgetRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update a user's monthly budget (admin only)."""
    user_repo = UserRepository(db)
    budget_service = BudgetService(db)
    audit_logger = AuditLogger(db)

    # Get existing user
    user = user_repo.get_by_id(user_id, current_user.organization_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Store old budget for audit log
    old_budget = user.monthly_budget_usd

    try:
        # Update budget using budget service (includes validation)
        budget_service.update_user_budget(
            user_id=user_id,
            new_budget=request.monthly_budget_usd,
            updated_by=current_user.id
        )

        # Refresh user to get updated budget info
        db.refresh(user)

        # Log budget change
        audit_logger.log_budget_change(
            user_id=user_id,
            old_budget=float(old_budget),
            new_budget=float(request.monthly_budget_usd),
            actor_id=current_user.id,
            organization_id=current_user.organization_id
        )

        return UpdateBudgetResponse(
            message=f"Budget updated successfully to ${request.monthly_budget_usd}",
            user=user_to_response(user, db)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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


# Budget monitoring endpoints
@router.get("/budget/overview", response_model=BudgetOverviewResponse)
def get_budget_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get budget overview dashboard for all users in the organization.
    
    Returns summary statistics and user budget utilization data.
    """
    user_repo = UserRepository(db)
    budget_service = BudgetService(db)
    
    # Get all users in organization
    users = user_repo.get_all(current_user.organization_id)
    
    # Calculate budget statistics
    total_budget = sum(user.monthly_budget_usd for user in users)
    total_spending = Decimal('0.00')
    users_over_budget = 0
    users_near_limit = 0  # 80%+ utilization
    user_budget_data = []
    
    for user in users:
        try:
            budget_status = budget_service.get_budget_status_with_warnings(user.id)
            current_spending = budget_status["current_spending"]
            budget_limit = budget_status["budget_limit"]
            utilization = budget_status["utilization_percentage"]
            
            total_spending += current_spending
            
            if budget_status["is_over_budget"]:
                users_over_budget += 1
            elif utilization >= 80.0:
                users_near_limit += 1
            
            user_budget_data.append({
                "user_id": str(user.id),
                "email": user.email,
                "name": user.name,
                "monthly_budget_usd": float(budget_limit),
                "current_spending_usd": float(current_spending),
                "remaining_budget_usd": float(budget_status["remaining_budget"]),
                "utilization_percentage": utilization,
                "is_over_budget": budget_status["is_over_budget"],
                "is_near_limit": budget_status["is_near_limit"],
                "has_warning": budget_status["has_warning"],
                "warning_message": budget_status["warning_message"]
            })
        except Exception:
            # If budget service fails for a user, skip them
            continue
    
    # Sort by utilization percentage descending
    user_budget_data.sort(key=lambda x: x["utilization_percentage"], reverse=True)
    
    return {
        "summary": {
            "total_users": len(users),
            "total_budget_usd": float(total_budget),
            "total_spending_usd": float(total_spending),
            "remaining_budget_usd": float(total_budget - total_spending),
            "overall_utilization_percentage": float(total_spending / total_budget * 100) if total_budget > 0 else 0.0,
            "users_over_budget": users_over_budget,
            "users_near_limit": users_near_limit,
            "users_within_budget": len(users) - users_over_budget - users_near_limit
        },
        "users": user_budget_data
    }


@router.get("/budget/spending-trends", response_model=SpendingTrendsResponse)
def get_spending_trends(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    months: int = Query(6, description="Number of months to look back", ge=1, le=24)
):
    """
    Get spending trends over time for budget analytics.
    
    Returns monthly spending data for trend analysis.
    """
    from backend.repositories.user_repository import UserRepository
    from backend.models.user_monthly_spending import UserMonthlySpending
    from sqlalchemy import extract
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date.replace(day=1)  # First day of current month
    
    # Go back the specified number of months
    for _ in range(months - 1):
        if start_date.month == 1:
            start_date = start_date.replace(year=start_date.year - 1, month=12)
        else:
            start_date = start_date.replace(month=start_date.month - 1)
    
    # Query monthly spending data
    spending_data = (
        db.query(
            UserMonthlySpending.year,
            UserMonthlySpending.month,
            func.sum(UserMonthlySpending.total_spent_usd).label('total_spending'),
            func.count(UserMonthlySpending.user_id).label('active_users')
        )
        .join(User, User.id == UserMonthlySpending.user_id)
        .filter(
            User.organization_id == current_user.organization_id,
            UserMonthlySpending.year >= start_date.year,
            UserMonthlySpending.month >= start_date.month if UserMonthlySpending.year == start_date.year else True
        )
        .group_by(UserMonthlySpending.year, UserMonthlySpending.month)
        .order_by(UserMonthlySpending.year, UserMonthlySpending.month)
        .all()
    )
    
    # Get total budget for each month (sum of all user budgets)
    user_repo = UserRepository(db)
    users = user_repo.get_all(current_user.organization_id)
    total_monthly_budget = sum(user.monthly_budget_usd for user in users)
    
    # Format the data
    trends = []
    for row in spending_data:
        month_str = f"{row.year}-{row.month:02d}"
        utilization = float(row.total_spending / total_monthly_budget * 100) if total_monthly_budget > 0 else 0.0
        
        trends.append({
            "year": row.year,
            "month": row.month,
            "month_label": month_str,
            "total_spending_usd": float(row.total_spending),
            "active_users": row.active_users,
            "total_budget_usd": float(total_monthly_budget),
            "utilization_percentage": utilization
        })
    
    return {
        "period_months": months,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "trends": trends
    }


@router.get("/budget/alerts", response_model=BudgetAlertsResponse)
def get_budget_alerts(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    include_resolved: bool = Query(False, description="Include users who are no longer over budget")
):
    """
    Get budget utilization alerts for monitoring.
    
    Returns users who are over budget or approaching their limits.
    """
    user_repo = UserRepository(db)
    budget_service = BudgetService(db)
    
    users = user_repo.get_all(current_user.organization_id)
    alerts = []
    
    for user in users:
        try:
            budget_status = budget_service.get_budget_status_with_warnings(user.id)
            
            # Only include users with warnings or over budget
            if budget_status["has_warning"] or budget_status["is_over_budget"]:
                alert_level = "critical" if budget_status["is_over_budget"] else "warning"
                
                alerts.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "alert_level": alert_level,
                    "monthly_budget_usd": float(budget_status["budget_limit"]),
                    "current_spending_usd": float(budget_status["current_spending"]),
                    "utilization_percentage": budget_status["utilization_percentage"],
                    "is_over_budget": budget_status["is_over_budget"],
                    "warning_message": budget_status["warning_message"],
                    "last_updated": datetime.utcnow().isoformat()
                })
            elif include_resolved:
                # Include users within budget if requested
                alerts.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "alert_level": "resolved",
                    "monthly_budget_usd": float(budget_status["budget_limit"]),
                    "current_spending_usd": float(budget_status["current_spending"]),
                    "utilization_percentage": budget_status["utilization_percentage"],
                    "is_over_budget": False,
                    "warning_message": None,
                    "last_updated": datetime.utcnow().isoformat()
                })
        except Exception:
            # Skip users with budget service errors
            continue
    
    # Sort by utilization percentage descending (most critical first)
    alerts.sort(key=lambda x: x["utilization_percentage"], reverse=True)
    
    return {
        "total_alerts": len([a for a in alerts if a["alert_level"] in ["warning", "critical"]]),
        "critical_alerts": len([a for a in alerts if a["alert_level"] == "critical"]),
        "warning_alerts": len([a for a in alerts if a["alert_level"] == "warning"]),
        "alerts": alerts
    }

# Debug endpoints for session management
@router.get("/debug/sessions")
def get_active_sessions(
    current_user: User = Depends(require_admin)
):
    """Get information about active sessions (for debugging)."""
    return {
        "active_session_count": session_manager.get_active_session_count(),
        "message": "Use this to monitor active sessions"
    }


@router.post("/debug/sessions/cleanup")
def cleanup_sessions(
    current_user: User = Depends(require_admin)
):
    """Force cleanup of expired sessions (for debugging)."""
    cleaned_up = session_manager.cleanup_expired_sessions()
    return {
        "cleaned_up_sessions": cleaned_up,
        "remaining_active_sessions": session_manager.get_active_session_count()
    }


@router.delete("/debug/users/{user_id}/sessions")
def force_delete_user_sessions(
    user_id: UUID,
    current_user: User = Depends(require_admin)
):
    """Force delete all sessions for a specific user (for debugging)."""
    deleted_sessions = session_manager.delete_user_sessions(user_id)
    return {
        "deleted_sessions": deleted_sessions,
        "user_id": str(user_id),
        "message": f"Deleted {deleted_sessions} sessions for user {user_id}"
    }