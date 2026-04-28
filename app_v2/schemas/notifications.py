"""
Pydantic models for Notifications system request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# Response Schemas
# =============================================================================

class NotificationItem(BaseModel):
    """Single notification in responses."""
    id: str
    type: str
    title: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    read: bool
    readAt: Optional[str] = None
    createdAt: str


class NotificationsResponse(BaseModel):
    """GET /api/notifications response."""
    notifications: List[NotificationItem]
    total: int
    hasMore: bool


class UnreadCountResponse(BaseModel):
    """GET /api/notifications/count response."""
    unread: int


class MarkAsReadResponse(BaseModel):
    """POST /api/notifications/:id/read response."""
    message: str
