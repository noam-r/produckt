#!/usr/bin/env python3
"""
Simple migration script for cost control data (SQLite compatible).

This script manually adds the cost control columns and tables for testing purposes.
For production, use the proper Alembic migrations.

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

# Override database URL to use SQLite for migration
os.environ['DATABASE_URL'] = 'sqlite:///./produck.db'

from backend.database import SessionLocal, engine
from backend.models.user import User
from backend.models.initiative import Initiative
from backend.models.llmcall import LLMCall
from sqlalchemy import text


def migrate_cost_controls_simple():
    """Simple migration for cost control features."""
    db = SessionLocal()
    try:
        print("="*70)
        print("Simple Cost Control Data Migration")
        print("="*70)

        # Step 1: Add budget columns to users table if they don't exist
        print("\n1. Adding budget columns to users table...")
        add_user_budget_columns(db)

        # Step 2: Add question limit columns to initiatives table if they don't exist
        print("\n2. Adding question limit columns to initiatives table...")
        add_initiative_limit_columns(db)

        # Step 3: Create user_monthly_spending table if it doesn't exist
        print("\n3. Creating user_monthly_spending table...")
        create_monthly_spending_table(db)

        # Step 4: Set default values for existing users and initiatives
        print("\n4. Setting default values...")
        set_default_values(db)

        # Step 5: Initialize current month spending records
        print("\n5. Initializing current month spending records...")
        initialize_current_month_spending(db)

        # Step 6: Backfill historical spending data
        print("\n6. Backfilling historical spending data...")
        backfill_historical_spending(db)

        print("\n" + "="*70)
        print("Simple Cost Control Migration Complete!")
        print("="*70)

        db.commit()

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def add_user_budget_columns(db):
    """Add budget columns to users table."""
    try:
        # Check if columns already exist
        result = db.execute(text("PRAGMA table_info(users)")).fetchall()
        columns = [row[1] for row in result]
        
        if 'monthly_budget_usd' not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN monthly_budget_usd DECIMAL(10,2) DEFAULT 100.00"))
            print("   ✓ Added monthly_budget_usd column")
        else:
            print("   ✓ monthly_budget_usd column already exists")
            
        if 'budget_updated_at' not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN budget_updated_at DATETIME"))
            print("   ✓ Added budget_updated_at column")
        else:
            print("   ✓ budget_updated_at column already exists")
            
        if 'budget_updated_by' not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN budget_updated_by VARCHAR(36)"))
            print("   ✓ Added budget_updated_by column")
        else:
            print("   ✓ budget_updated_by column already exists")
            
        db.commit()
    except Exception as e:
        print(f"   ✗ Error adding user budget columns: {e}")
        raise


def add_initiative_limit_columns(db):
    """Add question limit columns to initiatives table."""
    try:
        # Check if columns already exist
        result = db.execute(text("PRAGMA table_info(initiatives)")).fetchall()
        columns = [row[1] for row in result]
        
        if 'max_questions' not in columns:
            db.execute(text("ALTER TABLE initiatives ADD COLUMN max_questions INTEGER DEFAULT 50"))
            print("   ✓ Added max_questions column")
        else:
            print("   ✓ max_questions column already exists")
            
        if 'max_questions_updated_at' not in columns:
            db.execute(text("ALTER TABLE initiatives ADD COLUMN max_questions_updated_at DATETIME"))
            print("   ✓ Added max_questions_updated_at column")
        else:
            print("   ✓ max_questions_updated_at column already exists")
            
        if 'max_questions_updated_by' not in columns:
            db.execute(text("ALTER TABLE initiatives ADD COLUMN max_questions_updated_by VARCHAR(36)"))
            print("   ✓ Added max_questions_updated_by column")
        else:
            print("   ✓ max_questions_updated_by column already exists")
            
        db.commit()
    except Exception as e:
        print(f"   ✗ Error adding initiative limit columns: {e}")
        raise


def create_monthly_spending_table(db):
    """Create user_monthly_spending table."""
    try:
        # Check if table already exists
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_monthly_spending'")).fetchone()
        
        if not result:
            db.execute(text("""
                CREATE TABLE user_monthly_spending (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    total_spent_usd DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, year, month)
                )
            """))
            
            # Create index
            db.execute(text("CREATE INDEX ix_user_monthly_spending_user_month ON user_monthly_spending(user_id, year, month)"))
            
            print("   ✓ Created user_monthly_spending table")
            db.commit()
        else:
            print("   ✓ user_monthly_spending table already exists")
    except Exception as e:
        print(f"   ✗ Error creating monthly spending table: {e}")
        raise


def set_default_values(db):
    """Set default values for existing users and initiatives."""
    try:
        # Set default budgets for users without them
        result = db.execute(text("UPDATE users SET monthly_budget_usd = 100.00 WHERE monthly_budget_usd IS NULL OR monthly_budget_usd = 0"))
        print(f"   ✓ Updated {result.rowcount} users with default $100 budget")
        
        # Set default question limits for initiatives without them
        result = db.execute(text("UPDATE initiatives SET max_questions = 50 WHERE max_questions IS NULL OR max_questions = 0"))
        print(f"   ✓ Updated {result.rowcount} initiatives with default 50 question limit")
        
        db.commit()
    except Exception as e:
        print(f"   ✗ Error setting default values: {e}")
        raise


def initialize_current_month_spending(db):
    """Initialize spending records for current month for all users."""
    try:
        current_date = date.today()
        current_year = current_date.year
        current_month = current_date.month
        
        # Get all user IDs
        users = db.execute(text("SELECT id FROM users")).fetchall()
        
        created_count = 0
        for user_row in users:
            user_id = user_row[0]
            
            # Check if spending record already exists for current month
            existing = db.execute(text("""
                SELECT id FROM user_monthly_spending 
                WHERE user_id = :user_id AND year = :year AND month = :month
            """), {"user_id": user_id, "year": current_year, "month": current_month}).fetchone()
            
            if not existing:
                # Create new spending record for current month
                import uuid
                record_id = str(uuid.uuid4())
                now = datetime.utcnow()
                
                db.execute(text("""
                    INSERT INTO user_monthly_spending (id, user_id, year, month, total_spent_usd, created_at, updated_at)
                    VALUES (:id, :user_id, :year, :month, 0.00, :created_at, :updated_at)
                """), {
                    "id": record_id,
                    "user_id": user_id,
                    "year": current_year,
                    "month": current_month,
                    "created_at": now,
                    "updated_at": now
                })
                created_count += 1
        
        print(f"   ✓ Created {created_count} current month spending records")
        db.commit()
    except Exception as e:
        print(f"   ✗ Error initializing current month spending: {e}")
        raise


def backfill_historical_spending(db):
    """Backfill historical spending data from LLM calls."""
    try:
        # Get all LLM calls with costs and user attribution
        llm_calls = db.execute(text("""
            SELECT user_id, cost_usd, created_at 
            FROM llm_calls 
            WHERE user_id IS NOT NULL AND cost_usd > 0
        """)).fetchall()
        
        if not llm_calls:
            print("   ✓ No LLM calls found with cost data")
            return
        
        # Group spending by user, year, month
        spending_by_month = defaultdict(lambda: Decimal('0.00'))
        
        for call in llm_calls:
            user_id, cost_usd, created_at = call
            call_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
            year = call_date.year
            month = call_date.month
            cost = Decimal(str(cost_usd))
            
            spending_by_month[(user_id, year, month)] += cost
        
        created_count = 0
        updated_count = 0
        
        for (user_id, year, month), total_cost in spending_by_month.items():
            # Check if spending record already exists
            existing = db.execute(text("""
                SELECT id, total_spent_usd FROM user_monthly_spending 
                WHERE user_id = :user_id AND year = :year AND month = :month
            """), {"user_id": user_id, "year": year, "month": month}).fetchone()
            
            if existing:
                # Update existing record if our calculated total is higher
                existing_id, existing_total = existing
                if total_cost > Decimal(str(existing_total)):
                    db.execute(text("""
                        UPDATE user_monthly_spending 
                        SET total_spent_usd = :total_cost, updated_at = :updated_at
                        WHERE id = :id
                    """), {
                        "total_cost": float(total_cost),
                        "updated_at": datetime.utcnow(),
                        "id": existing_id
                    })
                    updated_count += 1
            else:
                # Create new spending record
                import uuid
                record_id = str(uuid.uuid4())
                now = datetime.utcnow()
                
                db.execute(text("""
                    INSERT INTO user_monthly_spending (id, user_id, year, month, total_spent_usd, created_at, updated_at)
                    VALUES (:id, :user_id, :year, :month, :total_cost, :created_at, :updated_at)
                """), {
                    "id": record_id,
                    "user_id": user_id,
                    "year": year,
                    "month": month,
                    "total_cost": float(total_cost),
                    "created_at": now,
                    "updated_at": now
                })
                created_count += 1
        
        print(f"   ✓ Created {created_count} new historical records")
        print(f"   ✓ Updated {updated_count} existing records")
        
        db.commit()
    except Exception as e:
        print(f"   ✗ Error backfilling historical spending: {e}")
        raise


if __name__ == "__main__":
    migrate_cost_controls_simple()