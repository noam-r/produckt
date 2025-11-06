"""
Schemas for Score API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class RICEScoreData(BaseModel):
    """RICE score components."""
    reach: int = Field(..., description="Number of users affected per time period")
    impact: float = Field(..., description="Impact score (0.25, 0.5, 1, 2, 3)")
    confidence: int = Field(..., ge=0, le=100, description="Confidence percentage (0-100)")
    effort: float = Field(..., gt=0, description="Person-months of effort")
    rice_score: float = Field(..., description="Calculated RICE score")
    reasoning: Dict[str, str] = Field(..., description="Reasoning for each component")


class FDVScoreData(BaseModel):
    """FDV score components."""
    feasibility: int = Field(..., ge=1, le=10, description="Feasibility score (1-10)")
    desirability: int = Field(..., ge=1, le=10, description="Desirability score (1-10)")
    viability: int = Field(..., ge=1, le=10, description="Viability score (1-10)")
    fdv_score: float = Field(..., description="Calculated FDV score (average)")
    reasoning: Dict[str, str] = Field(..., description="Reasoning for each component")


class ScoreResponse(BaseModel):
    """Schema for Score response."""
    id: UUID
    initiative_id: UUID

    # RICE
    reach: Optional[int] = None
    impact: Optional[float] = None
    confidence: Optional[int] = None
    effort: Optional[float] = None
    rice_score: Optional[float] = None
    rice_reasoning: Optional[Dict] = None

    # FDV
    feasibility: Optional[int] = None
    desirability: Optional[int] = None
    viability: Optional[int] = None
    fdv_score: Optional[float] = None
    fdv_reasoning: Optional[Dict] = None

    # Data quality tracking
    data_quality: Optional[Dict] = None
    warnings: Optional[list] = None

    # Metadata
    scored_by: Optional[UUID] = None
    scored_at: datetime

    model_config = {"from_attributes": True}


class ScoreSummary(BaseModel):
    """Summary of scores for quick comparison."""
    initiative_id: UUID
    initiative_title: str
    rice_score: Optional[float] = None
    fdv_score: Optional[float] = None
    scored_at: datetime
