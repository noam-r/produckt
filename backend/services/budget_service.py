"""
Budget service for managing user spending limits and cost tracking.
"""

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.user_monthly_spending import UserMonthlySpending
from backend.models.llmcall import LLMCall
from backend.services.exceptions import BudgetExceededError


class BudgetCheckResult(NamedTuple):
    """Result of checking if a user can afford an operation."""
    can_afford: bool
    current_spending: Decimal
    budget_limit: Decimal
    estimated_cost: Decimal
    remaining_budget: Decimal


class BudgetStatus(NamedTuple):
    """Comprehensive budget status for a user."""
    user_id: UUID
    monthly_budget: Decimal
    current_spending: Decimal
    remaining_budget: Decimal
    utilization_percentage: float
    year: int
    month: int


class BudgetService:
    """Service for managing user budgets and tracking spending."""

    def __init__(self, db: Session):
        self.db = db

    def get_monthly_spending(self, user_id: UUID, year: int, month: int) -> Decimal:
        """Get user's spending for a specific month."""
        spending_record = (
            self.db.query(UserMonthlySpending)
            .filter(
                UserMonthlySpending.user_id == user_id,
                UserMonthlySpending.year == year,
                UserMonthlySpending.month == month
            )
            .first()
        )
        
        if spending_record:
            return spending_record.total_spent_usd
        return Decimal('0.00')

    def get_current_month_spending(self, user_id: UUID) -> Decimal:
        """Get user's spending for current calendar month."""
        now = datetime.utcnow()
        return self.get_monthly_spending(user_id, now.year, now.month)

    def check_budget_limit(self, user_id: UUID, estimated_cost: Decimal) -> BudgetCheckResult:
        """Check if user can afford an operation."""
        # Get user's budget
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        budget_limit = user.monthly_budget_usd
        current_spending = self.get_current_month_spending(user_id)
        remaining_budget = budget_limit - current_spending
        
        can_afford = (current_spending + estimated_cost) <= budget_limit
        
        return BudgetCheckResult(
            can_afford=can_afford,
            current_spending=current_spending,
            budget_limit=budget_limit,
            estimated_cost=estimated_cost,
            remaining_budget=remaining_budget
        )

    def check_budget_limit_or_raise(self, user_id: UUID, estimated_cost: Decimal) -> None:
        """Check if user can afford an operation, raise BudgetExceededError if not."""
        result = self.check_budget_limit(user_id, estimated_cost)
        
        if not result.can_afford:
            raise BudgetExceededError(
                current_spending=result.current_spending,
                budget_limit=result.budget_limit,
                estimated_cost=result.estimated_cost,
                user_id=str(user_id)
            )

    def record_spending(self, user_id: UUID, amount: Decimal, llm_call_id: UUID) -> None:
        """Record spending against user's monthly budget."""
        now = datetime.utcnow()
        year, month = now.year, now.month
        
        # Get or create monthly spending record
        spending_record = (
            self.db.query(UserMonthlySpending)
            .filter(
                UserMonthlySpending.user_id == user_id,
                UserMonthlySpending.year == year,
                UserMonthlySpending.month == month
            )
            .first()
        )
        
        if not spending_record:
            spending_record = UserMonthlySpending(
                user_id=user_id,
                year=year,
                month=month,
                total_spent_usd=Decimal('0.00')
            )
            self.db.add(spending_record)
        
        # Add the new spending
        spending_record.total_spent_usd += amount
        
        # Commit the changes
        self.db.commit()

    def update_user_budget(self, user_id: UUID, new_budget: Decimal, updated_by: UUID) -> None:
        """Update user's monthly budget (admin only)."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate budget range (as per requirements)
        if new_budget < Decimal('0.00') or new_budget > Decimal('10000.00'):
            raise ValueError("Budget must be between $0.00 and $10,000.00")
        
        # Store old budget for notification
        old_budget = user.monthly_budget_usd
        
        user.monthly_budget_usd = new_budget
        user.budget_updated_at = datetime.utcnow()
        user.budget_updated_by = updated_by
        
        self.db.commit()
        
        # Send notification about budget change
        from backend.services.notification_service import NotificationService
        notification_service = NotificationService(self.db)
        notification_service.notify_budget_updated(
            user_id=user_id,
            old_budget=old_budget,
            new_budget=new_budget,
            updated_by_admin=True
        )

    def get_budget_status(self, user_id: UUID) -> BudgetStatus:
        """Get comprehensive budget status for user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        now = datetime.utcnow()
        current_spending = self.get_current_month_spending(user_id)
        remaining_budget = user.monthly_budget_usd - current_spending
        
        # Calculate utilization percentage
        if user.monthly_budget_usd > 0:
            utilization_percentage = float(current_spending / user.monthly_budget_usd * 100)
        else:
            utilization_percentage = 0.0
        
        return BudgetStatus(
            user_id=user_id,
            monthly_budget=user.monthly_budget_usd,
            current_spending=current_spending,
            remaining_budget=remaining_budget,
            utilization_percentage=utilization_percentage,
            year=now.year,
            month=now.month
        )

    def get_budget_status_with_warnings(self, user_id: UUID) -> dict:
        """Get comprehensive budget status with warnings."""
        budget_status = self.get_budget_status(user_id)
        
        from backend.services.notification_service import NotificationService
        notification_service = NotificationService(self.db)
        
        return notification_service.get_budget_status_with_warnings(
            user_id=user_id,
            current_spending=budget_status.current_spending,
            budget_limit=budget_status.monthly_budget
        )