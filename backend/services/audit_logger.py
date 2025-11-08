"""
Audit logging service for tracking critical changes.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog


class AuditLogger:
    """Service for creating audit log entries."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: UUID,
        changes: Dict[str, Any],
        actor_id: Optional[UUID],
        organization_id: UUID
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The action performed (e.g., "create", "update", "delete")
            entity_type: The type of entity (e.g., "user", "role", "context")
            entity_id: The ID of the affected entity
            changes: Dictionary of changes made
            actor_id: ID of the user who performed the action
            organization_id: Organization context

        Returns:
            The created audit log entry
        """
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            actor_id=actor_id,
            organization_id=organization_id,
            timestamp=datetime.utcnow()
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def log_user_creation(
        self,
        user_id: UUID,
        email: str,
        name: str,
        roles: list[str],
        actor_id: Optional[UUID],
        organization_id: UUID
    ) -> AuditLog:
        """Log user creation."""
        return self.log(
            action="create_user",
            entity_type="user",
            entity_id=user_id,
            changes={
                "email": email,
                "name": name,
                "roles": roles
            },
            actor_id=actor_id,
            organization_id=organization_id
        )

    def log_user_update(
        self,
        user_id: UUID,
        changes: Dict[str, Any],
        actor_id: Optional[UUID],
        organization_id: UUID
    ) -> AuditLog:
        """Log user update."""
        return self.log(
            action="update_user",
            entity_type="user",
            entity_id=user_id,
            changes=changes,
            actor_id=actor_id,
            organization_id=organization_id
        )

    def log_user_deletion(
        self,
        user_id: UUID,
        email: str,
        actor_id: Optional[UUID],
        organization_id: UUID
    ) -> AuditLog:
        """Log user deletion."""
        return self.log(
            action="delete_user",
            entity_type="user",
            entity_id=user_id,
            changes={"email": email},
            actor_id=actor_id,
            organization_id=organization_id
        )

    def log_password_change(
        self,
        user_id: UUID,
        changed_by_admin: bool,
        actor_id: Optional[UUID],
        organization_id: UUID
    ) -> AuditLog:
        """Log password change."""
        return self.log(
            action="change_password",
            entity_type="user",
            entity_id=user_id,
            changes={"changed_by_admin": changed_by_admin},
            actor_id=actor_id,
            organization_id=organization_id
        )

    def log_role_assignment(
        self,
        user_id: UUID,
        added_roles: list[str],
        removed_roles: list[str],
        actor_id: Optional[UUID],
        organization_id: UUID
    ) -> AuditLog:
        """Log role assignment changes."""
        return self.log(
            action="update_roles",
            entity_type="user",
            entity_id=user_id,
            changes={
                "added_roles": added_roles,
                "removed_roles": removed_roles
            },
            actor_id=actor_id,
            organization_id=organization_id
        )
