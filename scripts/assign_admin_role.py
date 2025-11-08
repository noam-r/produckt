#!/usr/bin/env python3
"""
Assign admin role to existing users.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.repositories.user_repository import UserRepository
from backend.repositories.role_repository import RoleRepository
from backend.repositories.user_role_repository import UserRoleRepository


def assign_admin_role(email: str):
    """Assign admin role to a user by email."""
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        role_repo = RoleRepository(db)
        user_role_repo = UserRoleRepository(db)

        # Get user
        user = user_repo.get_by_email(email)
        if not user:
            print(f"✗ User with email {email} not found")
            return

        # Get admin role
        admin_role = role_repo.get_by_name("admin")
        if not admin_role:
            print("✗ Admin role not found. Please run scripts/seed_roles.py first")
            return

        # Check if user already has admin role
        if user_role_repo.has_role(user.id, "admin"):
            print(f"✓ User {email} already has admin role")
            return

        # Assign admin role
        user_role_repo.assign_role(user.id, admin_role.id)
        print(f"✓ Admin role assigned to {email}")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/assign_admin_role.py <email>")
        print("\nExample:")
        print("  python scripts/assign_admin_role.py admin@acme.com")
        sys.exit(1)

    email = sys.argv[1]
    assign_admin_role(email)
