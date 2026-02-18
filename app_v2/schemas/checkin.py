"""
Pydantic models for Check-in system request/response validation.

Matches the API documentation in docs/v2/architecture/api/checkin.md
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================

class CheckInRequest(BaseModel):
    """POST /api/checkin"""
    mood: int = Field(..., ge=1, le=5, description="1-5 scale")
    physicalEnergy: int = Field(..., ge=1, le=10, description="1-10 scale")
    mentalEnergy: int = Field(..., ge=1, le=10, description="1-10 scale")
    sleep: int = Field(..., ge=1, le=5, description="1-5 scale")
    stress: int = Field(..., ge=1, le=10, description="1-10 scale")


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class CheckInResponseData(BaseModel):
    """Response data for POST /api/checkin"""
    streak: int
    insight: str
    tip: str


class TrendResponseData(BaseModel):
    """Response data for GET /api/checkin/trends"""
    dataPoints: int
    moodValues: List[int]
    moodChange: int
    energyValues: List[int]
    energyChange: int
    stressValues: List[int]
    stressChange: int
