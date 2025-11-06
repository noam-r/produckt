"""
AuditLog model for tracking all critical changes.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from backend.models.utils import GUID

from backend.database import Base


class AuditLog(Base):
    """
    Audit log for tracking all critical changes.
    Records before/after values for compliance and debugging.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Actor
    actor_id = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Action
    action = Column(String(100), nullable=False)  # e.g., "created_initiative", "answered_question"

    # Entity
    entity_type = Column(String(50), nullable=False)  # e.g., "Initiative", "Context", "Answer"
    entity_id = Column(GUID, nullable=False, index=True)

    # Changes (JSON for flexible schema)
    changes = Column(JSON, nullable=False)  # {"field": {"old": "value1", "new": "value2"}}

    # Organization (for multi-tenancy filtering)
    organization_id = Column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    actor = relationship("User", foreign_keys=[actor_id])
    organization = relationship("Organization", foreign_keys=[organization_id])

    # Indexes
    __table_args__ = (
        Index('ix_audit_org_timestamp', 'organization_id', 'timestamp'),
        Index('ix_audit_entity', 'entity_type', 'entity_id'),
        Index('ix_audit_actor', 'actor_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type})>"
