"""
Question and Answer API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from backend.database import get_db
from backend.models import User, QuestionPriority
from backend.repositories.initiative import InitiativeRepository
from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository
from backend.schemas.question import (
    AnswerCreate, AnswerResponse, QuestionResponse,
    QuestionWithAnswerResponse, QuestionListResponse
)
from backend.auth.dependencies import get_current_user


router = APIRouter(prefix="/initiatives/{initiative_id}/questions", tags=["Questions"])


@router.get("", response_model=QuestionListResponse)
def list_questions(
    initiative_id: UUID,
    iteration: Optional[int] = Query(None, description="Filter by iteration"),
    priority: Optional[QuestionPriority] = Query(None, description="Filter by priority"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all questions for an initiative.

    Optionally filter by iteration or priority.
    """
    # Verify initiative exists and user has access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get questions
    question_repo = QuestionRepository(db)
    answer_repo = AnswerRepository(db)

    if priority:
        questions = question_repo.get_by_priority(initiative_id, priority, iteration)
    else:
        questions = question_repo.get_by_initiative(initiative_id, iteration)

    # Load answers for each question
    questions_with_answers = []
    for question in questions:
        answer = answer_repo.get_by_question(question.id)
        question_data = QuestionWithAnswerResponse.model_validate(question)
        if answer:
            question_data.answer = AnswerResponse.model_validate(answer)
        questions_with_answers.append(question_data)

    # Get counts
    priority_counts = question_repo.count_by_priority(initiative_id, iteration)
    answered_count = answer_repo.get_answered_count(initiative_id)

    return QuestionListResponse(
        questions=questions_with_answers,
        total=len(questions),
        answered_count=answered_count,
        p0_count=priority_counts["P0"],
        p1_count=priority_counts["P1"],
        p2_count=priority_counts["P2"]
    )


@router.get("/{question_id}", response_model=QuestionWithAnswerResponse)
def get_question(
    initiative_id: UUID,
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific question with its answer."""
    # Verify initiative exists and user has access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get question
    question_repo = QuestionRepository(db)
    question = question_repo.get_with_answer(question_id)

    if not question or question.initiative_id != initiative_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Build response
    response = QuestionWithAnswerResponse.model_validate(question)
    if question.answer:
        response.answer = AnswerResponse.model_validate(question.answer)

    return response


@router.put("/{question_id}/answer", response_model=AnswerResponse)
def answer_question(
    initiative_id: UUID,
    question_id: UUID,
    data: AnswerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answer a question (create or update answer).

    Supports status: Answered, Unknown, or Skipped.
    """
    # Verify initiative exists and user has access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Verify question exists
    question_repo = QuestionRepository(db)
    question = question_repo.get_by_id(question_id)

    if not question or question.initiative_id != initiative_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Create or update answer
    answer_repo = AnswerRepository(db)
    answer = answer_repo.upsert_answer(
        question_id=question_id,
        answer_text=data.answer_text,
        answer_status=data.answer_status,
        answered_by=current_user.id
    )

    # Update skip_reason if provided
    if data.skip_reason:
        answer.skip_reason = data.skip_reason

    db.commit()

    return answer


@router.get("/unanswered/count")
def count_unanswered(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unanswered questions for an initiative."""
    # Verify initiative exists and user has access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    answer_repo = AnswerRepository(db)
    unanswered = answer_repo.get_unanswered_questions(initiative_id)

    return {
        "initiative_id": initiative_id,
        "unanswered_count": len(unanswered),
        "unanswered_question_ids": unanswered
    }
