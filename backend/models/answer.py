"""
Answer model with status support (Answered/Unknown/Skipped).
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, Text, Enum, ForeignKey, DateTime
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base


class AnswerStatus(str, enum.Enum):
    """Answer status for flexible UX."""
    ANSWERED = "Answered"  # User provided answer
    UNKNOWN = "Unknown"  # User explicitly doesn't know
    SKIPPED = "Skipped"  # User chose to skip
    ESTIMATED = "Estimated"  # User provided estimate (affects scoring confidence)


class Answer(Base):
    """
    Answer to a question with status support.
    Allows users to mark answers as Unknown or Skipped.
    """
    __tablename__ = "answers"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Question (one-to-one)
    question_id = Column(
        GUID,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Answer content
    answer_text = Column(Text, nullable=True)  # Nullable if status=Unknown/Skipped
    answer_status = Column(Enum(AnswerStatus), nullable=False)  # Status field
    skip_reason = Column(Text, nullable=True)  # Optional reason for skipping
    estimation_confidence = Column(Text, nullable=True)  # For ESTIMATED status: "Low", "Medium", "High"

    # Metadata
    answered_by = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    answered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    question = relationship("Question", back_populates="answer")
    answered_by_user = relationship("User", foreign_keys=[answered_by])

    def __repr__(self):
        return f"<Answer(id={self.id}, status={self.answer_status.value}, question_id={self.question_id})>"
