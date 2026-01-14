"""
Pydantic models for Circles system request/response validation.

Defines schemas for pools, invitations, groups, and meetings.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class InvitationSettingsInput(BaseModel):
    """Invitation settings for a pool."""
    expiryDays: int = Field(default=14, ge=1, le=90)
    customMessage: Optional[str] = Field(None, max_length=500)


class CreatePoolRequest(BaseModel):
    """Request body for creating a pool."""
    name: str = Field(..., min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    targetGroupSize: int = Field(default=4, ge=3, le=6)
    cadence: str = Field(default="biweekly", description="weekly | biweekly")
    invitationSettings: Optional[InvitationSettingsInput] = None


class UpdatePoolRequest(BaseModel):
    """Request body for updating a pool."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    topic: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    targetGroupSize: Optional[int] = Field(None, ge=3, le=6)
    cadence: Optional[str] = None
    invitationSettings: Optional[InvitationSettingsInput] = None


class PoolStatsResponse(BaseModel):
    """Pool statistics."""
    pending: int
    accepted: int
    declined: int
    groups: int
    canAssign: bool


class PoolResponse(BaseModel):
    """Pool in API responses."""
    id: str
    organizationId: str
    name: str
    topic: Optional[str] = None
    description: Optional[str] = None
    targetGroupSize: int
    cadence: str
    status: str
    stats: Dict[str, Any]
    createdBy: str
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class InviteeInput(BaseModel):
    """Individual invitee."""
    email: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class SendInvitationsRequest(BaseModel):
    """Request body for sending invitations."""
    invitees: List[InviteeInput]


class InvitationResponse(BaseModel):
    """Invitation in API responses."""
    id: str
    poolId: str
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    status: str
    expiresAt: datetime
    createdAt: datetime

    class Config:
        from_attributes = True


class SendInvitationsResponse(BaseModel):
    """Response for sending invitations."""
    sent: List[Dict[str, str]]
    failed: List[Dict[str, str]]
    duplicate: List[Dict[str, str]]


class GroupMemberResponse(BaseModel):
    """Group member in responses."""
    id: str
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class GroupResponse(BaseModel):
    """Group in API responses."""
    id: str
    poolId: str
    name: str
    members: List[str]
    status: str
    leaderId: Optional[str] = None
    stats: Dict[str, Any]
    createdAt: datetime

    class Config:
        from_attributes = True


class AssignGroupsResponse(BaseModel):
    """Response for group assignment."""
    groups: List[GroupResponse]
    totalMembers: int


class ScheduleMeetingRequest(BaseModel):
    """Request body for scheduling a meeting."""
    title: Optional[str] = Field(None, max_length=200)
    topic: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    scheduledAt: datetime
    duration: int = Field(default=60, ge=15, le=180)
    timezone: str = Field(default="Europe/Stockholm")


class MeetingAttendeeResponse(BaseModel):
    """Meeting attendee in responses."""
    userId: str
    status: str
    respondedAt: Optional[datetime] = None


class MeetingResponse(BaseModel):
    """Meeting in API responses."""
    id: str
    groupId: str
    title: str
    topic: Optional[str] = None
    description: Optional[str] = None
    scheduledAt: datetime
    duration: int
    timezone: str
    meetingLink: Optional[str] = None
    status: str
    scheduledBy: str
    attendance: List[MeetingAttendeeResponse]
    createdAt: datetime

    class Config:
        from_attributes = True


class AvailabilitySlot(BaseModel):
    """Single availability slot."""
    day: int = Field(..., ge=0, le=6, description="0=Sunday, 6=Saturday")
    hour: int = Field(..., ge=0, le=23)


class UpdateAvailabilityRequest(BaseModel):
    """Request body for updating availability."""
    slots: List[AvailabilitySlot]
    timezone: str = Field(default="UTC")


class AvailabilityResponse(BaseModel):
    """User availability in responses."""
    userId: str
    slots: List[AvailabilitySlot]
    timezone: str


class GroupAvailabilityResponse(BaseModel):
    """Group availability status."""
    commonSlots: List[AvailabilitySlot]
    totalMembers: int
    membersWithAvailability: int
    membersWithoutAvailability: int
    allMembersSet: bool
