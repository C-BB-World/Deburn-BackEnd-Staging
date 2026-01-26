"""
Pydantic models for User system request/response validation.

Defines schemas for profiles, consents, and account deletion.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    """User profile in API responses."""
    firstName: str
    lastName: Optional[str] = None
    jobTitle: Optional[str] = None
    leadershipLevel: Optional[str] = None
    timezone: str = "UTC"
    preferredLanguage: str = "en"
    email: str
    organization: str
    country: str


class ProfileUpdateRequest(BaseModel):
    """Request body for updating profile."""
    firstName: Optional[str] = Field(None, min_length=1, max_length=50)
    lastName: Optional[str] = Field(None, max_length=50)
    jobTitle: Optional[str] = Field(None, max_length=100)
    leadershipLevel: Optional[str] = Field(
        None,
        description="individual_contributor | team_lead | manager | director | executive"
    )
    timezone: Optional[str] = Field(None, description="IANA timezone")
    preferredLanguage: Optional[str] = Field(None, description="en | sv")


class ConsentRecord(BaseModel):
    """Individual consent record."""
    accepted: bool
    acceptedAt: Optional[datetime] = None
    version: Optional[str] = None


class ConsentsResponse(BaseModel):
    """Response for getting user consents."""
    consents: Dict[str, ConsentRecord]
    needsUpdate: bool
    outdatedConsents: List[str]


class ConsentUpdateRequest(BaseModel):
    """Request body for updating a consent."""
    accepted: bool
    version: str


class ConsentUpdateResponse(BaseModel):
    """Response for consent update."""
    accepted: bool
    acceptedAt: Optional[datetime] = None
    version: str


class DeleteAccountRequest(BaseModel):
    """Request body for account deletion."""
    reason: Optional[str] = Field(None, max_length=500)


class DeleteAccountResponse(BaseModel):
    """Response for account deletion request."""
    scheduledFor: datetime
    message: str = "Account deletion scheduled. Login within 30 days to cancel."


class CancelDeletionResponse(BaseModel):
    """Response for cancelling account deletion."""
    message: str = "Account deletion cancelled successfully"


class UserResponse(BaseModel):
    """Full user information in responses."""
    id: str
    email: str
    status: str
    profile: Dict[str, Any]
    organization: str
    country: str
    createdAt: datetime
    lastLoginAt: Optional[datetime] = None

    class Config:
        from_attributes = True


# Valid voice options for TTS
VALID_VOICES = [
    # High pitch
    "Aria", "Sarah", "Laura", "Alice", "Matilda", "Jessica", "Lily",
    # Low pitch
    "Roger", "Charlie", "George", "Callum", "Liam", "Daniel"
]


class CoachPreferences(BaseModel):
    """Coach preferences for the user."""
    voice: str = Field(default="Alice", description="TTS voice name")


class CoachPreferencesResponse(BaseModel):
    """Response for getting coach preferences."""
    coachPreferences: CoachPreferences


class CoachPreferencesUpdateRequest(BaseModel):
    """Request body for updating coach preferences."""
    coachPreferences: CoachPreferences
