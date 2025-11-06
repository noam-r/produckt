"""
Schemas for MRD API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class MRDResponse(BaseModel):
    """Schema for MRD response."""
    id: UUID
    initiative_id: UUID
    content: str = Field(..., description="MRD content in Markdown format")
    quality_disclaimer: Optional[str] = Field(None, description="Quality disclaimer text")
    version: int = Field(..., description="Version number (increments on regeneration)")
    word_count: Optional[int] = Field(None, description="Total word count")
    completeness_score: Optional[int] = Field(None, description="Completeness score 0-100")
    readiness_at_generation: Optional[int] = Field(None, description="Readiness score at time of generation")
    assumptions_made: Optional[List[str]] = Field(None, description="List of assumptions")
    generated_by: Optional[UUID] = Field(None, description="User who generated the MRD")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    model_config = {"from_attributes": True}


class MRDContentResponse(BaseModel):
    """Schema for MRD content-only response (for export)."""
    content: str = Field(..., description="MRD content in Markdown format")
    quality_disclaimer: Optional[str] = Field(None, description="Quality disclaimer text")
    word_count: int = Field(..., description="Total word count")
    version: int = Field(..., description="Version number")


class MRDMetadataResponse(BaseModel):
    """Schema for MRD metadata response."""
    word_count: int
    completeness_score: int
    readiness_score: int
    assumptions_count: int
    version: int
