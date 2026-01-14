"""
FastAPI dependencies for Calendar system.

Provides dependency injection for calendar-related services.
"""

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.calendar.services.google_calendar_service import GoogleCalendarService
from app_v2.calendar.services.token_encryption import TokenEncryptionService
from app_v2.calendar.services.connection_service import CalendarConnectionService
from app_v2.calendar.services.calendar_availability_service import CalendarAvailabilityService


_google_calendar_service: Optional[GoogleCalendarService] = None
_token_encryption_service: Optional[TokenEncryptionService] = None
_connection_service: Optional[CalendarConnectionService] = None
_availability_service: Optional[CalendarAvailabilityService] = None


def init_calendar_services(db: AsyncIOMotorDatabase) -> None:
    """
    Initialize calendar services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
    """
    global _google_calendar_service, _token_encryption_service
    global _connection_service, _availability_service

    _google_calendar_service = GoogleCalendarService(
        client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", ""),
        webhook_url=os.getenv("CALENDAR_WEBHOOK_URL"),
    )

    encryption_key = os.getenv("CALENDAR_ENCRYPTION_KEY", "")
    if encryption_key:
        _token_encryption_service = TokenEncryptionService(encryption_key=encryption_key)
    else:
        _token_encryption_service = None

    if _token_encryption_service:
        _connection_service = CalendarConnectionService(
            db=db,
            google_calendar=_google_calendar_service,
            token_encryption=_token_encryption_service,
        )

        _availability_service = CalendarAvailabilityService(
            db=db,
            google_calendar=_google_calendar_service,
            connection_service=_connection_service,
        )


def get_google_calendar_service() -> GoogleCalendarService:
    """Get Google Calendar service instance."""
    if _google_calendar_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _google_calendar_service


def get_token_encryption_service() -> TokenEncryptionService:
    """Get token encryption service instance."""
    if _token_encryption_service is None:
        raise RuntimeError("Calendar services not initialized or encryption key not set.")
    return _token_encryption_service


def get_connection_service() -> CalendarConnectionService:
    """Get calendar connection service instance."""
    if _connection_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _connection_service


def get_availability_service() -> CalendarAvailabilityService:
    """Get calendar availability service instance."""
    if _availability_service is None:
        raise RuntimeError("Calendar services not initialized.")
    return _availability_service
