"""
FastAPI router for Circles system endpoints.

Provides endpoints for pools, invitations, groups, meetings, and availability.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app_v2.auth.dependencies import require_auth
from app_v2.circles.dependencies import (
    get_pool_service,
    get_invitation_service,
    get_group_service,
    get_meeting_service,
    get_availability_service,
)
from app_v2.circles.services.pool_service import PoolService
from app_v2.circles.services.invitation_service import InvitationService
from app_v2.circles.services.group_service import GroupService
from app_v2.circles.services.meeting_service import MeetingService
from app_v2.circles.services.availability_service import AvailabilityService
from app_v2.circles.models import (
    CreatePoolRequest,
    UpdatePoolRequest,
    PoolResponse,
    PoolStatsResponse,
    SendInvitationsRequest,
    SendInvitationsResponse,
    InvitationResponse,
    GroupResponse,
    AssignGroupsResponse,
    ScheduleMeetingRequest,
    MeetingResponse,
    MeetingAttendeeResponse,
    UpdateAvailabilityRequest,
    AvailabilityResponse,
    AvailabilitySlot,
    GroupAvailabilityResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/circles", tags=["circles"])


def _format_pool(pool: dict) -> dict:
    """Format pool document for response."""
    return {
        "id": str(pool["_id"]),
        "organizationId": str(pool["organizationId"]),
        "name": pool["name"],
        "topic": pool.get("topic"),
        "description": pool.get("description"),
        "targetGroupSize": pool["targetGroupSize"],
        "cadence": pool["cadence"],
        "status": pool["status"],
        "stats": pool.get("stats", {}),
        "createdBy": str(pool["createdBy"]),
        "createdAt": pool["createdAt"],
        "updatedAt": pool["updatedAt"]
    }


def _format_group(group: dict) -> dict:
    """Format group document for response."""
    return {
        "id": str(group["_id"]),
        "poolId": str(group["poolId"]),
        "name": group["name"],
        "members": [str(m) for m in group.get("members", [])],
        "status": group["status"],
        "leaderId": str(group["leaderId"]) if group.get("leaderId") else None,
        "stats": group.get("stats", {}),
        "createdAt": group["createdAt"]
    }


def _format_meeting(meeting: dict) -> dict:
    """Format meeting document for response."""
    return {
        "id": str(meeting["_id"]),
        "groupId": str(meeting["groupId"]),
        "title": meeting["title"],
        "topic": meeting.get("topic"),
        "description": meeting.get("description"),
        "scheduledAt": meeting["scheduledAt"],
        "duration": meeting["duration"],
        "timezone": meeting["timezone"],
        "meetingLink": meeting.get("meetingLink"),
        "status": meeting["status"],
        "scheduledBy": str(meeting["scheduledBy"]),
        "attendance": [
            {
                "userId": str(a["userId"]),
                "status": a["status"],
                "respondedAt": a.get("respondedAt")
            }
            for a in meeting.get("attendance", [])
        ],
        "createdAt": meeting["createdAt"]
    }


@router.post("/pools", response_model=PoolResponse)
async def create_pool(
    body: CreatePoolRequest,
    user: Annotated[dict, Depends(require_auth)],
    pool_service: Annotated[PoolService, Depends(get_pool_service)],
    organization_id: str = Query(..., description="Organization ID"),
):
    """Create a new circle pool."""
    pool = await pool_service.create_pool(
        organization_id=organization_id,
        name=body.name,
        created_by=str(user["_id"]),
        topic=body.topic,
        description=body.description,
        target_group_size=body.targetGroupSize,
        cadence=body.cadence,
        invitation_settings=body.invitationSettings.model_dump() if body.invitationSettings else None
    )

    return PoolResponse(**_format_pool(pool))


@router.get("/pools/{pool_id}", response_model=PoolResponse)
async def get_pool(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
    pool_service: Annotated[PoolService, Depends(get_pool_service)],
):
    """Get pool by ID."""
    pool = await pool_service.get_pool(pool_id)
    return PoolResponse(**_format_pool(pool))


@router.get("/pools/{pool_id}/stats", response_model=PoolStatsResponse)
async def get_pool_stats(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
    pool_service: Annotated[PoolService, Depends(get_pool_service)],
):
    """Get pool statistics."""
    stats = await pool_service.get_pool_stats(pool_id)
    return PoolStatsResponse(**stats)


@router.post("/pools/{pool_id}/invitations", response_model=SendInvitationsResponse)
async def send_invitations(
    pool_id: str,
    body: SendInvitationsRequest,
    user: Annotated[dict, Depends(require_auth)],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
):
    """Send invitations to a pool."""
    invitees = [inv.model_dump() for inv in body.invitees]

    result = await invitation_service.send_invitations(
        pool_id=pool_id,
        invitees=invitees,
        invited_by=str(user["_id"])
    )

    return SendInvitationsResponse(**result)


@router.post("/invitations/{token}/accept", response_model=InvitationResponse)
async def accept_invitation(
    token: str,
    user: Annotated[dict, Depends(require_auth)],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
):
    """Accept an invitation."""
    invitation = await invitation_service.accept_invitation(
        token=token,
        user_id=str(user["_id"])
    )

    return InvitationResponse(
        id=str(invitation["_id"]),
        poolId=str(invitation["poolId"]),
        email=invitation["email"],
        firstName=invitation.get("firstName"),
        lastName=invitation.get("lastName"),
        status=invitation["status"],
        expiresAt=invitation["expiresAt"],
        createdAt=invitation["createdAt"]
    )


@router.post("/pools/{pool_id}/assign", response_model=AssignGroupsResponse)
async def assign_groups(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
    group_service: Annotated[GroupService, Depends(get_group_service)],
):
    """Assign accepted invitees to groups."""
    result = await group_service.assign_groups(
        pool_id=pool_id,
        user_id=str(user["_id"])
    )

    return AssignGroupsResponse(
        groups=[GroupResponse(**_format_group(g)) for g in result["groups"]],
        totalMembers=result["totalMembers"]
    )


@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
    group_service: Annotated[GroupService, Depends(get_group_service)],
):
    """Get group by ID."""
    group = await group_service.get_group(group_id)
    return GroupResponse(**_format_group(group))


@router.get("/my-groups", response_model=list[GroupResponse])
async def get_my_groups(
    user: Annotated[dict, Depends(require_auth)],
    group_service: Annotated[GroupService, Depends(get_group_service)],
):
    """Get current user's groups."""
    groups = await group_service.get_groups_for_user(str(user["_id"]))
    return [GroupResponse(**_format_group(g)) for g in groups]


@router.post("/groups/{group_id}/meetings", response_model=MeetingResponse)
async def schedule_meeting(
    group_id: str,
    body: ScheduleMeetingRequest,
    user: Annotated[dict, Depends(require_auth)],
    meeting_service: Annotated[MeetingService, Depends(get_meeting_service)],
):
    """Schedule a meeting for a group."""
    meeting = await meeting_service.schedule_meeting(
        group_id=group_id,
        scheduled_by=str(user["_id"]),
        title=body.title,
        topic=body.topic,
        description=body.description,
        scheduled_at=body.scheduledAt,
        duration=body.duration,
        meeting_timezone=body.timezone
    )

    return MeetingResponse(**_format_meeting(meeting))


@router.get("/groups/{group_id}/meetings", response_model=list[MeetingResponse])
async def get_group_meetings(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
    meeting_service: Annotated[MeetingService, Depends(get_meeting_service)],
    upcoming: bool = True,
):
    """Get meetings for a group."""
    meetings = await meeting_service.get_meetings_for_group(
        group_id=group_id,
        upcoming=upcoming
    )
    return [MeetingResponse(**_format_meeting(m)) for m in meetings]


@router.get("/my-meetings", response_model=list[MeetingResponse])
async def get_my_meetings(
    user: Annotated[dict, Depends(require_auth)],
    meeting_service: Annotated[MeetingService, Depends(get_meeting_service)],
    upcoming: bool = True,
):
    """Get current user's meetings."""
    meetings = await meeting_service.get_meetings_for_user(
        user_id=str(user["_id"]),
        upcoming=upcoming
    )
    return [MeetingResponse(**_format_meeting(m)) for m in meetings]


@router.put("/availability", response_model=AvailabilityResponse)
async def update_availability(
    body: UpdateAvailabilityRequest,
    user: Annotated[dict, Depends(require_auth)],
    availability_service: Annotated[AvailabilityService, Depends(get_availability_service)],
):
    """Update user's weekly availability."""
    slots = [s.model_dump() for s in body.slots]

    result = await availability_service.update_availability(
        user_id=str(user["_id"]),
        slots=slots,
        user_timezone=body.timezone
    )

    return AvailabilityResponse(
        userId=str(result["userId"]),
        slots=[AvailabilitySlot(**s) for s in result["slots"]],
        timezone=result["timezone"]
    )


@router.get("/groups/{group_id}/availability", response_model=GroupAvailabilityResponse)
async def get_group_availability(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
    availability_service: Annotated[AvailabilityService, Depends(get_availability_service)],
):
    """Get availability status for a group."""
    result = await availability_service.get_group_availability_status(group_id)

    return GroupAvailabilityResponse(
        commonSlots=[AvailabilitySlot(**s) for s in result["commonSlots"]],
        totalMembers=result["totalMembers"],
        membersWithAvailability=result["membersWithAvailability"],
        membersWithoutAvailability=result["membersWithoutAvailability"],
        allMembersSet=result["allMembersSet"]
    )
