"""
Context model for organization-level context with versioning.
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, UniqueConstraint, Index
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin


class Context(Base, TimestampMixin):
    """
    Organization-level context with versioning.
    Each organization can have multiple versions, but only one is current.
    """
    __tablename__ = "contexts"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Organization (allows multiple versions)
    organization_id = Column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Context fields
    company_mission = Column(Text, nullable=True)
    strategic_objectives = Column(Text, nullable=True)
    target_markets = Column(Text, nullable=True)
    competitive_landscape = Column(Text, nullable=True)
    technical_constraints = Column(Text, nullable=True)

    # Versioning
    version = Column(Integer, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)

    # Creator
    created_by = Column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization = relationship("Organization", back_populates="contexts")
    created_by_user = relationship("User", foreign_keys=[created_by])

    # Constraints
    __table_args__ = (
        # Unique constraint: one version per organization
        UniqueConstraint('organization_id', 'version', name='uq_org_version'),
        # Index for fast lookup of current version
        Index('ix_org_current', 'organization_id', 'is_current'),
    )

    def __repr__(self):
        return f"<Context(id={self.id}, org={self.organization_id}, version={self.version}, current={self.is_current})>"
