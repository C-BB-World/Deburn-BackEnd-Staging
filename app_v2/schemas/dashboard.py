"""
Pydantic models for Dashboard request/response validation.

Matches the API documentation in docs/v2/architecture/api/dashboard.md
"""

from typing import Optional
from pydantic import BaseModel


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class TodaysCheckin(BaseModel):
    """Today's check-in data."""
    mood: int
    physicalEnergy: int
    mentalEnergy: int
    sleep: int
    stress: int


class TodaysFocus(BaseModel):
    """Today's focus module."""
    title: str
    progress: int


class NextCircle(BaseModel):
    """Next circle meeting info."""
    date: str
