"""
Notification service for user notifications and budget warnings.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.models.user import User


class NotificationService:
    """Service for managing user notifications."""

    def __init__(self, db: Session):
        self.db = db

    def notify_budget_updated(
        self, 
        user_id: UUID, 
        old_budget: Decimal, 
        new_budget: Decimal,
        updated_by_admin: bool = True
    ) -> None:
        """
        Notify user when their budget is updated.
        
        For now, this logs the notification. In the future, this could
        send emails, push notifications, or store in a notifications table.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # For now, we'll use Python logging to record the notification
        # In a production system, this would likely store notifications in a database
        # or send them via email/push notification service
        import logging
        logger = logging.getLogger(__name__)
        
        if updated_by_admin:
            message = (
                f"Your monthly budget has been updated from ${old_budget} to ${new_budget} "
                f"by an administrator."
            )
        else:
            message = f"Your monthly budget has been updated to ${new_budget}."
        
        logger.info(f"Budget notification for user {user.email}: {message}")
        
        # TODO: In the future, implement actual notification delivery:
        # - Store in notifications table
        # - Send email notification
        # - Send push notification
        # - Add to user's notification feed

    def check_and_warn_budget_utilization(
        self, 
        user_id: UUID, 
        current_spending: Decimal, 
        budget_limit: Decimal
    ) -> Optional[str]:
        """
        Check budget utilization and return warning message if at 80% or higher.
        
        Returns:
            Warning message if user is at 80%+ utilization, None otherwise
        """
        if budget_limit <= 0:
            return None
        
        utilization_percentage = float(current_spending / budget_limit * 100)
        
        if utilization_percentage >= 80:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            remaining_budget = budget_limit - current_spending
            
            warning_message = (
                f"Budget Warning: You have used {utilization_percentage:.1f}% "
                f"of your monthly budget (${current_spending} of ${budget_limit}). "
                f"Remaining budget: ${remaining_budget}."
            )
            
            # Log the warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Budget utilization warning for user {user.email}: {warning_message}")
            
            return warning_message
        
        return None

    def get_budget_status_with_warnings(
        self, 
        user_id: UUID, 
        current_spending: Decimal, 
        budget_limit: Decimal
    ) -> dict:
        """
        Get budget status with any applicable warnings.
        
        Returns:
            Dictionary with budget status and warning information
        """
        warning_message = self.check_and_warn_budget_utilization(
            user_id, current_spending, budget_limit
        )
        
        utilization_percentage = float(current_spending / budget_limit * 100) if budget_limit > 0 else 0
        remaining_budget = budget_limit - current_spending
        
        return {
            "current_spending": current_spending,
            "budget_limit": budget_limit,
            "remaining_budget": remaining_budget,
            "utilization_percentage": utilization_percentage,
            "has_warning": warning_message is not None,
            "warning_message": warning_message,
            "is_over_budget": current_spending > budget_limit,
            "is_near_limit": utilization_percentage >= 80
        }