"""
User model for authentication and authorization.
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Enum, Boolean, ForeignKey, DateTime
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin


class UserRoleEnum(str, enum.Enum):
    """User roles for RBAC (legacy single-role enum, deprecated)."""
    ADMIN = "Admin"
    PRODUCT_MANAGER = "Product_Manager"
    CONTRIBUTOR = "Contributor"
    VIEWER = "Viewer"


class User(Base, TimestampMixin):
    """
    User model with simple password authentication (POC).
    Production will migrate to OAuth2/JWT.
    """
    __tablename__ = "users"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    name = Column(String(100), nullable=False)
    role = Column(Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.PRODUCT_MANAGER)

    # Organization
    organization_id = Column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    initiatives = relationship("Initiative", back_populates="created_by_user", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(ur.role.name == role_name for ur in self.user_roles)

    def has_any_role(self, *role_names: str) -> bool:
        """Check if user has any of the specified roles."""
        user_role_names = {ur.role.name for ur in self.user_roles}
        return bool(user_role_names.intersection(role_names))

    @property
    def role_names(self) -> list[str]:
        """Get list of role names for this user."""
        return [ur.role.name for ur in self.user_roles]
