"""
Job repository for managing async background jobs.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Job, JobStatus, JobType
from backend.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for Job operations."""

    def __init__(self, db: Session):
        """Initialize JobRepository with Job model."""
        super().__init__(Job, db)

    def get_by_id(self, job_id: UUID, organization_id: UUID) -> Optional[Job]:
        """
        Get job by ID with organization filtering.
        
        Args:
            job_id: Job ID
            organization_id: Organization ID for security filtering
            
        Returns:
            Job if found and belongs to organization, None otherwise
        """
        query = select(Job).where(
            Job.id == job_id,
            Job.organization_id == organization_id
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_by_initiative_and_type(
        self,
        initiative_id: UUID,
        job_type: JobType,
        status: Optional[JobStatus] = None
    ) -> List[Job]:
        """Get jobs for an initiative by type and optionally status."""
        query = select(Job).where(
            Job.initiative_id == initiative_id,
            Job.job_type == job_type
        )

        if status:
            query = query.where(Job.status == status)

        query = query.order_by(Job.created_at.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_pending_jobs(self, limit: int = 100) -> List[Job]:
        """Get pending jobs to process."""
        query = select(Job).where(
            Job.status == JobStatus.PENDING
        ).order_by(Job.created_at).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def create_job(
        self,
        job_type: JobType,
        organization_id: UUID,
        created_by: UUID,
        initiative_id: Optional[UUID] = None
    ) -> Job:
        """Create a new job."""
        job = Job(
            job_type=job_type,
            status=JobStatus.PENDING,
            organization_id=organization_id,
            created_by=created_by,
            initiative_id=initiative_id,
            progress_percent=0  # Initialize to 0
        )
        self.db.add(job)
        self.db.flush()  # Get the ID without committing
        return job

    def update_status(
        self,
        job: Job,
        status: JobStatus,
        progress_message: Optional[str] = None,
        progress_percent: Optional[int] = None
    ) -> Job:
        """Update job status and progress."""
        job.status = status

        if progress_message is not None:
            job.progress_message = progress_message

        if progress_percent is not None:
            job.progress_percent = progress_percent

        # Update timestamps based on status
        from datetime import datetime
        if status == JobStatus.IN_PROGRESS and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.completed_at = datetime.utcnow()

        return job

    def mark_completed(
        self,
        job: Job,
        result_data: dict
    ) -> Job:
        """Mark job as completed with result data."""
        job.status = JobStatus.COMPLETED
        job.result_data = result_data
        job.progress_message = "Completed"
        job.progress_percent = 100

        from datetime import datetime
        job.completed_at = datetime.utcnow()

        return job

    def mark_failed(
        self,
        job: Job,
        error_message: str,
        error_details: Optional[dict] = None
    ) -> Job:
        """Mark job as failed with error information."""
        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.error_details = error_details

        from datetime import datetime
        job.completed_at = datetime.utcnow()

        return job

    def list_jobs_by_initiative(self, initiative_id: UUID, organization_id: UUID) -> List[Job]:
        """List all jobs for an initiative."""
        query = select(Job).where(
            Job.initiative_id == initiative_id,
            Job.organization_id == organization_id
        ).order_by(Job.created_at.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    def list_jobs_by_status(self, status: JobStatus, organization_id: UUID) -> List[Job]:
        """List all jobs with a specific status for an organization."""
        query = select(Job).where(
            Job.status == status,
            Job.organization_id == organization_id
        ).order_by(Job.created_at.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    # Internal helper method for background job processing (no org check needed)
    def _get_by_id_internal(self, job_id: UUID) -> Optional[Job]:
        """
        Internal method to get job by ID without organization filtering.
        Only used by background job processor which already has the job context.
        DO NOT use in API endpoints - use get_by_id() instead.
        """
        query = select(Job).where(Job.id == job_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    # Convenience methods for background job processing
    def complete_job(self, job_id: UUID, result_data: dict) -> Job:
        """Complete a job by ID (for background processing)."""
        job = self._get_by_id_internal(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return self.mark_completed(job, result_data)

    def fail_job(self, job_id: UUID, error_message: str, error_details: Optional[dict] = None) -> Job:
        """Fail a job by ID (for background processing)."""
        job = self._get_by_id_internal(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return self.mark_failed(job, error_message, error_details)

    def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress_percent: Optional[int] = None,
        progress_message: Optional[str] = None
    ) -> Job:
        """Update job status by ID (for background processing)."""
        job = self._get_by_id_internal(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        return self.update_status(job, status, progress_message, progress_percent)
