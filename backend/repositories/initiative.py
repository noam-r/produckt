"""
Initiative repository for data access.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.models import Initiative, InitiativeStatus
from backend.repositories.base import BaseRepository


class InitiativeRepository(BaseRepository[Initiative]):
    """Repository for Initiative entities."""

    def __init__(self, db: Session):
        super().__init__(Initiative, db)

    def get_by_status(
        self,
        status: InitiativeStatus,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Initiative]:
        """
        Get initiatives by status.

        Args:
            status: Initiative status to filter by
            organization_id: Organization ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of initiatives with the specified status
        """
        query = select(Initiative).where(
            Initiative.organization_id == organization_id,
            Initiative.status == status
        ).order_by(Initiative.created_at.desc()).limit(limit).offset(offset)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_with_questions(
        self,
        id: UUID,
        organization_id: UUID
    ) -> Optional[Initiative]:
        """
        Get initiative with all related questions loaded.

        Args:
            id: Initiative ID
            organization_id: Organization ID

        Returns:
            Initiative with questions loaded, or None if not found
        """
        query = select(Initiative).where(
            Initiative.id == id,
            Initiative.organization_id == organization_id
        ).options(joinedload(Initiative.questions))

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_ready_for_mrd(self, organization_id: UUID) -> List[Initiative]:
        """
        Get initiatives that are ready for MRD generation.

        Returns initiatives with status IN_QA or READY.

        Args:
            organization_id: Organization ID

        Returns:
            List of initiatives ready for MRD generation
        """
        query = select(Initiative).where(
            Initiative.organization_id == organization_id,
            Initiative.status.in_([InitiativeStatus.IN_QA, InitiativeStatus.READY])
        ).order_by(Initiative.readiness_score.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def update_status(
        self,
        id: UUID,
        status: InitiativeStatus,
        organization_id: UUID
    ) -> Optional[Initiative]:
        """
        Update initiative status.

        Args:
            id: Initiative ID
            status: New status
            organization_id: Organization ID

        Returns:
            Updated initiative or None if not found
        """
        initiative = self.get_by_id(id, organization_id)
        if initiative:
            initiative.status = status
            self.db.flush()
            self.db.refresh(initiative)
        return initiative

    def update_readiness_score(
        self,
        id: UUID,
        score: float,
        organization_id: UUID
    ) -> Optional[Initiative]:
        """
        Update initiative readiness score.

        Args:
            id: Initiative ID
            score: New readiness score (0-100)
            organization_id: Organization ID

        Returns:
            Updated initiative or None if not found
        """
        initiative = self.get_by_id(id, organization_id)
        if initiative:
            initiative.readiness_score = score
            self.db.flush()
            self.db.refresh(initiative)
        return initiative

    def increment_iteration(
        self,
        id: UUID,
        organization_id: UUID
    ) -> Optional[Initiative]:
        """
        Increment the iteration count for an initiative.

        Args:
            id: Initiative ID
            organization_id: Organization ID

        Returns:
            Updated initiative or None if not found
        """
        initiative = self.get_by_id(id, organization_id)
        if initiative:
            initiative.iteration_count += 1
            self.db.flush()
            self.db.refresh(initiative)
        return initiative

    def search_by_title(
        self,
        search_term: str,
        organization_id: UUID,
        limit: int = 20
    ) -> List[Initiative]:
        """
        Search initiatives by title or description.

        Args:
            search_term: Term to search for
            organization_id: Organization ID
            limit: Maximum number of results

        Returns:
            List of matching initiatives
        """
        search_pattern = f"%{search_term}%"
        query = select(Initiative).where(
            Initiative.organization_id == organization_id,
            (Initiative.title.ilike(search_pattern) |
             Initiative.description.ilike(search_pattern))
        ).order_by(Initiative.created_at.desc()).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())
