#!/usr/bin/env python3
"""
Complete database initialization script.
Seeds roles and creates a default admin user.
Safe to run multiple times - only creates data if it doesn't exist.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.models import Organization, User
from backend.models.user import UserRoleEnum
from backend.repositories.role_repository import RoleRepository
from backend.repositories.user_role_repository import UserRoleRepository
from backend.auth.password import hash_password


def init_database():
    """Initialize database with roles and default admin user."""
    db = SessionLocal()
    try:
        print("="*60)
        print("Initializing ProDuckt Database")
        print("="*60)

        # Step 1: Ensure default roles exist
        print("\n[1/3] Ensuring default roles exist...")
        role_repo = RoleRepository(db)
        role_repo.ensure_default_roles()

        roles = role_repo.get_all()
        print(f"✓ {len(roles)} roles available:")
        for role in roles:
            print(f"    - {role.name}: {role.description}")

        # Step 2: Check if admin user exists
        print("\n[2/3] Checking for admin user...")
        admin_email = "admin@produckt.local"
        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            print(f"✓ Admin user already exists: {admin_email}")
            admin_user = existing_admin
        else:
            # Create default organization for admin
            org_name = "Default Organization"
            org = db.query(Organization).filter(Organization.name == org_name).first()
            if not org:
                org = Organization(name=org_name)
                db.add(org)
                db.flush()
                print(f"✓ Created organization: {org_name}")

            # Create admin user
            admin_user = User(
                email=admin_email,
                password_hash=hash_password("Admin123!"),
                name="System Administrator",
                role=UserRoleEnum.ADMIN,
                organization_id=org.id,
                is_active=True,
                force_password_change=True  # Force password change on first login
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"✓ Created admin user: {admin_email}")

        # Step 3: Ensure admin user has admin role in RBAC
        print("\n[3/3] Assigning RBAC roles...")
        user_role_repo = UserRoleRepository(db)
        admin_role = role_repo.get_by_name("admin")

        if not admin_role:
            print("✗ ERROR: Admin role not found!")
            return

        # Check if admin already has the role
        existing_roles = [ur.role.name for ur in admin_user.user_roles]
        if "admin" in existing_roles:
            print(f"✓ Admin user already has admin role")
        else:
            user_role_repo.set_user_roles(admin_user.id, [admin_role.id])
            print(f"✓ Assigned admin role to {admin_email}")

        db.commit()

        print("\n" + "="*60)
        print("Database Initialization Complete!")
        print("="*60)
        print("\nDefault Admin Login:")
        print("-" * 60)
        print(f"  Email:    {admin_email}")
        print(f"  Password: Admin123! (temporary)")
        print("-" * 60)
        print("\n⚠️  You will be REQUIRED to change your password on first login!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
