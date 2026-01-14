"""
Pydantic models for Check-in system request/response validation.

Defines schemas for check-in operations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MetricsInput(BaseModel):
    """Check-in metrics input."""
    mood: int = Field(..., ge=1, le=5, description="1=struggling, 5=great")
    physicalEnergy: int = Field(..., ge=1, le=10, description="1=exhausted, 10=energized")
    mentalEnergy: int = Field(..., ge=1, le=10, description="1=foggy, 10=sharp")
    sleep: int = Field(..., ge=1, le=5, description="1=poor, 5=great")
    stress: int = Field(..., ge=1, le=10, description="1=calm, 10=overwhelmed")


class CheckInRequest(BaseModel):
    """Request body for submitting a check-in."""
    mood: int = Field(..., ge=1, le=5)
    physicalEnergy: int = Field(..., ge=1, le=10)
    mentalEnergy: int = Field(..., ge=1, le=10)
    sleep: int = Field(..., ge=1, le=5)
    stress: int = Field(..., ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=500)


class CheckInResponse(BaseModel):
    """Check-in data in API responses."""
    id: str
    date: str
    timestamp: datetime
    metrics: MetricsInput
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class SubmitCheckInResponse(BaseModel):
    """Response for check-in submission."""
    streak: int
    insight: str
    tip: str


class TodayCheckInResponse(BaseModel):
    """Response for today's check-in status."""
    hasCheckedInToday: bool
    checkin: Optional[CheckInResponse] = None


class HistoryResponse(BaseModel):
    """Response for check-in history."""
    checkins: List[CheckInResponse]
    total: int
    limit: int
    offset: int
    hasMore: bool


class StreakResponse(BaseModel):
    """Response for streak information."""
    streak: int


class TrendDataResponse(BaseModel):
    """Response for trend data."""
    dataPoints: int
    moodValues: List[int]
    moodChange: Optional[int] = None
    energyValues: List[float]
    energyChange: Optional[int] = None
    stressValues: List[int]
    stressChange: Optional[int] = None
