"""
FastAPI router for Calendar system endpoints.

Provides endpoints for OAuth, connections, and availability.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from fastapi.responses import RedirectResponse

from app_v2.dependencies import (
    require_auth,
    get_connection_service,
    get_calendar_availability_service,
)
from app_v2.services.calendar.connection_service import CalendarConnectionService
from app_v2.services.calendar.calendar_availability_service import CalendarAvailabilityService
from app_v2.schemas.calendar import (
    CalendarConnectionResponse,
    CalendarAuthUrlResponse,
    UserAvailabilityResponse,
    GroupAvailabilityResponse,
    AvailabilitySlot,
    WorkingHoursResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _format_connection(connection: dict) -> dict:
    """Format connection document for response."""
    return {
        "id": str(connection["_id"]),
        "provider": connection["provider"],
        "providerEmail": connection.get("providerEmail"),
        "status": connection["status"],
        "calendarIds": connection.get("calendarIds", []),
        "primaryCalendarId": connection.get("primaryCalendarId"),
        "connectedAt": connection["connectedAt"],
        "lastSyncAt": connection.get("lastSyncAt"),
    }


@router.get("/auth/google", response_model=CalendarAuthUrlResponse)
async def get_google_auth_url(
    user: Annotated[dict, Depends(require_auth)],
    connection_service: Annotated[CalendarConnectionService, Depends(get_connection_service)],
    return_url: Optional[str] = Query(None, description="URL to redirect after connection"),
):
    """Get Google OAuth authorization URL."""
    auth_url = connection_service.get_auth_url(
        user_id=str(user["_id"]),
        return_url=return_url
    )
    return CalendarAuthUrlResponse(authUrl=auth_url)


@router.get("/auth/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    connection_service: Annotated[CalendarConnectionService, Depends(get_connection_service)],
    error: Optional[str] = None,
):
    """Handle Google OAuth callback."""
    if error:
        logger.warning(f"OAuth error: {error}")
        return RedirectResponse(url="/circles?calendar_error=denied")

    try:
        result = await connection_service.handle_oauth_callback(code=code, state=state)
        return_url = result.get("returnUrl") or "/circles"
        return RedirectResponse(url=f"{return_url}?calendar_connected=true")

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(url="/circles?calendar_error=failed")


@router.get("/connection", response_model=Optional[CalendarConnectionResponse])
async def get_connection(
    user: Annotated[dict, Depends(require_auth)],
    connection_service: Annotated[CalendarConnectionService, Depends(get_connection_service)],
):
    """Get current user's calendar connection."""
    connection = await connection_service.get_connection(str(user["_id"]))
    if not connection:
        return None
    return CalendarConnectionResponse(**_format_connection(connection))


@router.delete("/connection")
async def disconnect_calendar(
    user: Annotated[dict, Depends(require_auth)],
    connection_service: Annotated[CalendarConnectionService, Depends(get_connection_service)],
):
    """Disconnect calendar and revoke tokens."""
    success = await connection_service.disconnect(str(user["_id"]))
    return {"disconnected": success}


@router.get("/availability", response_model=UserAvailabilityResponse)
async def get_user_availability(
    user: Annotated[dict, Depends(require_auth)],
    availability_service: Annotated[CalendarAvailabilityService, Depends(get_calendar_availability_service)],
    connection_service: Annotated[CalendarConnectionService, Depends(get_connection_service)],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_duration: int = Query(60, ge=15, le=180),
    timezone_str: str = Query("Europe/Stockholm", alias="timezone"),
):
    """Get current user's availability."""
    if not start_date:
        start_date = datetime.now(timezone.utc)
    if not end_date:
        end_date = start_date + timedelta(days=14)

    slots = await availability_service.get_user_availability(
        user_id=str(user["_id"]),
        start_date=start_date,
        end_date=end_date,
        min_duration=min_duration
    )

    connection = await connection_service.get_connection(str(user["_id"]))
    source = "calendar" if connection and connection.get("status") == "active" else "manual"

    converted_slots = availability_service.convert_to_timezone(slots, timezone_str)

    return UserAvailabilityResponse(
        slots=[AvailabilitySlot(**s) for s in converted_slots],
        source=source,
        timezone=timezone_str
    )


@router.get("/groups/{group_id}/availability", response_model=GroupAvailabilityResponse)
async def get_group_availability(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
    availability_service: Annotated[CalendarAvailabilityService, Depends(get_calendar_availability_service)],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_duration: int = Query(60, ge=15, le=180),
    max_slots: int = Query(5, ge=1, le=20),
    timezone_str: str = Query("Europe/Stockholm", alias="timezone"),
):
    """Get common availability for a group."""
    result = await availability_service.find_group_availability(
        group_id=group_id,
        start_date=start_date,
        end_date=end_date,
        min_duration=min_duration,
        max_slots=max_slots
    )

    converted_slots = availability_service.convert_to_timezone(result["slots"], timezone_str)

    return GroupAvailabilityResponse(
        slots=[AvailabilitySlot(**s) for s in converted_slots],
        totalFound=result["totalFound"],
        usersWithCalendar=result["usersWithCalendar"],
        usersWithManual=result["usersWithManual"],
        errors=result["errors"]
    )


@router.get("/working-hours", response_model=WorkingHoursResponse)
async def get_working_hours(
    user: Annotated[dict, Depends(require_auth)],
    availability_service: Annotated[CalendarAvailabilityService, Depends(get_calendar_availability_service)],
):
    """Get current user's working hours configuration."""
    working_hours = await availability_service.get_user_working_hours(str(user["_id"]))
    return WorkingHoursResponse(**working_hours)


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    connection_service: Annotated[CalendarConnectionService, Depends(get_connection_service)],
):
    """Handle Google Calendar webhook notifications."""
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_id = request.headers.get("X-Goog-Resource-ID")
    token = request.headers.get("X-Goog-Channel-Token")

    if not all([channel_id, resource_id, token]):
        logger.warning("Webhook missing required headers")
        return Response(status_code=200)

    connection = await connection_service.handle_webhook(
        channel_id=channel_id,
        resource_id=resource_id,
        token=token
    )

    if not connection:
        return Response(status_code=200)

    logger.info(f"Webhook received for user {connection['userId']}")

    return Response(status_code=200)
