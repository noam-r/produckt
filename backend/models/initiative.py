"""
Initiative model - core entity for product ideas.
"""

import enum
import uuid
from sqlalchemy import Column, String, Text, Integer, Enum, ForeignKey, Index, DateTime
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin


class InitiativeStatus(str, enum.Enum):
    """Initiative lifecycle status."""
    DRAFT = "Draft"
    IN_QA = "In_QA"
    READY = "Ready"
    MRD_GENERATED = "MRD_Generated"
    SCORED = "Scored"
    ARCHIVED = "Archived"


class Initiative(Base, TimestampMixin):
    """
    Initiative represents a product idea going through the MRD process.
    """
    __tablename__ = "initiatives"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Basic info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Status and readiness
    status = Column(Enum(InitiativeStatus), nullable=False, default=InitiativeStatus.DRAFT)
    readiness_score = Column(Integer, nullable=True)  # 0-100
    iteration_count = Column(Integer, default=0, nullable=False)  # Max 3

    # Organization and creator
    organization_id = Column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_by = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Context snapshot (stored at initiative creation)
    context_snapshot_id = Column(
        GUID,
        ForeignKey("contexts.id", ondelete="SET NULL"),
        nullable=True
    )

    # Question limit fields
    max_questions = Column(Integer, nullable=False, default=50)
    max_questions_updated_at = Column(DateTime, nullable=True)
    max_questions_updated_by = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="initiatives")
    created_by_user = relationship("User", back_populates="initiatives", foreign_keys=[created_by])
    context_snapshot = relationship("Context", foreign_keys=[context_snapshot_id])
    questions = relationship("Question", back_populates="initiative", cascade="all, delete-orphan")
    mrd = relationship("MRD", back_populates="initiative", uselist=False, cascade="all, delete-orphan")
    score = relationship("Score", back_populates="initiative", uselist=False, cascade="all, delete-orphan")
    evaluation = relationship("Evaluation", back_populates="initiative", uselist=False, cascade="all, delete-orphan")
    max_questions_updated_by_user = relationship("User", foreign_keys=[max_questions_updated_by])

    # Indexes
    __table_args__ = (
        Index('ix_initiatives_org_status', 'organization_id', 'status'),
        Index('ix_initiatives_created_by', 'created_by'),
    )

    def __repr__(self):
        return f"<Initiative(id={self.id}, title={self.title}, status={self.status.value})>"
