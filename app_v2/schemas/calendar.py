"""
Pydantic models for Calendar system request/response validation.

Defines schemas for calendar connections, availability, and webhooks.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CalendarConnectionResponse(BaseModel):
    """Calendar connection in API responses."""
    id: str
    provider: str
    providerEmail: Optional[str] = None
    status: str
    calendarIds: List[str] = []
    primaryCalendarId: Optional[str] = None
    connectedAt: datetime
    lastSyncAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class CalendarAuthUrlResponse(BaseModel):
    """Response for OAuth URL request."""
    authUrl: str


class AvailabilitySlot(BaseModel):
    """Single availability slot."""
    start: datetime
    end: datetime
    duration: int = Field(..., description="Duration in minutes")


class UserAvailabilityResponse(BaseModel):
    """User availability response."""
    slots: List[AvailabilitySlot]
    source: str = Field(..., description="calendar | manual")
    timezone: str


class GroupAvailabilityResponse(BaseModel):
    """Group availability response."""
    slots: List[AvailabilitySlot]
    totalFound: int
    usersWithCalendar: int
    usersWithManual: int
    errors: List[str] = []


class AvailabilityQueryParams(BaseModel):
    """Query parameters for availability."""
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    minDuration: int = Field(default=60, ge=15, le=180)
    maxSlots: int = Field(default=5, ge=1, le=20)
    timezone: str = Field(default="Europe/Stockholm")


class WorkingHoursInput(BaseModel):
    """Working hours configuration."""
    startHour: int = Field(default=9, ge=0, le=23)
    endHour: int = Field(default=18, ge=0, le=23)
    workDays: List[int] = Field(
        default=[1, 2, 3, 4, 5],
        description="0=Monday, 6=Sunday"
    )
    timezone: str = Field(default="Europe/Stockholm")


class WorkingHoursResponse(BaseModel):
    """Working hours in API responses."""
    startHour: int
    endHour: int
    workDays: List[int]
    timezone: str


class CalendarListItem(BaseModel):
    """Calendar in list response."""
    id: str
    summary: str
    primary: bool = False


class CalendarListResponse(BaseModel):
    """List of user's calendars."""
    calendars: List[CalendarListItem]
    primaryCalendarId: Optional[str] = None


class WebhookValidationResponse(BaseModel):
    """Response for webhook validation."""
    valid: bool
    message: Optional[str] = None


class ConflictDetail(BaseModel):
    """Conflict detail for scheduling."""
    userId: str
    conflictStart: datetime
    conflictEnd: datetime


class ConflictCheckRequest(BaseModel):
    """Request to check for conflicts."""
    userIds: List[str]
    start: datetime
    end: datetime


class ConflictCheckResponse(BaseModel):
    """Response for conflict check."""
    hasConflicts: bool
    conflicts: List[ConflictDetail] = []
