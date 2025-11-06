"""
Organization model for multi-tenancy.
"""

import uuid
from sqlalchemy import Column, String
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin


class Organization(Base, TimestampMixin):
    """
    Organization model for multi-tenancy.
    Each user belongs to one organization.
    """
    __tablename__ = "organizations"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Basic info
    name = Column(String(200), nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    contexts = relationship("Context", back_populates="organization", cascade="all, delete-orphan")
    initiatives = relationship("Initiative", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name})>"
