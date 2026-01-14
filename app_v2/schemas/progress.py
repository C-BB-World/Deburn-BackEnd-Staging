"""
Pydantic models for Progress system request/response validation.

Defines schemas for stats and insights.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class StatsResponse(BaseModel):
    """User progress statistics."""
    streak: int
    checkins: int
    lessons: int
    sessions: int


class InsightResponse(BaseModel):
    """Insight in API responses."""
    id: str
    userId: str
    type: str
    trigger: str
    title: str
    description: str
    metrics: Dict[str, Any] = {}
    isRead: bool = False
    expiresAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class InsightsListResponse(BaseModel):
    """List of insights."""
    insights: List[InsightResponse]


class UnreadCountResponse(BaseModel):
    """Unread insights count."""
    count: int
