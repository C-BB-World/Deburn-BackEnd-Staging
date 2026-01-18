"""
Pydantic models for Circles system request/response validation.

Matches the API documentation in docs/v2/architecture/api/circles.md
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================

class AvailabilitySlot(BaseModel):
    """Single availability slot."""
    dayOfWeek: int = Field(..., ge=0, le=6, description="0=Sunday, 6=Saturday")
    startTime: str = Field(..., description="HH:MM format")
    endTime: str = Field(..., description="HH:MM format")


class UpdateAvailabilityRequest(BaseModel):
    """PUT /api/circles/availability"""
    slots: List[AvailabilitySlot]


class ScheduleMeetingRequest(BaseModel):
    """POST /api/circles/groups/:groupId/meetings"""
    title: str
    description: Optional[str] = None
    scheduledAt: str  # ISO 8601 datetime
    duration: int  # Duration in minutes
    location: Optional[str] = None


class UpdateAttendanceRequest(BaseModel):
    """POST /api/circles/meetings/:meetingId/attendance"""
    attending: bool


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class GroupMember(BaseModel):
    """Group member in responses."""
    name: str
    avatar: Optional[str] = None


class Group(BaseModel):
    """Circle group in responses."""
    id: str
    name: str
    memberCount: int
    members: List[GroupMember]
    nextMeeting: Optional[str] = None


class UpcomingMeeting(BaseModel):
    """Upcoming meeting in responses."""
    id: str
    title: str
    groupName: str
    date: str  # ISO 8601 datetime


class Invitation(BaseModel):
    """Circle invitation in responses."""
    id: str
    groupName: str
    invitedBy: str


# =============================================================================
# Admin Request Schemas
# =============================================================================

class InviteeItem(BaseModel):
    """Single invitee for bulk invitations."""
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class SendInvitationsRequest(BaseModel):
    """POST /api/circles/pools/:id/invitations"""
    invitees: List[InviteeItem]


class CreatePoolRequest(BaseModel):
    """POST /api/circles/pools"""
    name: str
    organizationId: str
    topic: Optional[str] = None
    description: Optional[str] = None
    targetGroupSize: int = Field(default=4, ge=3, le=6)
    cadence: str = Field(default="biweekly", pattern="^(weekly|biweekly)$")
