"""
Job model - tracks async background tasks.
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime, Index, JSON, Integer
from sqlalchemy.orm import relationship
from backend.models.utils import GUID

from backend.database import Base


class JobStatus(str, enum.Enum):
    """Job execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    """Type of background job."""
    GENERATE_QUESTIONS = "generate_questions"
    GENERATE_MRD = "generate_mrd"
    EVALUATE_READINESS = "evaluate_readiness"


class Job(Base):
    """
    Async job for long-running operations.

    Tracks status and results of background tasks like question generation,
    MRD generation, and readiness evaluation.
    """
    __tablename__ = "jobs"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Job metadata
    job_type = Column(Enum(JobType), nullable=False, index=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)

    # Progress tracking
    progress_message = Column(String(500), nullable=True)  # e.g., "Analyzing knowledge gaps..."
    progress_percent = Column(Integer, nullable=True)  # 0-100 or None

    # References
    organization_id = Column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    initiative_id = Column(
        GUID,
        ForeignKey("initiatives.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    created_by = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Result data (stored as JSON when complete)
    result_data = Column(JSON, nullable=True)

    # Error info (if failed)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    initiative = relationship("Initiative", foreign_keys=[initiative_id])
    created_by_user = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index('ix_jobs_org_status', 'organization_id', 'status'),
        Index('ix_jobs_initiative', 'initiative_id'),
        Index('ix_jobs_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Job(id={self.id}, type={self.job_type.value}, status={self.status.value})>"
