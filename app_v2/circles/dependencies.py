"""
FastAPI dependencies for Circles system.

Provides dependency injection for circle-related services.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.circles.services.pool_service import PoolService
from app_v2.circles.services.invitation_service import InvitationService
from app_v2.circles.services.group_service import GroupService
from app_v2.circles.services.meeting_service import MeetingService
from app_v2.circles.services.availability_service import AvailabilityService


_pool_service: Optional[PoolService] = None
_invitation_service: Optional[InvitationService] = None
_group_service: Optional[GroupService] = None
_meeting_service: Optional[MeetingService] = None
_availability_service: Optional[AvailabilityService] = None


def init_circles_services(
    db: AsyncIOMotorDatabase,
    calendar_service=None
) -> None:
    """
    Initialize circles services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
        calendar_service: Optional Google Calendar service
    """
    global _pool_service, _invitation_service, _group_service
    global _meeting_service, _availability_service

    _pool_service = PoolService(db=db)
    _invitation_service = InvitationService(db=db)
    _group_service = GroupService(db=db)
    _meeting_service = MeetingService(db=db, calendar_service=calendar_service)
    _availability_service = AvailabilityService(db=db)


def get_pool_service() -> PoolService:
    """Get pool service instance."""
    if _pool_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _pool_service


def get_invitation_service() -> InvitationService:
    """Get invitation service instance."""
    if _invitation_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _invitation_service


def get_group_service() -> GroupService:
    """Get group service instance."""
    if _group_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _group_service


def get_meeting_service() -> MeetingService:
    """Get meeting service instance."""
    if _meeting_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _meeting_service


def get_availability_service() -> AvailabilityService:
    """Get availability service instance."""
    if _availability_service is None:
        raise RuntimeError("Circles services not initialized.")
    return _availability_service
