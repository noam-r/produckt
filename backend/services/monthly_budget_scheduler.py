"""
Monthly budget reset scheduler service.

This service handles scheduling and creating monthly budget reset jobs.
It can be called by cron jobs, admin endpoints, or other scheduling mechanisms.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.job import Job, JobType, JobStatus
from backend.models.organization import Organization
from backend.repositories.job import JobRepository

logger = logging.getLogger(__name__)


class MonthlyBudgetScheduler:
    """Service for scheduling monthly budget reset jobs."""

    def __init__(self, db: Session):
        self.db = db

    def schedule_monthly_reset(self, organization_id: Optional[UUID] = None) -> Job:
        """
        Schedule a monthly budget reset job.
        
        Args:
            organization_id: Optional organization ID. If None, uses system organization.
            
        Returns:
            Created job instance
        """
        # Get system organization if none specified
        if organization_id is None:
            # Use the first organization as system org (or create logic to identify system org)
            system_org = self.db.query(Organization).first()
            if not system_org:
                raise ValueError("No organization found for system operations")
            organization_id = system_org.id

        # Check if there's already a pending or in-progress monthly reset job
        job_repo = JobRepository(self.db)
        existing_job = (
            self.db.query(Job)
            .filter(
                Job.job_type == JobType.MONTHLY_BUDGET_RESET,
                Job.organization_id == organization_id,
                Job.status.in_([JobStatus.PENDING, JobStatus.IN_PROGRESS])
            )
            .first()
        )

        if existing_job:
            logger.info(f"Monthly budget reset job already exists: {existing_job.id}")
            return existing_job

        # Create new monthly reset job
        job = Job(
            job_type=JobType.MONTHLY_BUDGET_RESET,
            organization_id=organization_id,
            initiative_id=None,  # System-level job, not tied to specific initiative
            created_by=None,  # System job
            progress_message="Scheduled for execution",
            progress_percent=0
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Scheduled monthly budget reset job: {job.id}")
        return job

    def should_schedule_reset(self) -> bool:
        """
        Check if a monthly reset should be scheduled.
        
        This checks if we're in a new month and haven't already scheduled a reset.
        
        Returns:
            True if reset should be scheduled
        """
        now = datetime.utcnow()
        
        # Check if there's already a job for this month
        existing_job = (
            self.db.query(Job)
            .filter(
                Job.job_type == JobType.MONTHLY_BUDGET_RESET,
                Job.created_at >= datetime(now.year, now.month, 1),  # This month
                Job.status != JobStatus.FAILED  # Ignore failed jobs
            )
            .first()
        )

        return existing_job is None

    def schedule_if_needed(self, organization_id: Optional[UUID] = None) -> Optional[Job]:
        """
        Schedule monthly reset if needed.
        
        Args:
            organization_id: Optional organization ID
            
        Returns:
            Job if scheduled, None if not needed
        """
        if self.should_schedule_reset():
            return self.schedule_monthly_reset(organization_id)
        return None

    def get_last_reset_job(self) -> Optional[Job]:
        """
        Get the most recent monthly budget reset job.
        
        Returns:
            Most recent reset job or None
        """
        return (
            self.db.query(Job)
            .filter(Job.job_type == JobType.MONTHLY_BUDGET_RESET)
            .order_by(Job.created_at.desc())
            .first()
        )

    def cleanup_old_reset_jobs(self, months_to_keep: int = 12) -> int:
        """
        Clean up old monthly reset jobs to prevent database bloat.
        
        Args:
            months_to_keep: Number of months of job history to keep
            
        Returns:
            Number of jobs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=months_to_keep * 30)
        
        deleted_count = (
            self.db.query(Job)
            .filter(
                Job.job_type == JobType.MONTHLY_BUDGET_RESET,
                Job.created_at < cutoff_date,
                Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])  # Only delete finished jobs
            )
            .delete()
        )
        
        self.db.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old monthly reset jobs")
        
        return deleted_count