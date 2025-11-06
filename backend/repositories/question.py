"""
Question repository for data access.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.models import Question, QuestionPriority, QuestionCategory
from backend.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    """Repository for Question entities."""

    def __init__(self, db: Session):
        super().__init__(Question, db)

    def get_by_initiative(
        self,
        initiative_id: UUID,
        iteration: Optional[int] = None
    ) -> List[Question]:
        """
        Get all questions for an initiative.

        Args:
            initiative_id: Initiative ID
            iteration: Optional iteration number to filter by

        Returns:
            List of questions for the initiative
        """
        query = select(Question).where(Question.initiative_id == initiative_id)

        if iteration is not None:
            query = query.where(Question.iteration == iteration)

        query = query.order_by(
            Question.priority.asc(),  # P0 first
            Question.category.asc(),
            Question.created_at.asc()
        )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_with_answer(
        self,
        id: UUID
    ) -> Optional[Question]:
        """
        Get question with answer loaded.

        Args:
            id: Question ID

        Returns:
            Question with answer loaded, or None if not found
        """
        query = select(Question).where(
            Question.id == id
        ).options(joinedload(Question.answers))

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_by_priority(
        self,
        initiative_id: UUID,
        priority: QuestionPriority,
        iteration: Optional[int] = None
    ) -> List[Question]:
        """
        Get questions by priority level.

        Args:
            initiative_id: Initiative ID
            priority: Question priority (P0/P1/P2)
            iteration: Optional iteration number

        Returns:
            List of questions with specified priority
        """
        query = select(Question).where(
            Question.initiative_id == initiative_id,
            Question.priority == priority
        )

        if iteration is not None:
            query = query.where(Question.iteration == iteration)

        query = query.order_by(
            Question.category.asc(),
            Question.created_at.asc()
        )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_blocking_questions(
        self,
        initiative_id: UUID
    ) -> List[Question]:
        """
        Get questions that block MRD generation (P0).

        Args:
            initiative_id: Initiative ID

        Returns:
            List of P0 questions that must be answered
        """
        query = select(Question).where(
            Question.initiative_id == initiative_id,
            Question.blocks_mrd_generation == True
        ).order_by(
            Question.category.asc(),
            Question.created_at.asc()
        )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_by_category(
        self,
        initiative_id: UUID,
        category: QuestionCategory,
        iteration: Optional[int] = None
    ) -> List[Question]:
        """
        Get questions by category.

        Args:
            initiative_id: Initiative ID
            category: Question category
            iteration: Optional iteration number

        Returns:
            List of questions in the category
        """
        query = select(Question).where(
            Question.initiative_id == initiative_id,
            Question.category == category
        )

        if iteration is not None:
            query = query.where(Question.iteration == iteration)

        query = query.order_by(
            Question.priority.asc(),
            Question.created_at.asc()
        )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_unanswered(
        self,
        initiative_id: UUID,
        iteration: Optional[int] = None
    ) -> List[Question]:
        """
        Get unanswered questions for an initiative.

        Args:
            initiative_id: Initiative ID
            iteration: Optional iteration number

        Returns:
            List of questions without answers
        """
        from backend.models import Answer

        # Get all questions
        questions_query = select(Question).where(
            Question.initiative_id == initiative_id
        )

        if iteration is not None:
            questions_query = questions_query.where(Question.iteration == iteration)

        # Get IDs of answered questions
        answered_query = select(Answer.question_id).distinct()

        # Filter to unanswered
        query = questions_query.where(
            ~Question.id.in_(answered_query)
        ).order_by(
            Question.priority.asc(),
            Question.category.asc()
        )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def count_by_priority(
        self,
        initiative_id: UUID,
        iteration: Optional[int] = None
    ) -> dict:
        """
        Count questions by priority level.

        Args:
            initiative_id: Initiative ID
            iteration: Optional iteration number

        Returns:
            Dictionary with counts for P0, P1, P2
        """
        from sqlalchemy import func

        query = select(
            Question.priority,
            func.count(Question.id)
        ).where(
            Question.initiative_id == initiative_id
        )

        if iteration is not None:
            query = query.where(Question.iteration == iteration)

        query = query.group_by(Question.priority)

        result = self.db.execute(query)
        counts = {priority.value: 0 for priority in QuestionPriority}

        for priority, count in result.all():
            counts[priority.value] = count

        return counts

    def get_latest_iteration(self, initiative_id: UUID) -> int:
        """
        Get the latest iteration number for an initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            Latest iteration number (0 if no questions exist)
        """
        from sqlalchemy import func

        query = select(func.max(Question.iteration)).where(
            Question.initiative_id == initiative_id
        )

        result = self.db.execute(query)
        max_iteration = result.scalar_one_or_none()
        return max_iteration if max_iteration is not None else 0
