"""
Repository for Score operations.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Score
from backend.repositories.base import BaseRepository


class ScoreRepository(BaseRepository[Score]):
    """Repository for Score CRUD operations."""

    def __init__(self, db: Session):
        """Initialize Score repository."""
        super().__init__(Score, db)

    def get_by_initiative(self, initiative_id: UUID) -> Optional[Score]:
        """
        Get score for a specific initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            Score if exists, None otherwise
        """
        query = select(Score).where(Score.initiative_id == initiative_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def create_or_update(
        self,
        initiative_id: UUID,
        reach: int,
        impact: float,
        confidence: int,
        effort: float,
        rice_score: float,
        rice_reasoning: dict,
        feasibility: int,
        desirability: int,
        viability: int,
        fdv_score: float,
        fdv_reasoning: dict,
        scored_by: UUID,
        data_quality: Optional[dict] = None,
        warnings: Optional[list] = None
    ) -> Score:
        """
        Create a new score or update existing one.

        Args:
            initiative_id: Initiative ID
            reach: RICE reach value
            impact: RICE impact value
            confidence: RICE confidence percentage
            effort: RICE effort in person-months
            rice_score: Calculated RICE score
            rice_reasoning: RICE reasoning dict
            feasibility: FDV feasibility score (1-10)
            desirability: FDV desirability score (1-10)
            viability: FDV viability score (1-10)
            fdv_score: Calculated FDV score
            fdv_reasoning: FDV reasoning dict
            scored_by: User ID who calculated the score
            data_quality: Optional dict of data quality indicators
            warnings: Optional list of warning strings

        Returns:
            Score object (new or updated)
        """
        # Check if score exists
        existing = self.get_by_initiative(initiative_id)

        if existing:
            # Update existing score
            existing.reach = reach
            existing.impact = impact
            existing.confidence = confidence
            existing.effort = effort
            existing.rice_score = rice_score
            existing.rice_reasoning = rice_reasoning
            existing.feasibility = feasibility
            existing.desirability = desirability
            existing.viability = viability
            existing.fdv_score = fdv_score
            existing.fdv_reasoning = fdv_reasoning
            existing.scored_by = scored_by
            existing.data_quality = data_quality
            existing.warnings = warnings

            self.db.flush()
            self.db.refresh(existing)
            return existing
        else:
            # Create new score
            score = Score(
                initiative_id=initiative_id,
                reach=reach,
                impact=impact,
                confidence=confidence,
                effort=effort,
                rice_score=rice_score,
                rice_reasoning=rice_reasoning,
                feasibility=feasibility,
                desirability=desirability,
                viability=viability,
                fdv_score=fdv_score,
                fdv_reasoning=fdv_reasoning,
                scored_by=scored_by,
                data_quality=data_quality,
                warnings=warnings
            )
            return self.create(score)

    def delete_by_initiative(self, initiative_id: UUID) -> bool:
        """
        Delete score for an initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            True if deleted, False if not found
        """
        score = self.get_by_initiative(initiative_id)
        if score:
            self.delete(score.id)
            return True
        return False
