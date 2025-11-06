"""
Context repository for data access with versioning support.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Context
from backend.repositories.base import BaseRepository


class ContextRepository(BaseRepository[Context]):
    """Repository for Context entities with version management."""

    def __init__(self, db: Session):
        super().__init__(Context, db)

    def get_current(self, organization_id: UUID) -> Optional[Context]:
        """
        Get the current (active) context for an organization.

        Args:
            organization_id: Organization ID

        Returns:
            Current context or None if no current context exists
        """
        query = select(Context).where(
            Context.organization_id == organization_id,
            Context.is_current == True
        )

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_by_version(
        self,
        organization_id: UUID,
        version: int
    ) -> Optional[Context]:
        """
        Get a specific version of context.

        Args:
            organization_id: Organization ID
            version: Version number

        Returns:
            Context with specified version or None if not found
        """
        query = select(Context).where(
            Context.organization_id == organization_id,
            Context.version == version
        )

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_all_versions(
        self,
        organization_id: UUID
    ) -> List[Context]:
        """
        Get all context versions for an organization.

        Args:
            organization_id: Organization ID

        Returns:
            List of all context versions, ordered by version descending
        """
        query = select(Context).where(
            Context.organization_id == organization_id
        ).order_by(Context.version.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_latest_version(self, organization_id: UUID) -> int:
        """
        Get the latest version number for an organization.

        Args:
            organization_id: Organization ID

        Returns:
            Latest version number (0 if no contexts exist)
        """
        from sqlalchemy import func

        query = select(func.max(Context.version)).where(
            Context.organization_id == organization_id
        )

        result = self.db.execute(query)
        max_version = result.scalar_one_or_none()
        return max_version if max_version is not None else 0

    def create_new_version(
        self,
        organization_id: UUID,
        company_mission: Optional[str] = None,
        strategic_objectives: Optional[str] = None,
        target_markets: Optional[str] = None,
        competitive_landscape: Optional[str] = None,
        technical_constraints: Optional[str] = None,
        created_by: UUID = None
    ) -> Context:
        """
        Create a new version of context, marking it as current.

        Automatically:
        1. Gets the next version number
        2. Marks all existing contexts as not current
        3. Creates new context as current

        Args:
            organization_id: Organization ID
            company_mission: Company mission statement
            strategic_objectives: Strategic objectives
            target_markets: Target markets description
            competitive_landscape: Competitive analysis
            technical_constraints: Technical constraints
            created_by: User ID who created this version

        Returns:
            Newly created context
        """
        # Get next version number
        next_version = self.get_latest_version(organization_id) + 1

        # Mark all existing contexts as not current
        existing_contexts = self.get_all_versions(organization_id)
        for ctx in existing_contexts:
            ctx.is_current = False

        # Create new context
        new_context = Context(
            organization_id=organization_id,
            company_mission=company_mission,
            strategic_objectives=strategic_objectives,
            target_markets=target_markets,
            competitive_landscape=competitive_landscape,
            technical_constraints=technical_constraints,
            version=next_version,
            is_current=True,
            created_by=created_by
        )

        return self.create(new_context)

    def set_current(
        self,
        id: UUID,
        organization_id: UUID
    ) -> Optional[Context]:
        """
        Set a specific context version as current.

        Args:
            id: Context ID to make current
            organization_id: Organization ID

        Returns:
            Updated context or None if not found
        """
        # Get the context to make current
        context = self.get_by_id(id, organization_id)
        if not context:
            return None

        # Mark all other contexts as not current
        all_contexts = self.get_all_versions(organization_id)
        for ctx in all_contexts:
            ctx.is_current = (ctx.id == id)

        self.db.flush()
        self.db.refresh(context)
        return context

    def delete_version(
        self,
        id: UUID,
        organization_id: UUID
    ) -> bool:
        """
        Delete a context version.

        Cannot delete the current version - must set another version as
        current first.

        Args:
            id: Context ID to delete
            organization_id: Organization ID

        Returns:
            True if deleted, False if not found or is current version
        """
        context = self.get_by_id(id, organization_id)

        if not context:
            return False

        if context.is_current:
            # Don't allow deleting current version
            return False

        self.db.delete(context)
        self.db.flush()
        return True

    def get_history(
        self,
        organization_id: UUID,
        limit: int = 10
    ) -> List[Context]:
        """
        Get recent context version history.

        Args:
            organization_id: Organization ID
            limit: Maximum number of versions to return

        Returns:
            List of recent context versions
        """
        query = select(Context).where(
            Context.organization_id == organization_id
        ).order_by(
            Context.version.desc()
        ).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())
