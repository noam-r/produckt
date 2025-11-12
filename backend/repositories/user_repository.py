"""
Repository for User model operations.
"""

import secrets
import string
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from backend.models.user import User
from backend.models.user_role import UserRole as UserRoleAssociation
from backend.auth.password import hash_password


class UserRepository:
    """Repository for managing users."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, organization_id: UUID) -> List[User]:
        """Get all users in an organization."""
        return self.db.query(User).filter(
            User.organization_id == organization_id
        ).options(
            joinedload(User.user_roles).joinedload(UserRoleAssociation.role)
        ).order_by(User.name).all()

    def get_by_id(self, user_id: UUID, organization_id: UUID) -> Optional[User]:
        """Get user by ID within organization."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.organization_id == organization_id
        ).options(
            joinedload(User.user_roles).joinedload(UserRoleAssociation.role)
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).options(
            joinedload(User.user_roles).joinedload(UserRoleAssociation.role)
        ).first()

    def create(
        self,
        email: str,
        password: str,
        name: str,
        organization_id: UUID,
        is_active: bool = True
    ) -> User:
        """
        Create a new user.

        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            name: User's full name
            organization_id: Organization ID
            is_active: Whether the user is active

        Returns:
            The created user
        """
        password_hash = hash_password(password)

        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            organization_id=organization_id,
            is_active=is_active
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def update(
        self,
        user_id: UUID,
        organization_id: UUID,
        email: Optional[str] = None,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        force_password_change: Optional[bool] = None
    ) -> Optional[User]:
        """
        Update user details.

        Args:
            user_id: User's ID
            organization_id: Organization ID for security check
            email: New email (optional)
            name: New name (optional)
            is_active: New active status (optional)
            force_password_change: Force password change flag (optional)

        Returns:
            The updated user or None if not found
        """
        user = self.get_by_id(user_id, organization_id)
        if not user:
            return None

        if email is not None:
            user.email = email
        if name is not None:
            user.name = name
        if is_active is not None:
            user.is_active = is_active
        if force_password_change is not None:
            user.force_password_change = force_password_change

        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(
        self,
        user_id: UUID,
        organization_id: UUID,
        new_password: str
    ) -> Optional[User]:
        """
        Change user's password.

        Args:
            user_id: User's ID
            organization_id: Organization ID for security check
            new_password: New plain text password (will be hashed)

        Returns:
            The updated user or None if not found
        """
        user = self.get_by_id(user_id, organization_id)
        if not user:
            return None

        user.password_hash = hash_password(new_password)

        self.db.commit()
        self.db.refresh(user)

        return user

    def delete(self, user_id: UUID, organization_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id: User's ID
            organization_id: Organization ID for security check

        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id, organization_id)
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()

        return True

    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """
        Generate a cryptographically secure random password.

        Args:
            length: Length of the password (default: 16)

        Returns:
            A random password containing letters, digits, and special characters
        """
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*"

        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # Fill the rest with random characters from all sets
        all_chars = lowercase + uppercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)
