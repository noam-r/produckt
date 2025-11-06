"""
Schemas for Context API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ContextBase(BaseModel):
    """Base schema for Context."""
    company_mission: Optional[str] = Field(None, description="Company mission statement")
    strategic_objectives: Optional[str] = Field(None, description="Strategic objectives")
    target_markets: Optional[str] = Field(None, description="Target markets")
    competitive_landscape: Optional[str] = Field(None, description="Competitive analysis")
    technical_constraints: Optional[str] = Field(None, description="Technical constraints")


class ContextCreate(ContextBase):
    """Schema for creating a new context version."""
    pass


class ContextResponse(ContextBase):
    """Schema for context response."""
    id: UUID
    organization_id: UUID
    version: int
    is_current: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContextListResponse(BaseModel):
    """Schema for context version list."""
    contexts: list[ContextResponse]
    total: int
