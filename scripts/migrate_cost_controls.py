#!/usr/bin/env python3
"""
Migration script for cost control data.

This script:
1. Verifies default budgets for existing users ($100)
2. Verifies default question limits for existing initiatives (50)
3. Initializes monthly spending records for current month
4. Backfills historical spending data from LLM calls

Requirements: 1.3, 5.1
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Use the configured database URL from environment/settings

from backend.database import SessionLocal
from backend.models.user import User
from backend.models.initiative import Initiative
from backend.models.user_monthly_spending import UserMonthlySpending
from backend.models.llmcall import LLMCall
from sqlalchemy import func, text


def migrate_cost_controls():
    """Migrate existing users and initiatives to have cost control defaults."""
    db = SessionLocal()
    try:
        print("="*70)
        print("Cost Control Data Migration")
        print("="*70)

        # Step 1: Verify and update user budgets
        print("\n1. Verifying user budget defaults...")
        users_updated = ensure_user_budgets(db)
        print(f"   ✓ {users_updated} users verified/updated with $100 default budget")

        # Step 2: Verify and update initiative question limits
        print("\n2. Verifying initiative question limits...")
        initiatives_updated = ensure_initiative_limits(db)
        print(f"   ✓ {initiatives_updated} initiatives verified/updated with 50 question limit")

        # Step 3: Initialize current month spending records
        print("\n3. Initializing current month spending records...")
        current_records = initialize_current_month_spending(db)
        print(f"   ✓ {current_records} current month spending records initialized")

        # Step 4: Backfill historical spending data
        print("\n4. Backfilling historical spending data...")
        historical_records = backfill_historical_spending(db)
        print(f"   ✓ {historical_records} historical spending records created")

        # Step 5: Summary report
        print("\n" + "="*70)
        print("Migration Summary")
        print("="*70)
        
        # Use raw SQL to avoid column issues
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        total_initiatives = db.execute(text("SELECT COUNT(*) FROM initiatives")).scalar()
        
        try:
            total_spending_records = db.query(UserMonthlySpending).count()
        except Exception:
            total_spending_records = 0
        
        print(f"Total users with budgets:           {total_users}")
        print(f"Total initiatives with limits:      {total_initiatives}")
        print(f"Total monthly spending records:     {total_spending_records}")
        
        # Show budget distribution
        try:
            budget_stats = db.query(
                User.monthly_budget_usd,
                func.count(User.id).label('count')
            ).group_by(User.monthly_budget_usd).all()
            
            print(f"\nBudget distribution:")
            for budget, count in budget_stats:
                print(f"  ${budget}: {count} users")
        except Exception:
            print(f"\nBudget distribution: Not available (columns not migrated)")
        
        # Show question limit distribution
        try:
            limit_stats = db.query(
                Initiative.max_questions,
                func.count(Initiative.id).label('count')
            ).group_by(Initiative.max_questions).all()
            
            print(f"\nQuestion limit distribution:")
            for limit, count in limit_stats:
                print(f"  {limit} questions: {count} initiatives")
        except Exception:
            print(f"\nQuestion limit distribution: Not available (columns not migrated)")

        print("\n" + "="*70)
        print("Cost Control Migration Complete!")
        print("="*70)

        db.commit()

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def ensure_user_budgets(db) -> int:
    """Ensure all users have the default $100 budget."""
    try:
        # Check if budget columns exist by trying to query them
        users_without_budget = db.query(User).filter(
            (User.monthly_budget_usd == None) | (User.monthly_budget_usd == 0)
        ).all()
        
        updated_count = 0
        for user in users_without_budget:
            user.monthly_budget_usd = Decimal('100.00')
            updated_count += 1
        
        if updated_count > 0:
            db.commit()
        
        return updated_count
    except Exception as e:
        error_msg = str(e).lower()
        if ("column" in error_msg and ("not" in error_msg or "unknown" in error_msg)) or "no such column" in error_msg:
            print(f"   - Budget columns not found, need to run migrations first")
            print(f"   - Run: alembic upgrade head")
            return 0
        else:
            raise


def ensure_initiative_limits(db) -> int:
    """Ensure all initiatives have the default 50 question limit."""
    try:
        # Check if question limit columns exist by trying to query them
        initiatives_without_limit = db.query(Initiative).filter(
            (Initiative.max_questions == None) | (Initiative.max_questions == 0)
        ).all()
        
        updated_count = 0
        for initiative in initiatives_without_limit:
            initiative.max_questions = 50
            updated_count += 1
        
        if updated_count > 0:
            db.commit()
        
        return updated_count
    except Exception as e:
        error_msg = str(e).lower()
        if ("column" in error_msg and ("not" in error_msg or "unknown" in error_msg)) or "no such column" in error_msg:
            print(f"   - Question limit columns not found, need to run migrations first")
            return 0
        else:
            raise


def initialize_current_month_spending(db) -> int:
    """Initialize spending records for current month for all users."""
    try:
        current_date = date.today()
        current_year = current_date.year
        current_month = current_date.month
        
        # Get all users
        all_users = db.query(User).all()
        
        created_count = 0
        for user in all_users:
            # Check if spending record already exists for current month
            existing_record = db.query(UserMonthlySpending).filter(
                UserMonthlySpending.user_id == user.id,
                UserMonthlySpending.year == current_year,
                UserMonthlySpending.month == current_month
            ).first()
            
            if not existing_record:
                # Create new spending record for current month
                spending_record = UserMonthlySpending(
                    user_id=user.id,
                    year=current_year,
                    month=current_month,
                    total_spent_usd=Decimal('0.00')
                )
                db.add(spending_record)
                created_count += 1
        
        if created_count > 0:
            db.commit()
        
        return created_count
    except Exception as e:
        error_msg = str(e).lower()
        if ("table" in error_msg and ("not" in error_msg or "unknown" in error_msg)) or "no such table" in error_msg:
            print(f"   - UserMonthlySpending table not found, need to run migrations first")
            return 0
        else:
            raise


def backfill_historical_spending(db) -> int:
    """Backfill historical spending data from LLM calls."""
    try:
        # Get all LLM calls with costs and user attribution
        llm_calls = db.query(LLMCall).filter(
            LLMCall.user_id.isnot(None),
            LLMCall.cost_usd > 0
        ).all()
        
        if not llm_calls:
            print(f"   - No LLM calls found with cost data")
            return 0
        
        # Group spending by user, year, month
        spending_by_month = defaultdict(lambda: Decimal('0.00'))
        
        for call in llm_calls:
            call_date = call.created_at.date()
            year = call_date.year
            month = call_date.month
            user_id = call.user_id
            cost = Decimal(str(call.cost_usd))
            
            spending_by_month[(user_id, year, month)] += cost
        
        created_count = 0
        updated_count = 0
        
        for (user_id, year, month), total_cost in spending_by_month.items():
            # Check if spending record already exists
            existing_record = db.query(UserMonthlySpending).filter(
                UserMonthlySpending.user_id == user_id,
                UserMonthlySpending.year == year,
                UserMonthlySpending.month == month
            ).first()
            
            if existing_record:
                # Update existing record if our calculated total is higher
                if total_cost > existing_record.total_spent_usd:
                    existing_record.total_spent_usd = total_cost
                    updated_count += 1
            else:
                # Create new spending record
                spending_record = UserMonthlySpending(
                    user_id=user_id,
                    year=year,
                    month=month,
                    total_spent_usd=total_cost
                )
                db.add(spending_record)
                created_count += 1
        
        if created_count > 0 or updated_count > 0:
            db.commit()
        
        print(f"   - Created {created_count} new historical records")
        print(f"   - Updated {updated_count} existing records")
        
        return created_count
    except Exception as e:
        error_msg = str(e).lower()
        if ("table" in error_msg and ("not" in error_msg or "unknown" in error_msg)) or "no such table" in error_msg:
            print(f"   - UserMonthlySpending table not found, need to run migrations first")
            return 0
        else:
            raise


if __name__ == "__main__":
    migrate_cost_controls()