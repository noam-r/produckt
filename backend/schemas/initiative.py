"""
Schemas for Initiative API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from backend.models import InitiativeStatus


class InitiativeBase(BaseModel):
    """Base schema for Initiative."""
    title: str = Field(..., min_length=1, max_length=255, description="Initiative title")
    description: str = Field(..., min_length=1, description="Initiative description")


class InitiativeCreate(InitiativeBase):
    """Schema for creating a new initiative."""
    pass


class InitiativeUpdate(BaseModel):
    """Schema for updating an initiative."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[InitiativeStatus] = None


class InitiativeResponse(InitiativeBase):
    """Schema for initiative response."""
    id: UUID
    status: InitiativeStatus
    readiness_score: Optional[float] = None
    iteration_count: int
    organization_id: UUID
    created_by: UUID
    context_snapshot_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    # Workflow completion tracking
    has_questions: bool = False
    has_evaluation: bool = False
    has_mrd: bool = False
    has_scores: bool = False
    completion_percentage: int = 0

    model_config = {"from_attributes": True}


class InitiativeListResponse(BaseModel):
    """Schema for paginated initiative list."""
    initiatives: list[InitiativeResponse]
    total: int
    limit: int
    offset: int


class InitiativeStatusUpdate(BaseModel):
    """Schema for updating initiative status."""
    status: InitiativeStatus = Field(..., description="New status")
