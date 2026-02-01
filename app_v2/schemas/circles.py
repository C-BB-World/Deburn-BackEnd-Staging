"""
Pydantic models for Circles system request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class AvailabilitySlot(BaseModel):
    day: int = Field(..., ge=0, le=6)
    hour: int = Field(..., ge=0, le=23)


class UpdateAvailabilityRequest(BaseModel):
    groupId: str
    slots: List[AvailabilitySlot]


class ScheduleMeetingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    scheduledAt: str
    duration: int = 60
    location: Optional[str] = None
    meetingLink: Optional[str] = None
    timezone: Optional[str] = None
    availableMembers: Optional[List[str]] = None  # Names of members who can attend


class UpdateAttendanceRequest(BaseModel):
    attending: bool


class GroupMember(BaseModel):
    name: str
    avatar: Optional[str] = None


class Group(BaseModel):
    id: str
    name: str
    memberCount: int
    members: List[GroupMember]
    nextMeeting: Optional[str] = None


class UpcomingMeeting(BaseModel):
    id: str
    title: str
    groupName: str
    date: str


class Invitation(BaseModel):
    id: str
    groupName: str
    invitedBy: str


class InviteeItem(BaseModel):
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class SendInvitationsRequest(BaseModel):
    invitees: List[InviteeItem]


class CreatePoolRequest(BaseModel):
    name: str
    organizationId: str
    topic: Optional[str] = None
    description: Optional[str] = None
    targetGroupSize: int = Field(default=4, ge=3, le=6)
    cadence: str = Field(default="biweekly", pattern="^(weekly|biweekly)$")


class MoveMemberRequest(BaseModel):
    memberId: str
    toGroupId: str


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
