"""
Question throttle service for managing question generation limits.
"""

from typing import List, NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.question import Question
from backend.models.answer import Answer, AnswerStatus
from backend.models.initiative import Initiative
from backend.services.exceptions import QuestionGenerationThrottledError, InitiativeQuestionLimitError


class ThrottleCheckResult(NamedTuple):
    """Result of checking if more questions can be generated."""
    can_generate: bool
    reason: str
    unanswered_count: int
    total_count: int
    max_questions: int


class QuestionLimitCheckResult(NamedTuple):
    """Result of checking question limits (both unanswered and total)."""
    can_add: bool
    reason: str
    unanswered_count: int
    total_count: int
    max_questions: int
    questions_to_add: int


class QuestionThrottleService:
    """Service for managing question generation throttling and limits."""

    UNANSWERED_LIMIT = 5  # Maximum unanswered questions before throttling

    def __init__(self, db: Session):
        self.db = db

    def count_unanswered_questions(self, initiative_id: UUID) -> int:
        """Count questions that need answers."""
        # Questions are considered unanswered if they have no answer or 
        # have an answer with status "Unknown", "Skipped", or "Estimated"
        unanswered_statuses = [AnswerStatus.UNKNOWN, AnswerStatus.SKIPPED, AnswerStatus.ESTIMATED]
        
        # Count questions with no answer
        questions_without_answer = (
            self.db.query(func.count(Question.id))
            .outerjoin(Answer, Question.id == Answer.question_id)
            .filter(
                Question.initiative_id == initiative_id,
                Answer.id.is_(None)
            )
            .scalar()
        )
        
        # Count questions with unanswered status
        questions_with_unanswered_status = (
            self.db.query(func.count(Question.id))
            .join(Answer, Question.id == Answer.question_id)
            .filter(
                Question.initiative_id == initiative_id,
                Answer.answer_status.in_(unanswered_statuses)
            )
            .scalar()
        )
        
        return questions_without_answer + questions_with_unanswered_status

    def count_total_questions(self, initiative_id: UUID) -> int:
        """Count all questions for an initiative."""
        return (
            self.db.query(func.count(Question.id))
            .filter(Question.initiative_id == initiative_id)
            .scalar()
        )

    def can_generate_questions(self, initiative_id: UUID) -> ThrottleCheckResult:
        """Check if more questions can be generated (both unanswered and total limits)."""
        # Get initiative to check max_questions limit
        initiative = self.db.query(Initiative).filter(Initiative.id == initiative_id).first()
        if not initiative:
            return ThrottleCheckResult(
                can_generate=False,
                reason=f"Initiative {initiative_id} not found",
                unanswered_count=0,
                total_count=0,
                max_questions=0
            )
        
        unanswered_count = self.count_unanswered_questions(initiative_id)
        total_count = self.count_total_questions(initiative_id)
        max_questions = initiative.max_questions
        
        # Check unanswered questions limit (5 or more blocks generation)
        if unanswered_count >= self.UNANSWERED_LIMIT:
            return ThrottleCheckResult(
                can_generate=False,
                reason=f"Cannot generate questions: {unanswered_count} unanswered questions (limit: {self.UNANSWERED_LIMIT})",
                unanswered_count=unanswered_count,
                total_count=total_count,
                max_questions=max_questions
            )
        
        # Check total questions limit
        if total_count >= max_questions:
            return ThrottleCheckResult(
                can_generate=False,
                reason=f"Cannot generate questions: initiative at maximum question limit ({total_count}/{max_questions})",
                unanswered_count=unanswered_count,
                total_count=total_count,
                max_questions=max_questions
            )
        
        return ThrottleCheckResult(
            can_generate=True,
            reason="Can generate questions",
            unanswered_count=unanswered_count,
            total_count=total_count,
            max_questions=max_questions
        )

    def get_unanswered_questions(self, initiative_id: UUID) -> List[Question]:
        """Get list of questions needing answers."""
        unanswered_statuses = [AnswerStatus.UNKNOWN, AnswerStatus.SKIPPED, AnswerStatus.ESTIMATED]
        
        # Get questions with no answer
        questions_without_answer = (
            self.db.query(Question)
            .outerjoin(Answer, Question.id == Answer.question_id)
            .filter(
                Question.initiative_id == initiative_id,
                Answer.id.is_(None)
            )
            .all()
        )
        
        # Get questions with unanswered status
        questions_with_unanswered_status = (
            self.db.query(Question)
            .join(Answer, Question.id == Answer.question_id)
            .filter(
                Question.initiative_id == initiative_id,
                Answer.answer_status.in_(unanswered_statuses)
            )
            .all()
        )
        
        return questions_without_answer + questions_with_unanswered_status

    def check_question_limits(self, initiative_id: UUID, questions_to_add: int = 1) -> QuestionLimitCheckResult:
        """Check both unanswered and total question limits."""
        # Get initiative to check max_questions limit
        initiative = self.db.query(Initiative).filter(Initiative.id == initiative_id).first()
        if not initiative:
            return QuestionLimitCheckResult(
                can_add=False,
                reason=f"Initiative {initiative_id} not found",
                unanswered_count=0,
                total_count=0,
                max_questions=0,
                questions_to_add=questions_to_add
            )
        
        unanswered_count = self.count_unanswered_questions(initiative_id)
        total_count = self.count_total_questions(initiative_id)
        max_questions = initiative.max_questions
        
        # Check unanswered questions limit
        if unanswered_count >= self.UNANSWERED_LIMIT:
            return QuestionLimitCheckResult(
                can_add=False,
                reason=f"Cannot add questions: {unanswered_count} unanswered questions (limit: {self.UNANSWERED_LIMIT})",
                unanswered_count=unanswered_count,
                total_count=total_count,
                max_questions=max_questions,
                questions_to_add=questions_to_add
            )
        
        # Check total questions limit
        if (total_count + questions_to_add) > max_questions:
            return QuestionLimitCheckResult(
                can_add=False,
                reason=f"Cannot add {questions_to_add} questions: would exceed maximum limit ({total_count + questions_to_add} > {max_questions})",
                unanswered_count=unanswered_count,
                total_count=total_count,
                max_questions=max_questions,
                questions_to_add=questions_to_add
            )
        
        return QuestionLimitCheckResult(
            can_add=True,
            reason=f"Can add {questions_to_add} questions",
            unanswered_count=unanswered_count,
            total_count=total_count,
            max_questions=max_questions,
            questions_to_add=questions_to_add
        )

    def check_question_limits_or_raise(self, initiative_id: UUID, questions_to_add: int = 1) -> None:
        """Check question limits and raise appropriate exceptions if limits are exceeded."""
        result = self.check_question_limits(initiative_id, questions_to_add)
        
        if not result.can_add:
            # Check which limit was exceeded
            if result.unanswered_count >= self.UNANSWERED_LIMIT:
                raise QuestionGenerationThrottledError(
                    unanswered_count=result.unanswered_count,
                    limit=self.UNANSWERED_LIMIT,
                    initiative_id=str(initiative_id)
                )
            else:
                # Total questions limit exceeded
                raise InitiativeQuestionLimitError(
                    current_count=result.total_count,
                    max_limit=result.max_questions,
                    initiative_id=str(initiative_id)
                )