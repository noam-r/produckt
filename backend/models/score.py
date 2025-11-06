"""
Score model for RICE and FDV frameworks.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Float, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.models.utils import GUID

from backend.database import Base


class Score(Base):
    """
    Scoring results for RICE and FDV frameworks.
    Calculated by Scoring Agents after MRD generation.
    """
    __tablename__ = "scores"

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

    # RICE Framework
    reach = Column(Integer, nullable=True)  # Number of users affected
    impact = Column(Float, nullable=True)  # Impact score (0.25, 0.5, 1, 2, 3)
    confidence = Column(Float, nullable=True)  # Confidence % (0-100)
    effort = Column(Float, nullable=True)  # Person-months
    rice_score = Column(Float, nullable=True)  # (Reach × Impact × Confidence) / Effort

    # FDV Framework
    feasibility = Column(Integer, nullable=True)  # 1-10
    desirability = Column(Integer, nullable=True)  # 1-10
    viability = Column(Integer, nullable=True)  # 1-10
    fdv_score = Column(Float, nullable=True)  # Average of F, D, V

    # Metadata
    rice_reasoning = Column(JSON, nullable=True)  # Explanation of RICE values
    fdv_reasoning = Column(JSON, nullable=True)  # Explanation of FDV values

    # Data quality tracking
    data_quality = Column(JSON, nullable=True)  # Quality indicators for scoring data
    warnings = Column(JSON, nullable=True)  # List of warnings about scoring limitations

    # Timestamps
    scored_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Scored by
    scored_by = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    initiative = relationship("Initiative", back_populates="score")
    scored_by_user = relationship("User", foreign_keys=[scored_by])

    def __repr__(self):
        return f"<Score(id={self.id}, initiative_id={self.initiative_id}, RICE={self.rice_score}, FDV={self.fdv_score})>"
