#!/usr/bin/env python3
"""
Migrate roles to match question categories.
Adds new category-based roles: business_dev, operations, financial
Keeps existing roles: admin, technical, product
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.repositories.role_repository import RoleRepository


def migrate_roles():
    """Add new category-based roles to existing database."""
    db = SessionLocal()
    try:
        print("="*60)
        print("Migrating Roles to Match Question Categories")
        print("="*60)

        role_repo = RoleRepository(db)

        # Ensure all default roles exist (including new ones)
        print("\nEnsuring all category-based roles exist...")
        role_repo.ensure_default_roles()

        # List all roles
        roles = role_repo.get_all()
        print(f"\n✓ Total roles in database: {len(roles)}")
        for role in roles:
            print(f"    - {role.name}: {role.description}")

        print("\n" + "="*60)
        print("Role Migration Complete!")
        print("="*60)
        print("\nRoles now align with question categories:")
        print("  - admin         → Full system access")
        print("  - business_dev  → Business_Dev questions")
        print("  - technical     → Technical questions")
        print("  - product       → Product questions")
        print("  - operations    → Operations questions")
        print("  - financial     → Financial questions")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Error migrating roles: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_roles()
