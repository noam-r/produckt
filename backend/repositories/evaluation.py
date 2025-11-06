"""
Repository for Evaluation operations.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Evaluation
from backend.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository[Evaluation]):
    """Repository for Evaluation CRUD operations."""

    def __init__(self, db: Session):
        """Initialize Evaluation repository."""
        super().__init__(Evaluation, db)

    def get_by_initiative(self, initiative_id: UUID) -> Optional[Evaluation]:
        """
        Get evaluation for a specific initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            Evaluation if exists, None otherwise
        """
        query = select(Evaluation).where(Evaluation.initiative_id == initiative_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def create_or_update(
        self,
        initiative_id: UUID,
        evaluation_data: dict,
        readiness_score: int,
        risk_level: str,
        iteration_at_evaluation: int,
        evaluated_by: UUID
    ) -> Evaluation:
        """
        Create a new evaluation or update existing one.

        Args:
            initiative_id: Initiative ID
            evaluation_data: Full evaluation JSON data
            readiness_score: Readiness score 0-100
            risk_level: Risk level (Low/Medium/High)
            iteration_at_evaluation: Iteration count when evaluated
            evaluated_by: User ID who triggered evaluation

        Returns:
            Evaluation object (new or updated)
        """
        # Check if evaluation exists
        existing = self.get_by_initiative(initiative_id)

        if existing:
            # Update existing evaluation
            existing.evaluation_data = evaluation_data
            existing.readiness_score = readiness_score
            existing.risk_level = risk_level
            existing.iteration_at_evaluation = iteration_at_evaluation
            existing.evaluated_by = evaluated_by

            self.db.flush()
            self.db.refresh(existing)
            return existing
        else:
            # Create new evaluation
            new_evaluation = Evaluation(
                initiative_id=initiative_id,
                evaluation_data=evaluation_data,
                readiness_score=readiness_score,
                risk_level=risk_level,
                iteration_at_evaluation=iteration_at_evaluation,
                evaluated_by=evaluated_by
            )

            self.db.add(new_evaluation)
            self.db.flush()
            self.db.refresh(new_evaluation)
            return new_evaluation

    def delete_by_initiative(self, initiative_id: UUID) -> bool:
        """
        Delete evaluation for a specific initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            True if deleted, False if not found
        """
        evaluation = self.get_by_initiative(initiative_id)
        if evaluation:
            self.db.delete(evaluation)
            return True
        return False
