"""
LLMCall model for tracking all Claude API calls and costs.
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Enum, ForeignKey, DateTime, Index
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base


class LLMCallStatus(str, enum.Enum):
    """Status of LLM API call."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class LLMCall(Base):
    """
    Tracking for all Claude API calls with cost attribution.
    Used for observability and cost management.
    """
    __tablename__ = "llm_calls"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Agent metadata
    agent_name = Column(String(100), nullable=False)  # e.g., "Knowledge Gap Agent"
    model = Column(String(100), nullable=False)  # e.g., "claude-3-5-sonnet-20241022"
    provider = Column(String(50), default="anthropic", nullable=False)

    # Token usage
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # Performance
    latency_ms = Column(Integer, nullable=True)  # Milliseconds

    # Cost
    cost_usd = Column(Float, nullable=False, default=0.0)  # Calculated cost in USD

    # Status
    status = Column(Enum(LLMCallStatus), nullable=False, default=LLMCallStatus.SUCCESS)
    error_message = Column(String(500), nullable=True)

    # Attribution
    user_id = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    organization_id = Column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    initiative_id = Column(
        GUID,
        ForeignKey("initiatives.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Prompt versioning
    prompt_hash = Column(String(64), nullable=True)  # SHA-256 hash for versioning

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    initiative = relationship("Initiative", foreign_keys=[initiative_id])

    # Indexes
    __table_args__ = (
        Index('ix_llmcalls_org_created', 'organization_id', 'created_at'),
        Index('ix_llmcalls_initiative', 'initiative_id', 'created_at'),
        Index('ix_llmcalls_agent', 'agent_name', 'created_at'),
    )

    def __repr__(self):
        return f"<LLMCall(id={self.id}, agent={self.agent_name}, cost=${self.cost_usd:.4f})>"
