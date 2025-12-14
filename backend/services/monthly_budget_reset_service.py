"""
Monthly budget reset service for handling month rollover operations.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.user_monthly_spending import UserMonthlySpending

logger = logging.getLogger(__name__)


class MonthlyBudgetResetService:
    """Service for handling monthly budget reset operations."""

    def __init__(self, db: Session):
        self.db = db

    def reset_monthly_budgets(self, target_year: int, target_month: int) -> Dict[str, int]:
        """
        Reset spending counters for the new month while preserving historical data.
        
        Args:
            target_year: Year for the new month
            target_month: Month (1-12) for the new month
            
        Returns:
            Dictionary with reset statistics
        """
        logger.info(f"Starting monthly budget reset for {target_year}-{target_month:02d}")
        
        # Get all users who have spending records
        users_with_spending = (
            self.db.query(User.id)
            .join(UserMonthlySpending)
            .distinct()
            .all()
        )
        
        # Also get all users (in case some don't have spending records yet)
        all_users = self.db.query(User.id).all()
        
        # Combine and deduplicate
        all_user_ids = set([user.id for user in all_users] + [user.id for user in users_with_spending])
        
        reset_count = 0
        created_count = 0
        
        for user_id in all_user_ids:
            # Check if spending record already exists for the target month
            existing_record = (
                self.db.query(UserMonthlySpending)
                .filter(
                    UserMonthlySpending.user_id == user_id,
                    UserMonthlySpending.year == target_year,
                    UserMonthlySpending.month == target_month
                )
                .first()
            )
            
            if existing_record:
                # Reset existing record to zero (preserving the record structure)
                if existing_record.total_spent_usd != Decimal('0.00'):
                    existing_record.total_spent_usd = Decimal('0.00')
                    reset_count += 1
                    logger.debug(f"Reset spending for user {user_id} to $0.00")
            else:
                # Create new spending record for the month
                new_record = UserMonthlySpending(
                    user_id=user_id,
                    year=target_year,
                    month=target_month,
                    total_spent_usd=Decimal('0.00')
                )
                self.db.add(new_record)
                created_count += 1
                logger.debug(f"Created new spending record for user {user_id}")
        
        # Commit all changes
        self.db.commit()
        
        result = {
            'users_processed': len(all_user_ids),
            'records_reset': reset_count,
            'records_created': created_count,
            'target_year': target_year,
            'target_month': target_month
        }
        
        logger.info(f"Monthly budget reset completed: {result}")
        return result

    def get_previous_month_spending_summary(self, year: int, month: int) -> Dict[str, any]:
        """
        Get summary of spending for the previous month.
        
        Args:
            year: Current year
            month: Current month (1-12)
            
        Returns:
            Dictionary with spending summary for previous month
        """
        # Calculate previous month
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        
        # Get spending summary for previous month
        spending_summary = (
            self.db.query(
                func.count(UserMonthlySpending.user_id).label('users_with_spending'),
                func.sum(UserMonthlySpending.total_spent_usd).label('total_spending'),
                func.avg(UserMonthlySpending.total_spent_usd).label('average_spending'),
                func.max(UserMonthlySpending.total_spent_usd).label('max_spending')
            )
            .filter(
                UserMonthlySpending.year == prev_year,
                UserMonthlySpending.month == prev_month,
                UserMonthlySpending.total_spent_usd > 0
            )
            .first()
        )
        
        return {
            'previous_year': prev_year,
            'previous_month': prev_month,
            'users_with_spending': spending_summary.users_with_spending or 0,
            'total_spending': float(spending_summary.total_spending or Decimal('0.00')),
            'average_spending': float(spending_summary.average_spending or Decimal('0.00')),
            'max_spending': float(spending_summary.max_spending or Decimal('0.00'))
        }

    def should_run_reset(self, current_year: int, current_month: int) -> bool:
        """
        Check if monthly reset should run for the given month.
        
        This checks if we've already processed the reset for this month
        by looking for any spending records for the current month.
        
        Args:
            current_year: Current year
            current_month: Current month (1-12)
            
        Returns:
            True if reset should run, False if already processed
        """
        # Check if any spending records exist for the current month
        existing_records = (
            self.db.query(UserMonthlySpending)
            .filter(
                UserMonthlySpending.year == current_year,
                UserMonthlySpending.month == current_month
            )
            .count()
        )
        
        # If no records exist, we should run the reset
        # If records exist, we've already processed this month
        return existing_records == 0

    def cleanup_old_spending_records(self, months_to_keep: int = 24) -> int:
        """
        Clean up old spending records to prevent database bloat.
        
        Args:
            months_to_keep: Number of months of history to preserve
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=months_to_keep * 30)
        cutoff_year = cutoff_date.year
        cutoff_month = cutoff_date.month
        
        # Delete records older than the cutoff
        deleted_count = (
            self.db.query(UserMonthlySpending)
            .filter(
                (UserMonthlySpending.year < cutoff_year) |
                (
                    (UserMonthlySpending.year == cutoff_year) &
                    (UserMonthlySpending.month < cutoff_month)
                )
            )
            .delete()
        )
        
        self.db.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old spending records (older than {months_to_keep} months)")
        
        return deleted_count