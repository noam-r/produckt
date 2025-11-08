#!/usr/bin/env python3
"""
Seed default roles in the database.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.repositories.role_repository import RoleRepository


def seed_roles():
    """Seed default roles."""
    db = SessionLocal()
    try:
        role_repo = RoleRepository(db)
        role_repo.ensure_default_roles()
        print("✓ Default roles created successfully")

        # List all roles
        roles = role_repo.get_all()
        print(f"\nAvailable roles ({len(roles)}):")
        for role in roles:
            print(f"  - {role.name}: {role.description}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
