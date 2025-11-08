"""
Repository for UserRole model operations.
"""

from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from backend.models.user_role import UserRole
from backend.models.role import Role


class UserRoleRepository:
    """Repository for managing user-role assignments."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_roles(self, user_id: UUID) -> List[UserRole]:
        """Get all roles for a user."""
        return self.db.query(UserRole).filter(UserRole.user_id == user_id).all()

    def assign_role(self, user_id: UUID, role_id: UUID) -> UserRole:
        """
        Assign a role to a user.

        Args:
            user_id: The user's ID
            role_id: The role's ID

        Returns:
            The created UserRole association

        Raises:
            IntegrityError: If the role is already assigned to the user
        """
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        return user_role

    def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: The user's ID
            role_id: The role's ID

        Returns:
            True if the role was removed, False if the assignment didn't exist
        """
        user_role = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).first()

        if not user_role:
            return False

        self.db.delete(user_role)
        self.db.commit()
        return True

    def set_user_roles(self, user_id: UUID, role_ids: List[UUID]) -> List[UserRole]:
        """
        Set the roles for a user (replaces existing roles).

        Args:
            user_id: The user's ID
            role_ids: List of role IDs to assign

        Returns:
            List of UserRole associations
        """
        # Remove all existing roles
        self.db.query(UserRole).filter(UserRole.user_id == user_id).delete()

        # Add new roles
        user_roles = []
        for role_id in role_ids:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(user_role)
            user_roles.append(user_role)

        self.db.commit()

        # Refresh all user_roles
        for user_role in user_roles:
            self.db.refresh(user_role)

        return user_roles

    def has_role(self, user_id: UUID, role_name: str) -> bool:
        """
        Check if a user has a specific role by name.

        Args:
            user_id: The user's ID
            role_name: The role name to check

        Returns:
            True if the user has the role, False otherwise
        """
        return self.db.query(UserRole).join(Role).filter(
            UserRole.user_id == user_id,
            Role.name == role_name
        ).count() > 0
