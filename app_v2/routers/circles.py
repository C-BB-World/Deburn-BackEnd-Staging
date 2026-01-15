"""
FastAPI router for Circles system endpoints.

Provides endpoints for groups, meetings, invitations, and availability.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.dependencies import (
    require_auth,
    get_group_service,
    get_meeting_service,
    get_invitation_service,
    get_availability_service,
)
from app_v2.schemas.circles import (
    UpdateAvailabilityRequest,
    ScheduleMeetingRequest,
    UpdateAttendanceRequest,
)
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/circles", tags=["circles"])


@router.get("/my-groups")
async def get_my_groups(
    user: Annotated[dict, Depends(require_auth)],
):
    """Get current user's circle groups."""
    group_service = get_group_service()
    user_id = str(user["_id"])

    groups = await group_service.get_groups_for_user(user_id)

    formatted_groups = []
    for g in groups:
        formatted_groups.append({
            "id": str(g["_id"]),
            "name": g.get("name", ""),
            "memberCount": len(g.get("members", [])),
            "members": [
                {"name": "Member", "avatar": None}
                for _ in g.get("members", [])
            ],
            "nextMeeting": None,  # TODO: Get from meetings
        })

    return success_response({
        "groups": formatted_groups,
        "upcomingMeetings": [],
    })


@router.get("/my-invitations")
async def get_my_invitations(
    user: Annotated[dict, Depends(require_auth)],
):
    """Get current user's invitations (pending and accepted)."""
    invitation_service = get_invitation_service()
    user_id = str(user["_id"])

    pending = await invitation_service.get_pending_invitations_for_user(user_id)
    accepted = await invitation_service.get_accepted_invitations_for_user(user_id)

    return success_response({
        "invitations": [
            {
                "id": str(inv["_id"]),
                "groupName": inv.get("poolName", ""),
                "invitedBy": inv.get("invitedBy", ""),
            }
            for inv in pending
        ]
    })


@router.get("/availability")
async def get_user_availability(
    user: Annotated[dict, Depends(require_auth)],
):
    """Get current user's availability slots."""
    availability_service = get_availability_service()
    user_id = str(user["_id"])

    result = await availability_service.get_user_availability(user_id)

    slots = []
    if result:
        for s in result.get("slots", []):
            slots.append({
                "dayOfWeek": s.get("dayOfWeek", s.get("day", 0)),
                "startTime": s.get("startTime", f"{s.get('hour', 0):02d}:00"),
                "endTime": s.get("endTime", f"{s.get('hour', 0) + 1:02d}:00"),
            })

    return success_response({"slots": slots})


@router.put("/availability")
async def update_availability(
    body: UpdateAvailabilityRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Update user's weekly availability."""
    availability_service = get_availability_service()
    user_id = str(user["_id"])

    slots = [s.model_dump() for s in body.slots]
    await availability_service.update_availability(
        user_id=user_id,
        slots=slots,
        user_timezone="UTC"
    )

    return success_response({"slots": slots})


@router.get("/groups/{group_id}")
async def get_group(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get group by ID."""
    group_service = get_group_service()

    group = await group_service.get_group(group_id)

    return success_response({
        "id": str(group["_id"]),
        "name": group.get("name", ""),
        "memberCount": len(group.get("members", [])),
        "members": [
            {"name": "Member", "avatar": None}
            for _ in group.get("members", [])
        ],
        "nextMeeting": None,
    })


@router.get("/groups/{group_id}/meetings")
async def get_group_meetings(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get meetings for a group."""
    meeting_service = get_meeting_service()

    meetings = await meeting_service.get_meetings_for_group(
        group_id=group_id,
        upcoming=True
    )

    return success_response({
        "meetings": [
            {
                "id": str(m["_id"]),
                "title": m.get("title", ""),
                "groupName": "",
                "date": m.get("scheduledAt", "").isoformat() if m.get("scheduledAt") else "",
            }
            for m in meetings
        ]
    })


@router.get("/groups/{group_id}/common-availability")
async def get_common_availability(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get common availability slots for a group."""
    availability_service = get_availability_service()

    result = await availability_service.get_group_availability_status(group_id)

    slots = []
    for s in result.get("commonSlots", []):
        slots.append({
            "dayOfWeek": s.get("dayOfWeek", s.get("day", 0)),
            "startTime": s.get("startTime", ""),
            "endTime": s.get("endTime", ""),
            "availableCount": s.get("availableCount", 0),
        })

    return success_response({"slots": slots})


@router.post("/groups/{group_id}/meetings")
async def schedule_meeting(
    group_id: str,
    body: ScheduleMeetingRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Schedule a new meeting for the group."""
    meeting_service = get_meeting_service()

    meeting = await meeting_service.schedule_meeting(
        group_id=group_id,
        scheduled_by=str(user["_id"]),
        title=body.title,
        topic=None,
        description=body.description,
        scheduled_at=body.scheduledAt,
        duration=body.duration,
        meeting_timezone="UTC"
    )

    return success_response({
        "id": str(meeting["_id"]),
        "title": meeting.get("title", ""),
        "groupName": "",
        "date": meeting.get("scheduledAt", ""),
    })


@router.get("/invitations/{token}")
async def get_invitation(
    token: str,
):
    """Get invitation details by token."""
    invitation_service = get_invitation_service()

    invitation = await invitation_service.get_invitation_by_token(token)

    if not invitation:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"message": "Invitation not found or expired"})

    return success_response({
        "invitation": {
            "id": str(invitation["_id"]),
            "token": invitation.get("token"),
            "poolName": invitation.get("poolName", ""),
            "expiresAt": invitation.get("expiresAt"),
        },
        "pool": {"name": invitation.get("poolName", "")},
    })


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Accept an invitation."""
    invitation_service = get_invitation_service()

    await invitation_service.accept_invitation(
        token=token,
        user_id=str(user["_id"])
    )

    return success_response({"message": "Invitation accepted"})


@router.post("/invitations/{token}/decline")
async def decline_invitation(
    token: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Decline an invitation."""
    invitation_service = get_invitation_service()

    await invitation_service.decline_invitation(
        token=token,
        user_id=str(user["_id"])
    )

    return success_response({"message": "Invitation declined"})


@router.post("/meetings/{meeting_id}/cancel")
async def cancel_meeting(
    meeting_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Cancel a scheduled meeting."""
    meeting_service = get_meeting_service()

    await meeting_service.cancel_meeting(
        meeting_id=meeting_id,
        cancelled_by=str(user["_id"])
    )

    return success_response({"message": "Meeting cancelled"})


@router.post("/meetings/{meeting_id}/attendance")
async def update_meeting_attendance(
    meeting_id: str,
    body: UpdateAttendanceRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Update attendance for a meeting."""
    meeting_service = get_meeting_service()

    status = "confirmed" if body.attending else "declined"
    await meeting_service.update_attendance(
        meeting_id=meeting_id,
        user_id=str(user["_id"]),
        status=status
    )

    return success_response({"message": "Attendance updated"})
