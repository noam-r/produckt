"""
Repository for MRD (Market Requirements Document) operations.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import MRD
from backend.repositories.base import BaseRepository


class MRDRepository(BaseRepository[MRD]):
    """Repository for MRD CRUD operations."""

    def __init__(self, db: Session):
        """Initialize MRD repository."""
        super().__init__(MRD, db)

    def get_by_initiative(self, initiative_id: UUID) -> Optional[MRD]:
        """
        Get MRD for a specific initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            MRD if exists, None otherwise
        """
        query = select(MRD).where(MRD.initiative_id == initiative_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def create_or_update(
        self,
        initiative_id: UUID,
        content: str,
        quality_disclaimer: str,
        word_count: int,
        completeness_score: int,
        readiness_at_generation: int,
        assumptions_made: list,
        generated_by: UUID
    ) -> MRD:
        """
        Create a new MRD or update existing one (increments version).

        Args:
            initiative_id: Initiative ID
            content: MRD markdown content
            quality_disclaimer: Quality disclaimer text
            word_count: Word count
            completeness_score: Completeness score 0-100
            readiness_at_generation: Readiness score at time of generation
            assumptions_made: List of assumptions
            generated_by: User ID who generated the MRD

        Returns:
            MRD object (new or updated)
        """
        # Check if MRD exists
        existing = self.get_by_initiative(initiative_id)

        if existing:
            # Update existing MRD
            existing.content = content
            existing.quality_disclaimer = quality_disclaimer
            existing.version += 1
            existing.word_count = word_count
            existing.completeness_score = completeness_score
            existing.readiness_at_generation = readiness_at_generation
            existing.assumptions_made = assumptions_made
            existing.generated_by = generated_by

            self.db.flush()
            self.db.refresh(existing)
            return existing
        else:
            # Create new MRD
            mrd = MRD(
                initiative_id=initiative_id,
                content=content,
                quality_disclaimer=quality_disclaimer,
                version=1,
                word_count=word_count,
                completeness_score=completeness_score,
                readiness_at_generation=readiness_at_generation,
                assumptions_made=assumptions_made,
                generated_by=generated_by
            )
            return self.create(mrd)

    def delete_by_initiative(self, initiative_id: UUID) -> bool:
        """
        Delete MRD for an initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            True if deleted, False if not found
        """
        mrd = self.get_by_initiative(initiative_id)
        if mrd:
            self.delete(mrd.id)
            return True
        return False
