"""
Repository for Role model operations.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from backend.models.role import Role


class RoleRepository:
    """Repository for managing roles."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Role]:
        """Get all roles."""
        return self.db.query(Role).order_by(Role.name).all()

    def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self.db.query(Role).filter(Role.name == name).first()

    def create(self, name: str, description: Optional[str] = None) -> Role:
        """Create a new role."""
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def update(self, role_id: UUID, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Role]:
        """Update an existing role."""
        role = self.get_by_id(role_id)
        if not role:
            return None

        if name is not None:
            role.name = name
        if description is not None:
            role.description = description

        self.db.commit()
        self.db.refresh(role)
        return role

    def delete(self, role_id: UUID) -> bool:
        """Delete a role."""
        role = self.get_by_id(role_id)
        if not role:
            return False

        self.db.delete(role)
        self.db.commit()
        return True

    def ensure_default_roles(self) -> None:
        """Ensure default roles exist in the database."""
        default_roles = [
            ("admin", "Full system access, can manage users and contexts"),
            ("business_dev", "Business Development - can answer Business_Dev category questions"),
            ("technical", "Technical - can answer Technical category questions"),
            ("product", "Product - can answer Product category questions"),
            ("operations", "Operations - can answer Operations category questions"),
            ("financial", "Financial - can answer Financial category questions"),
        ]

        for name, description in default_roles:
            if not self.get_by_name(name):
                self.create(name=name, description=description)
