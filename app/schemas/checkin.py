"""
Check-in request/response schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    """Daily check-in request."""

    mood: int = Field(ge=1, le=5, description="Mood rating 1-5")
    physicalEnergy: int = Field(ge=1, le=10, description="Physical energy 1-10")
    mentalEnergy: int = Field(ge=1, le=10, description="Mental energy 1-10")
    sleep: int = Field(ge=1, le=5, description="Sleep quality 1-5")
    stress: int = Field(ge=1, le=10, description="Stress level 1-10")
    notes: Optional[str] = Field(None, max_length=500)


class CheckInMetrics(BaseModel):
    """Check-in metrics."""

    mood: int
    physicalEnergy: int
    mentalEnergy: int
    sleep: int
    stress: int


class CheckInResponse(BaseModel):
    """Check-in data in response."""

    id: str
    date: str
    timestamp: datetime
    metrics: CheckInMetrics
    notes: Optional[str] = None


class StreakResponse(BaseModel):
    """Streak data in response."""

    current: int
    longest: int


class MetricDataPoint(BaseModel):
    """Single data point for a metric."""

    date: str
    value: int


class MetricTrend(BaseModel):
    """Trend data for a single metric."""

    values: List[MetricDataPoint]
    average: Optional[float] = None
    trend: Optional[str] = None  # "improving", "stable", "declining"
    change: Optional[float] = None


class TrendData(BaseModel):
    """Alias for MetricTrend."""

    values: List[MetricDataPoint]
    average: Optional[float] = None
    trend: Optional[str] = None
    change: Optional[float] = None


class TrendsResponse(BaseModel):
    """Check-in trends response."""

    period: int
    dataPoints: int
    mood: MetricTrend
    physicalEnergy: MetricTrend
    mentalEnergy: MetricTrend
    sleep: MetricTrend
    stress: MetricTrend
