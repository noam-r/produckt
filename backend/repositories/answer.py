"""
Answer repository for data access.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.models import Answer, AnswerStatus
from backend.repositories.base import BaseRepository


class AnswerRepository(BaseRepository[Answer]):
    """Repository for Answer entities."""

    def __init__(self, db: Session):
        super().__init__(Answer, db)

    def get_by_question(self, question_id: UUID) -> Optional[Answer]:
        """
        Get answer for a specific question.

        Typically there's one answer per question (latest version).

        Args:
            question_id: Question ID

        Returns:
            Answer if found, None otherwise
        """
        query = select(Answer).where(
            Answer.question_id == question_id
        )

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_by_initiative(self, initiative_id: UUID) -> List[Answer]:
        """
        Get all answers for an initiative's questions.

        Args:
            initiative_id: Initiative ID

        Returns:
            List of all answers for the initiative
        """
        from backend.models import Question

        query = select(Answer).join(
            Question, Answer.question_id == Question.id
        ).where(
            Question.initiative_id == initiative_id
        ).order_by(Answer.answered_at.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_by_status(
        self,
        initiative_id: UUID,
        status: AnswerStatus
    ) -> List[Answer]:
        """
        Get answers by status for an initiative.

        Args:
            initiative_id: Initiative ID
            status: Answer status

        Returns:
            List of answers with the specified status
        """
        from backend.models import Question

        query = select(Answer).join(
            Question, Answer.question_id == Question.id
        ).where(
            Question.initiative_id == initiative_id,
            Answer.answer_status == status
        ).order_by(Answer.answered_at.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def count_by_status(self, initiative_id: UUID) -> dict:
        """
        Count answers by status for an initiative.

        Args:
            initiative_id: Initiative ID

        Returns:
            Dictionary with counts for each status
        """
        from sqlalchemy import func
        from backend.models import Question

        query = select(
            Answer.answer_status,
            func.count(Answer.id)
        ).join(
            Question, Answer.question_id == Question.id
        ).where(
            Question.initiative_id == initiative_id
        ).group_by(Answer.answer_status)

        result = self.db.execute(query)
        counts = {status.value: 0 for status in AnswerStatus}

        for status, count in result.all():
            counts[status.value] = count

        return counts

    def get_with_question(self, id: UUID) -> Optional[Answer]:
        """
        Get answer with related question loaded.

        Args:
            id: Answer ID

        Returns:
            Answer with question loaded, or None if not found
        """
        query = select(Answer).where(
            Answer.id == id
        ).options(joinedload(Answer.question))

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def upsert_answer(
        self,
        question_id: UUID,
        answer_text: Optional[str],
        answer_status: AnswerStatus,
        answered_by: UUID
    ) -> Answer:
        """
        Create or update an answer for a question.

        If an answer already exists, updates it. Otherwise creates new.

        Args:
            question_id: Question ID
            answer_text: Answer text (can be None for Unknown/Skipped)
            answer_status: Answer status
            answered_by: User ID who answered

        Returns:
            Created or updated answer
        """
        existing = self.get_by_question(question_id)

        if existing:
            # Update existing answer
            existing.answer_text = answer_text
            existing.answer_status = answer_status
            existing.answered_by = answered_by
            self.db.flush()
            self.db.refresh(existing)
            return existing
        else:
            # Create new answer
            answer = Answer(
                question_id=question_id,
                answer_text=answer_text,
                answer_status=answer_status,
                answered_by=answered_by
            )
            return self.create(answer)

    def get_answered_count(self, initiative_id: UUID) -> int:
        """
        Get count of answered questions (status = ANSWERED).

        Args:
            initiative_id: Initiative ID

        Returns:
            Number of answered questions
        """
        from sqlalchemy import func
        from backend.models import Question

        query = select(func.count(Answer.id)).join(
            Question, Answer.question_id == Question.id
        ).where(
            Question.initiative_id == initiative_id,
            Answer.answer_status == AnswerStatus.ANSWERED
        )

        result = self.db.execute(query)
        return result.scalar_one()

    def get_unanswered_questions(self, initiative_id: UUID) -> List[UUID]:
        """
        Get IDs of questions that don't have answers yet.

        Args:
            initiative_id: Initiative ID

        Returns:
            List of question IDs without answers
        """
        from backend.models import Question

        # Subquery for answered question IDs
        answered_subquery = select(Answer.question_id).distinct().scalar_subquery()

        # Query for unanswered questions
        query = select(Question.id).where(
            Question.initiative_id == initiative_id,
            ~Question.id.in_(answered_subquery)
        )

        result = self.db.execute(query)
        return list(result.scalars().all())
