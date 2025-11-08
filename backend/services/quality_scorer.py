"""
Quality Score Calculator - Dynamically calculates initiative quality based on Q&A coverage.

This provides a consistent, up-to-date quality score that measures how well
the initiative has been researched and documented, independent of workflow progress.
"""

from typing import Tuple
from sqlalchemy.orm import Session
from uuid import UUID

from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository


def calculate_quality_score(db: Session, initiative_id: UUID) -> Tuple[int, dict]:
    """
    Calculate quality score for an initiative based on question coverage.

    Quality score measures how thoroughly the initiative has been researched
    through the Q&A process. It's weighted by priority:
    - P0 (Must Have): 50% weight
    - P1 (Should Have): 30% weight
    - P2 (Nice to Have): 20% weight

    Args:
        db: Database session
        initiative_id: Initiative to score

    Returns:
        Tuple of (quality_score, breakdown_dict) where:
        - quality_score: 0-100 integer representing quality
        - breakdown_dict: Details of calculation for transparency

    Example breakdown:
        {
            "p0_answered": 5,
            "p0_total": 5,
            "p0_score": 50,
            "p1_answered": 8,
            "p1_total": 10,
            "p1_score": 24,  # (8/10) * 30
            "p2_answered": 3,
            "p2_total": 8,
            "p2_score": 7,   # (3/8) * 20
            "total_score": 81,
            "has_unanswered_p0": False,
            "has_unanswered_p1": True
        }
    """
    question_repo = QuestionRepository(db)
    answer_repo = AnswerRepository(db)

    # Get all questions for initiative
    questions = question_repo.get_by_initiative(initiative_id)

    if not questions:
        # No questions = no quality assessment possible
        return 0, {
            "p0_answered": 0,
            "p0_total": 0,
            "p0_score": 0,
            "p1_answered": 0,
            "p1_total": 0,
            "p1_score": 0,
            "p2_answered": 0,
            "p2_total": 0,
            "p2_score": 0,
            "total_score": 0,
            "has_unanswered_p0": False,
            "has_unanswered_p1": False,
            "note": "No questions generated yet"
        }

    # Count questions by priority
    p0_questions = [q for q in questions if q.priority == "P0"]
    p1_questions = [q for q in questions if q.priority == "P1"]
    p2_questions = [q for q in questions if q.priority == "P2"]

    # Count answered questions (Answered or Unknown status = answered)
    def is_answered(question):
        answer = answer_repo.get_by_question(question.id)
        if not answer:
            return False
        return answer.answer_status in ["Answered", "Unknown"]

    p0_answered = sum(1 for q in p0_questions if is_answered(q))
    p1_answered = sum(1 for q in p1_questions if is_answered(q))
    p2_answered = sum(1 for q in p2_questions if is_answered(q))

    # Calculate weighted scores
    p0_score = (p0_answered / len(p0_questions) * 50) if p0_questions else 0
    p1_score = (p1_answered / len(p1_questions) * 30) if p1_questions else 0
    p2_score = (p2_answered / len(p2_questions) * 20) if p2_questions else 0

    # If no questions of a priority exist, redistribute that weight proportionally
    # This ensures initiatives without P2 questions can still reach 100%
    total_weight = 0
    if p0_questions:
        total_weight += 50
    if p1_questions:
        total_weight += 30
    if p2_questions:
        total_weight += 20

    if total_weight < 100:
        # Adjust to 100-point scale
        adjustment_factor = 100 / total_weight if total_weight > 0 else 0
        p0_score *= adjustment_factor
        p1_score *= adjustment_factor
        p2_score *= adjustment_factor

    total_score = round(p0_score + p1_score + p2_score)

    return total_score, {
        "p0_answered": p0_answered,
        "p0_total": len(p0_questions),
        "p0_score": round(p0_score),
        "p1_answered": p1_answered,
        "p1_total": len(p1_questions),
        "p1_score": round(p1_score),
        "p2_answered": p2_answered,
        "p2_total": len(p2_questions),
        "p2_score": round(p2_score),
        "total_score": total_score,
        "has_unanswered_p0": p0_answered < len(p0_questions) if p0_questions else False,
        "has_unanswered_p1": p1_answered < len(p1_questions) if p1_questions else False,
        "total_questions": len(questions),
        "total_answered": p0_answered + p1_answered + p2_answered
    }
