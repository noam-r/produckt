"""
UserRole junction table for many-to-many relationship between users and roles.
"""

import uuid
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin
from backend.models.utils import GUID


class UserRole(Base, TimestampMixin):
    """
    Junction table for user-role many-to-many relationship.
    """
    __tablename__ = "user_roles"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role_id = Column(
        GUID,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"
