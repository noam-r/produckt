"""
Schemas for Question and Answer API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from backend.models import QuestionCategory, QuestionPriority, AnswerStatus


class QuestionBase(BaseModel):
    """Base schema for Question."""
    category: QuestionCategory
    priority: QuestionPriority
    question_text: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    blocks_mrd_generation: bool = Field(default=True)


class QuestionResponse(QuestionBase):
    """Schema for question response."""
    id: UUID
    initiative_id: UUID
    iteration: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnswerCreate(BaseModel):
    """Schema for creating/updating an answer."""
    answer_text: Optional[str] = Field(None, description="Answer text (can be None for Unknown/Skipped)")
    answer_status: AnswerStatus = Field(..., description="Answer status")
    skip_reason: Optional[str] = Field(None, description="Reason for skipping (if status=Skipped)")


class AnswerResponse(BaseModel):
    """Schema for answer response."""
    id: UUID
    question_id: UUID
    answer_text: Optional[str]
    answer_status: AnswerStatus
    skip_reason: Optional[str]
    answered_by: UUID
    answered_at: datetime

    model_config = {"from_attributes": True}


class QuestionWithAnswerResponse(QuestionResponse):
    """Schema for question with answer included."""
    answer: Optional[AnswerResponse] = None


class QuestionListResponse(BaseModel):
    """Schema for question list response."""
    questions: list[QuestionWithAnswerResponse]
    total: int
    answered_count: int
    p0_count: int
    p1_count: int
    p2_count: int
