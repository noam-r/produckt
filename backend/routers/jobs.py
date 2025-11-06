"""
Jobs API endpoints for polling job status.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Job, JobStatus
from backend.repositories.job import JobRepository
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get job status for polling.

    Returns job information including:
    - status: pending, in_progress, completed, failed
    - progress_message: Human-readable progress message
    - progress_percent: Progress percentage (0-100)
    - result_data: Results when completed
    - error_message: Error message if failed

    Args:
        job_id: UUID of the job to check
        current_user: Authenticated user
        db: Database session

    Returns:
        Job status information

    Raises:
        404: Job not found
        403: Job belongs to different organization
    """
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)

    # Return 404 if job doesn't exist or belongs to different organization
    # This prevents leaking information about jobs in other organizations
    if not job or job.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return {
        "id": str(job.id),
        "job_type": job.job_type.value,
        "status": job.status.value,
        "progress_message": job.progress_message,
        "progress_percent": job.progress_percent,
        "result_data": job.result_data,
        "error_message": job.error_message,
        "error_details": job.error_details,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }


@router.get("/")
def list_jobs(
    initiative_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List jobs for the current user's organization.

    Args:
        initiative_id: Filter by initiative ID (optional)
        status: Filter by status (pending, in_progress, completed, failed) (optional)
        limit: Maximum number of jobs to return (default: 50, max: 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        List of jobs
    """
    job_repo = JobRepository(db)

    # Validate status if provided
    if status:
        try:
            status_enum = JobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Must be one of: pending, in_progress, completed, failed"
            )
    else:
        status_enum = None

    # Limit to reasonable maximum
    if limit > 100:
        limit = 100

    # Get jobs based on filters
    if initiative_id:
        # Verify user has access to initiative
        from backend.repositories.initiative import InitiativeRepository
        initiative_repo = InitiativeRepository(db)
        initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

        if not initiative:
            raise HTTPException(
                status_code=404,
                detail=f"Initiative {initiative_id} not found"
            )

        # Get jobs for specific initiative
        from sqlalchemy import select
        query = select(Job).where(
            Job.initiative_id == initiative_id,
            Job.organization_id == current_user.organization_id
        )

        if status_enum:
            query = query.where(Job.status == status_enum)

        query = query.order_by(Job.created_at.desc()).limit(limit)
        result = db.execute(query)
        jobs = list(result.scalars().all())
    else:
        # Get all jobs for organization
        from sqlalchemy import select
        query = select(Job).where(
            Job.organization_id == current_user.organization_id
        )

        if status_enum:
            query = query.where(Job.status == status_enum)

        query = query.order_by(Job.created_at.desc()).limit(limit)
        result = db.execute(query)
        jobs = list(result.scalars().all())

    return {
        "jobs": [
            {
                "id": str(job.id),
                "job_type": job.job_type.value,
                "status": job.status.value,
                "progress_message": job.progress_message,
                "progress_percent": job.progress_percent,
                "initiative_id": str(job.initiative_id) if job.initiative_id else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ],
        "count": len(jobs)
    }
