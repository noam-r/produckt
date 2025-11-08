"""
Role model for role-based access control.
"""

import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin
from backend.models.utils import GUID


class Role(Base, TimestampMixin):
    """
    Role model for RBAC with many-to-many relationship with users.
    """
    __tablename__ = "roles"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Role details
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"
