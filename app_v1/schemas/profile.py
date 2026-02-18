"""
Profile request/response schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ProfileUpdateRequest(BaseModel):
    """Profile update request."""

    firstName: Optional[str] = Field(None, max_length=50)
    lastName: Optional[str] = Field(None, max_length=50)
    jobTitle: Optional[str] = Field(None, max_length=100)
    leadershipLevel: Optional[str] = Field(None, pattern=r"^(new|mid|senior|executive)$")
    preferredLanguage: Optional[str] = Field(None, pattern=r"^(en|sv)$")
    timezone: Optional[str] = None


class ProfileResponse(BaseModel):
    """User profile response."""

    firstName: Optional[str] = None
    lastName: Optional[str] = None
    jobTitle: Optional[str] = None
    leadershipLevel: Optional[str] = None
    preferredLanguage: str = "en"
    timezone: Optional[str] = None
    avatarUrl: Optional[str] = None
