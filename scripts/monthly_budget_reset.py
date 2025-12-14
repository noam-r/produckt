#!/usr/bin/env python3
"""
Monthly budget reset CLI script.

This script can be called by cron jobs or other scheduling systems to trigger
monthly budget resets. It schedules the reset job which will be executed by
the background job worker.

Usage:
    python scripts/monthly_budget_reset.py [--force]

Options:
    --force    Force scheduling even if a reset job already exists for this month
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database import SessionLocal
from backend.services.monthly_budget_scheduler import MonthlyBudgetScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function for monthly budget reset CLI."""
    parser = argparse.ArgumentParser(description='Schedule monthly budget reset job')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force scheduling even if a reset job already exists for this month'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Also cleanup old jobs and spending records'
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        scheduler = MonthlyBudgetScheduler(db)
        
        # Check if reset is needed (unless forced)
        if not args.force and not scheduler.should_schedule_reset():
            logger.info("Monthly budget reset not needed - already scheduled for this month")
            return 0
        
        # Schedule the reset job
        if args.force:
            logger.info("Forcing monthly budget reset job creation")
            job = scheduler.schedule_monthly_reset()
        else:
            job = scheduler.schedule_if_needed()
        
        if job:
            logger.info(f"Monthly budget reset job scheduled: {job.id}")
            print(f"SUCCESS: Monthly budget reset job scheduled with ID: {job.id}")
        else:
            logger.info("Monthly budget reset job was not needed")
            print("INFO: Monthly budget reset job was not needed")
        
        # Cleanup old jobs if requested
        if args.cleanup:
            logger.info("Cleaning up old jobs and records")
            job_cleanup_count = scheduler.cleanup_old_reset_jobs(months_to_keep=12)
            
            # Also cleanup old spending records
            from backend.services.monthly_budget_reset_service import MonthlyBudgetResetService
            reset_service = MonthlyBudgetResetService(db)
            record_cleanup_count = reset_service.cleanup_old_spending_records(months_to_keep=24)
            
            logger.info(f"Cleanup completed: {job_cleanup_count} jobs, {record_cleanup_count} spending records")
            print(f"CLEANUP: Removed {job_cleanup_count} old jobs and {record_cleanup_count} old spending records")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error scheduling monthly budget reset: {e}", exc_info=True)
        print(f"ERROR: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())