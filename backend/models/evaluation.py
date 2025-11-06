"""
Evaluation model - stores readiness assessment results.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from backend.models.utils import GUID

from backend.database import Base


class Evaluation(Base):
    """
    Readiness evaluation generated for an initiative.
    Stores AI assessment of MRD readiness and knowledge gaps.
    """
    __tablename__ = "evaluations"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Initiative (one-to-one)
    initiative_id = Column(
        GUID,
        ForeignKey("initiatives.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Evaluation results (stored as JSON)
    evaluation_data = Column(JSON, nullable=False)  # Full evaluation response from AI

    # Key metrics (denormalized for easy access)
    readiness_score = Column(Integer, nullable=False)  # 0-100
    risk_level = Column(Integer, nullable=False)  # Low/Medium/High as string in JSON

    # Iteration snapshot
    iteration_at_evaluation = Column(Integer, nullable=False)  # Which iteration this was evaluated at

    # Timestamps
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Evaluated by
    evaluated_by = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    initiative = relationship("Initiative", back_populates="evaluation")
    evaluated_by_user = relationship("User", foreign_keys=[evaluated_by])

    # Indexes
    __table_args__ = (
        Index('ix_evaluations_evaluated_at', 'evaluated_at'),
    )

    def __repr__(self):
        return f"<Evaluation(id={self.id}, initiative_id={self.initiative_id}, readiness_score={self.readiness_score})>"
