"""
FastAPI router for Circles system endpoints.

Provides endpoints for groups, meetings, invitations, and availability.
"""

import os
import logging
from typing import Annotated, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import RedirectResponse

from app_v2.dependencies import (
    require_auth,
    optional_auth,
    get_pool_service,
    get_group_service,
    get_meeting_service,
    get_invitation_service,
    get_availability_service,
    get_main_db,
    get_notification_service,
)
from app_v2.pipelines.availability import get_group_availability_for_scheduling
from app_v2.schemas.circles import (
    UpdateAvailabilityRequest,
    ScheduleMeetingRequest,
    UpdateAttendanceRequest,
    SendInvitationsRequest,
    CreatePoolRequest,
    MoveMemberRequest,
    AddMemberRequest,
    CreateGroupRequest,
)
from app_v2.services.email.email_service import EmailService
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/circles", tags=["circles"])


@router.get("/my-groups")
async def get_my_groups(
    user: Annotated[dict, Depends(require_auth)],
):
    """Get current user's circle groups."""
    group_service = get_group_service()
    meeting_service = get_meeting_service()
    user_id = str(user["_id"])

    groups = await group_service.get_groups_for_user(user_id)

    formatted_groups = []
    user_oid = ObjectId(user_id)

    for g in groups:
        group_id = str(g["_id"])

        # Get upcoming meetings and find the first one where user is an attendee
        upcoming_meetings = await meeting_service.get_meetings_for_group(
            group_id=group_id, upcoming=True, limit=10
        )

        next_meeting_data = None
        for meeting in upcoming_meetings:
            attendees = meeting.get("attendees")

            # Backwards compat: if no attendees field, show to all members
            if attendees is None or user_oid in attendees:
                next_meeting_data = {
                    "id": str(meeting["_id"]),
                    "title": meeting.get("title", ""),
                    "scheduledAt": meeting.get("scheduledAt").isoformat() if meeting.get("scheduledAt") else None,
                    "duration": meeting.get("duration", 60),
                    "meetingLink": meeting.get("meetingLink"),
                    "timezone": meeting.get("timezone", "UTC"),
                }
                break  # Found the next meeting for this user

        raw_members = g.get("members", [])
        members_data = [
            {
                "id": str(m.get("userId")) if isinstance(m, dict) else str(m),
                "name": m.get("name", "Member") if isinstance(m, dict) else "Member",
                "avatar": None
            }
            for m in raw_members
        ]

        formatted_groups.append({
            "id": group_id,
            "name": g.get("name", ""),
            "memberCount": len(raw_members),
            "members": members_data,
            "nextMeeting": next_meeting_data,
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
        "pending": pending,
        "accepted": accepted,
    })


@router.get("/availability")
async def get_user_availability(
    user: Annotated[dict, Depends(require_auth)],
    groupId: str = None,
):
    """Get current user's availability slots for a specific group."""
    availability_service = get_availability_service()
    user_id = str(user["_id"])

    if not groupId:
        return success_response({"slots": [], "groupId": None})

    result = await availability_service.get_availability(user_id, groupId)

    slots = []
    if result:
        slots = result.get("slots", [])

    return success_response({"slots": slots, "groupId": groupId})


@router.put("/availability")
async def update_availability(
    body: UpdateAvailabilityRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Update user's weekly availability for a specific group."""
    availability_service = get_availability_service()
    user_id = str(user["_id"])
    group_id = body.groupId

    slots = [s.model_dump() for s in body.slots]
    await availability_service.update_availability(
        user_id=user_id,
        group_id=group_id,
        slots=slots,
        user_timezone="UTC"
    )

    return success_response({"groupId": group_id, "slots": slots})


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
    upcoming: bool = Query(default=False, description="Filter to upcoming meetings only"),
):
    """Get meetings for a group."""
    meeting_service = get_meeting_service()

    meetings = await meeting_service.get_meetings_for_group(
        group_id=group_id,
        upcoming=upcoming,
        limit=20
    )

    # Filter out meetings where current user has declined
    user_id = user["_id"]
    filtered_meetings = []
    for m in meetings:
        attendance = m.get("attendance", [])
        user_attendance = next(
            (a for a in attendance if a.get("userId") == user_id),
            None
        )
        # Include meeting if user hasn't declined
        if not user_attendance or user_attendance.get("status") != "declined":
            filtered_meetings.append(m)

    return success_response({
        "meetings": [
            {
                "id": str(m["_id"]),
                "title": m.get("title", ""),
                "scheduledAt": m.get("scheduledAt").isoformat() if m.get("scheduledAt") else None,
                "duration": m.get("duration", 60),
                "meetingLink": m.get("meetingLink"),
                "status": m.get("status", "scheduled"),
                "timezone": m.get("timezone", "UTC"),
            }
            for m in filtered_meetings
        ]
    })


@router.get("/groups/{group_id}/common-availability")
async def get_common_availability(
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Get availability slots for a group with member counts.

    Returns all slots where at least one member is available,
    with counts and names of who can attend each slot.
    """
    result = await get_group_availability_for_scheduling(group_id)

    return success_response(result)


@router.post("/groups/{group_id}/meetings")
async def schedule_meeting(
    group_id: str,
    body: ScheduleMeetingRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """Schedule a new meeting for the group."""
    meeting_service = get_meeting_service()
    group_service = get_group_service()
    db = get_main_db()

    # Pipeline Step 1: Book the meeting
    meeting = await meeting_service.schedule_meeting(
        group_id=group_id,
        scheduled_by=str(user["_id"]),
        title=body.title,
        topic=None,
        description=body.description,
        scheduled_at=body.scheduledAt,
        duration=body.duration,
        meeting_link=body.meetingLink,
        meeting_timezone=body.timezone or "UTC",
        available_members=body.availableMembers
    )

    # Pipeline Step 2: Send emails to all group members
    try:
        group = await group_service.get_group(group_id)
        members = group.get("members", [])
        users_collection = db["users"]
        email_service = EmailService()

        # Format meeting datetime for email
        scheduled_at = meeting.get("scheduledAt")
        if scheduled_at:
            meeting_datetime = scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p")
        else:
            meeting_datetime = "TBD"

        meeting_timezone = body.timezone or "UTC"
        meeting_link = body.meetingLink or ""
        discussion_title = body.title or "Think Tank Discussion"

        for member in members:
            # Handle both dict format and plain ObjectId
            if isinstance(member, dict):
                member_id = member.get("userId")
            else:
                member_id = member

            if not member_id:
                continue

            # Ensure ObjectId
            if not isinstance(member_id, ObjectId):
                try:
                    member_id = ObjectId(str(member_id))
                except Exception:
                    continue

            # Get member details
            member_doc = await users_collection.find_one({"_id": member_id})
            if not member_doc or not member_doc.get("email"):
                continue

            member_email = member_doc.get("email")
            profile = member_doc.get("profile", {})
            first_name = profile.get("firstName") or member_doc.get("firstName") or ""
            member_language = profile.get("preferredLanguage") or "en"

            # Send email
            try:
                await email_service.send_meeting_scheduled_email(
                    to_email=member_email,
                    user_name=first_name if first_name else None,
                    discussion_title=discussion_title,
                    meeting_datetime=meeting_datetime,
                    timezone=meeting_timezone,
                    meeting_link=meeting_link,
                    language=member_language,
                )
            except Exception as e:
                logger.warning(f"Failed to send meeting email to {member_email}: {e}")

    except Exception as e:
        logger.warning(f"Failed to send meeting emails: {e}")

    return success_response({
        "id": str(meeting["_id"]),
        "title": meeting.get("title", ""),
        "meetingLink": meeting.get("meetingLink"),
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

    await invitation_service.decline_invitation(token=token)

    return success_response({"message": "Invitation declined"})


# Frontend URL for redirects
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")


@router.get("/invitations/{token}/accept")
async def accept_invitation_redirect(
    token: str,
    user: Annotated[Optional[dict], Depends(optional_auth)],
):
    """
    Accept an invitation via email link (GET request).

    If user is authenticated: accepts invitation and redirects to /circles.
    If user is not authenticated: redirects to /login with inviteToken param.
    """
    if not user:
        # Not authenticated - redirect to login with token
        return RedirectResponse(
            url=f"{APP_URL}/login?inviteToken={token}",
            status_code=302
        )

    # User is authenticated - accept the invitation
    invitation_service = get_invitation_service()

    try:
        await invitation_service.accept_invitation(
            token=token,
            user_id=str(user["_id"])
        )
        # Success - redirect to circles page
        return RedirectResponse(url=f"{APP_URL}/circles", status_code=302)
    except Exception as e:
        logger.error(f"Failed to accept invitation: {e}")
        # Error - redirect to circles with error param
        return RedirectResponse(
            url=f"{APP_URL}/circles?inviteError=true",
            status_code=302
        )


@router.get("/invitations/{token}/decline")
async def decline_invitation_redirect(
    token: str,
    user: Annotated[Optional[dict], Depends(optional_auth)],
):
    """
    Decline an invitation via email link (GET request).

    If user is authenticated: declines invitation and redirects to /circles.
    If user is not authenticated: redirects to /login with declineToken param.
    """
    if not user:
        # Not authenticated - redirect to login with token
        return RedirectResponse(
            url=f"{APP_URL}/login?declineToken={token}",
            status_code=302
        )

    # User is authenticated - decline the invitation
    invitation_service = get_invitation_service()

    try:
        await invitation_service.decline_invitation(token=token)
        # Success - redirect to home/dashboard
        return RedirectResponse(url=f"{APP_URL}/dashboard", status_code=302)
    except Exception as e:
        logger.error(f"Failed to decline invitation: {e}")
        # Error - redirect to dashboard
        return RedirectResponse(url=f"{APP_URL}/dashboard", status_code=302)


@router.post("/meetings/{meeting_id}/cancel")
async def cancel_meeting(
    meeting_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Cancel a scheduled meeting."""
    meeting_service = get_meeting_service()

    await meeting_service.cancel_meeting(
        meeting_id=meeting_id,
        user_id=str(user["_id"])
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


# =============================================================================
# Admin Endpoints (Organization Admin only)
# =============================================================================

@router.post("/pools")
async def create_pool(
    body: CreatePoolRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Create a new circle pool.

    Only organization admins can create pools.
    """
    pool_service = get_pool_service()
    user_id = str(user["_id"])

    pool = await pool_service.create_pool(
        organization_id=body.organizationId,
        name=body.name,
        created_by=user_id,
        topic=body.topic,
        description=body.description,
        target_group_size=body.targetGroupSize,
        cadence=body.cadence,
    )

    return success_response({
        "id": str(pool["_id"]),
        "name": pool.get("name", ""),
        "status": pool.get("status", "draft"),
        "organizationId": str(pool.get("organizationId")),
        "stats": pool.get("stats", {}),
        "targetGroupSize": pool.get("targetGroupSize", 4),
        "cadence": pool.get("cadence", "biweekly"),
        "createdAt": pool.get("createdAt").isoformat() if pool.get("createdAt") else None,
    })


@router.get("/pools")
async def get_pools(
    user: Annotated[dict, Depends(require_auth)],
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Get pools for organization admin.

    Returns pools where the user is an organization admin.
    """
    db = get_main_db()
    user_id = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(str(user["_id"]))

    # Get group size constraints from env
    min_group_size = int(os.environ.get("MIN_GROUP_SIZE", "3"))
    max_group_size = int(os.environ.get("MAX_GROUP_SIZE", "6"))

    # Find organizations where user is admin
    org_members = db["organizationmembers"]
    admin_memberships = await org_members.find({
        "userId": user_id,
        "role": "admin",
        "status": "active"
    }).to_list(length=50)

    if not admin_memberships:
        return success_response({"pools": []})

    org_ids = [m["organizationId"] for m in admin_memberships]

    pool_service = get_pool_service()
    all_pools = []

    for org_id in org_ids:
        pools = await pool_service.get_pools_for_organization(
            organization_id=str(org_id),
            status=status
        )
        all_pools.extend(pools)

    formatted_pools = [
        {
            "id": str(p["_id"]),
            "name": p.get("name", ""),
            "status": p.get("status", "draft"),
            "organizationId": str(p.get("organizationId")),
            "stats": p.get("stats", {}),
            "targetGroupSize": p.get("targetGroupSize", 4),
            "minGroupSize": min_group_size,
            "maxGroupSize": max_group_size,
            "cadence": p.get("cadence", "biweekly"),
            "createdAt": p.get("createdAt").isoformat() if p.get("createdAt") else None,
        }
        for p in all_pools
    ]

    return success_response({"pools": formatted_pools})


@router.get("/pools/{pool_id}")
async def get_pool(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get pool details by ID."""
    pool_service = get_pool_service()

    pool = await pool_service.get_pool(pool_id)

    # Get group size constraints from env
    min_group_size = int(os.environ.get("MIN_GROUP_SIZE", "3"))
    max_group_size = int(os.environ.get("MAX_GROUP_SIZE", "6"))

    return success_response({
        "id": str(pool["_id"]),
        "name": pool.get("name", ""),
        "status": pool.get("status", "draft"),
        "topic": pool.get("topic"),
        "description": pool.get("description"),
        "organizationId": str(pool.get("organizationId")),
        "targetGroupSize": pool.get("targetGroupSize", 4),
        "minGroupSize": min_group_size,
        "maxGroupSize": max_group_size,
        "cadence": pool.get("cadence", "biweekly"),
        "stats": pool.get("stats", {}),
        "invitationSettings": pool.get("invitationSettings", {}),
        "createdAt": pool.get("createdAt").isoformat() if pool.get("createdAt") else None,
        "assignedAt": pool.get("assignedAt").isoformat() if pool.get("assignedAt") else None,
    })


@router.post("/pools/{pool_id}/invitations")
async def send_pool_invitations(
    pool_id: str,
    body: SendInvitationsRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Send invitations to pool.

    Only organization admins can send invitations.
    """
    invitation_service = get_invitation_service()
    user_id = str(user["_id"])

    # Convert InviteeItem to dict
    invitees = [inv.model_dump() for inv in body.invitees]

    result = await invitation_service.send_invitations(
        pool_id=pool_id,
        invitees=invitees,
        invited_by=user_id
    )

    return success_response({
        "sent": result.get("sent", []),
        "failed": result.get("failed", []),
        "duplicate": result.get("duplicate", [])
    })


@router.get("/pools/{pool_id}/invitations")
async def get_pool_invitations(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get all invitations for a pool."""
    invitation_service = get_invitation_service()

    invitations = await invitation_service.get_invitations_for_pool(
        pool_id=pool_id,
        status=status
    )

    formatted = []
    for inv in invitations:
        created_at = inv.get("createdAt")
        expires_at = inv.get("expiresAt")

        created_at_str = None
        if created_at:
            try:
                created_at_str = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
            except Exception:
                created_at_str = str(created_at)

        expires_at_str = None
        if expires_at:
            try:
                expires_at_str = expires_at.isoformat() if hasattr(expires_at, 'isoformat') else str(expires_at)
            except Exception:
                expires_at_str = str(expires_at)

        formatted.append({
            "id": str(inv["_id"]),
            "email": inv.get("email", ""),
            "firstName": inv.get("firstName"),
            "lastName": inv.get("lastName"),
            "status": inv.get("status", "pending"),
            "userId": str(inv["userId"]) if inv.get("userId") else None,
            "createdAt": created_at_str,
            "expiresAt": expires_at_str,
        })

    return success_response({"invitations": formatted})


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Cancel a pending invitation.

    Only organization admins can cancel invitations.
    """
    invitation_service = get_invitation_service()
    pool_service = get_pool_service()

    # Get invitation to find pool
    invitation = await invitation_service.get_invitation_by_id(invitation_id)
    pool = await pool_service.get_pool(str(invitation["poolId"]))

    # Verify user is org admin
    db = get_main_db()
    user_id = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(str(user["_id"]))
    org_members = db["organizationmembers"]
    is_admin = await org_members.find_one({
        "organizationId": pool["organizationId"],
        "userId": user_id,
        "role": "admin"
    })

    if not is_admin:
        raise HTTPException(status_code=403, detail={"message": "Not authorized"})

    await invitation_service.cancel_invitation(invitation_id)

    return success_response({"message": "Invitation cancelled"})


@router.post("/pools/{pool_id}/assign")
async def assign_pool_groups(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Assign accepted invitees to groups.

    Only organization admins can trigger assignment.
    """
    group_service = get_group_service()
    user_id = str(user["_id"])

    result = await group_service.assign_groups(
        pool_id=pool_id,
        user_id=user_id
    )

    groups = result.get("groups", [])
    formatted_groups = [
        {
            "id": str(g["_id"]),
            "name": g.get("name", ""),
            "memberCount": len(g.get("members", [])),
        }
        for g in groups
    ]

    return success_response({
        "groups": formatted_groups,
        "totalMembers": result.get("totalMembers", 0)
    })


@router.get("/pools/{pool_id}/groups")
async def get_pool_groups(
    pool_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get all groups for a pool."""
    group_service = get_group_service()
    db = get_main_db()

    groups = await group_service.get_groups_for_pool(pool_id)

    users_collection = db["users"]

    formatted_groups = []
    for g in groups:
        raw_members = g.get("members", [])
        members = []

        for m in raw_members:
            # Handle both dict format {"userId": ObjectId, "name": "..."} and plain ObjectId
            if isinstance(m, dict):
                user_id = m.get("userId")
                stored_name = m.get("name")
            else:
                user_id = m
                stored_name = None

            # Ensure user_id is ObjectId for queries
            if user_id and not isinstance(user_id, ObjectId):
                try:
                    user_id = ObjectId(str(user_id))
                except Exception:
                    user_id = None

            uid_str = str(user_id) if user_id else ""

            # Use stored name first (from assign_groups), fall back to users collection
            if stored_name and stored_name != "Member":
                name = stored_name
                avatar = None
            else:
                # Look up in users collection
                user_doc = await users_collection.find_one({"_id": user_id}) if user_id else None
                if user_doc:
                    profile = user_doc.get("profile", {})
                    # Try multiple name locations
                    first_name = profile.get("firstName") or user_doc.get("firstName") or ""
                    last_name = profile.get("lastName") or user_doc.get("lastName") or ""
                    full_name = f"{first_name} {last_name}".strip()
                    # Fall back chain: full name -> user.name -> email -> stored name -> "Member"
                    name = full_name or user_doc.get("name") or user_doc.get("email") or stored_name or "Member"
                    avatar = profile.get("avatar")
                else:
                    name = stored_name or "Member"
                    avatar = None

            members.append({
                "id": uid_str,
                "name": name,
                "avatar": avatar,
            })

        formatted_groups.append({
            "id": str(g["_id"]),
            "name": g.get("name", ""),
            "memberCount": len(raw_members),
            "members": members,
            "leaderId": str(g.get("leaderId")) if g.get("leaderId") else None,
        })

    return success_response({"groups": formatted_groups})


@router.post("/pools/{pool_id}/groups")
async def create_group(
    pool_id: str,
    body: CreateGroupRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Create a new empty group in a pool.

    Only organization admins can create groups.
    """
    group_service = get_group_service()
    user_id = str(user["_id"])

    group = await group_service.create_group(
        pool_id=pool_id,
        name=body.name,
        admin_id=user_id
    )

    return success_response({
        "id": str(group["_id"]),
        "name": group.get("name", ""),
        "memberCount": 0,
        "members": [],
    })


@router.post("/pools/{pool_id}/groups/{group_id}/move-member")
async def move_member(
    pool_id: str,
    group_id: str,
    body: MoveMemberRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Move a member from one group to another.

    Only organization admins can move members.

    Errors:
        - 400 GROUP_TOO_SMALL: Source group would have < 3 members
        - 400 GROUP_FULL: Target group already has 6 members
        - 403: Not authorized (not org admin)
        - 404: Group or member not found
    """
    group_service = get_group_service()
    pool_service = get_pool_service()
    notification_service = get_notification_service()
    db = get_main_db()

    user_id = str(user["_id"])

    # Get pool info for notification
    pool = await pool_service.get_pool(pool_id)
    pool_name = pool.get("name", "")

    # Get source and target groups for names
    from_group = await group_service.get_group(group_id)
    to_group = await group_service.get_group(body.toGroupId)

    from_group_name = from_group.get("name", "")
    to_group_name = to_group.get("name", "")

    # Perform the move (validates permissions and constraints)
    await group_service.move_member(
        member_id=body.memberId,
        from_group_id=group_id,
        to_group_id=body.toGroupId,
        admin_id=user_id
    )

    # Get updated group info
    updated_from_group = await group_service.get_group(group_id)
    updated_to_group = await group_service.get_group(body.toGroupId)

    # Get member info for response and notification
    users_collection = db["users"]
    member_doc = await users_collection.find_one({"_id": ObjectId(body.memberId)})

    member_name = "Member"
    member_email = None
    member_language = "en"
    if member_doc:
        profile = member_doc.get("profile", {})
        first_name = profile.get("firstName", "")
        last_name = profile.get("lastName", "")
        member_name = f"{first_name} {last_name}".strip() or member_doc.get("email", "Member")
        member_email = member_doc.get("email")
        member_language = profile.get("preferredLanguage") or "en"

    # Create notification for the moved member
    try:
        await notification_service.create_user_moved_notification(
            user_id=body.memberId,
            from_group_name=from_group_name,
            to_group_name=to_group_name,
            pool_id=pool_id,
            from_group_id=group_id,
            to_group_id=body.toGroupId
        )
    except Exception as e:
        logger.warning(f"Failed to create move notification: {e}")

    # Send email notification
    if member_email:
        try:
            email_service = EmailService()
            await email_service.send_member_moved_email(
                to_email=member_email,
                user_name=member_name.split()[0] if member_name else None,
                from_group_name=from_group_name,
                to_group_name=to_group_name,
                pool_name=pool_name,
                language=member_language,
            )
        except Exception as e:
            logger.warning(f"Failed to send move email: {e}")

    return success_response({
        "message": "Member moved successfully",
        "fromGroup": {
            "id": group_id,
            "name": from_group_name,
            "memberCount": len(updated_from_group.get("members", []))
        },
        "toGroup": {
            "id": body.toGroupId,
            "name": to_group_name,
            "memberCount": len(updated_to_group.get("members", []))
        },
        "movedMember": {
            "id": body.memberId,
            "name": member_name
        }
    })


@router.post("/pools/{pool_id}/groups/{group_id}/add-member")
async def add_member_to_group(
    pool_id: str,
    group_id: str,
    body: AddMemberRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Add a latecomer to an existing group.

    Only organization admins can add members.
    The user must have an accepted invitation for this pool.
    """
    group_service = get_group_service()
    pool_service = get_pool_service()
    db = get_main_db()

    user_id = str(user["_id"])

    # Verify admin and get pool info
    pool = await pool_service.get_pool(pool_id)

    # Add member to group
    await group_service.add_member(
        group_id=group_id,
        user_id=body.userId,
        admin_id=user_id
    )

    # Get updated group
    updated_group = await group_service.get_group(group_id)

    # Get member info
    users_collection = db["users"]
    member_doc = await users_collection.find_one({"_id": ObjectId(body.userId)})

    member_name = "Member"
    if member_doc:
        profile = member_doc.get("profile", {})
        first_name = profile.get("firstName", "")
        last_name = profile.get("lastName", "")
        member_name = f"{first_name} {last_name}".strip() or member_doc.get("email", "Member")

    return success_response({
        "message": "Member added successfully",
        "group": {
            "id": group_id,
            "name": updated_group.get("name", ""),
            "memberCount": len(updated_group.get("members", []))
        },
        "addedMember": {
            "id": body.userId,
            "name": member_name
        }
    })


@router.post("/pools/{pool_id}/groups/{group_id}/remove-member")
async def remove_member_from_group(
    pool_id: str,
    group_id: str,
    body: AddMemberRequest,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Remove a member from a group and the pool entirely.

    Only organization admins can remove members.
    This deletes the user's invitation, as if they were never invited.
    """
    group_service = get_group_service()
    db = get_main_db()

    user_id = str(user["_id"])

    # Get member info before removal
    users_collection = db["users"]
    member_doc = await users_collection.find_one({"_id": ObjectId(body.userId)})

    member_name = "Member"
    if member_doc:
        profile = member_doc.get("profile", {})
        first_name = profile.get("firstName", "")
        last_name = profile.get("lastName", "")
        member_name = f"{first_name} {last_name}".strip() or member_doc.get("email", "Member")

    # Remove member from group and delete invitation
    updated_group = await group_service.remove_member(
        group_id=group_id,
        user_id=body.userId,
        admin_id=user_id
    )

    return success_response({
        "message": "Member removed successfully",
        "group": {
            "id": group_id,
            "name": updated_group.get("name", ""),
            "memberCount": len(updated_group.get("members", []))
        },
        "removedMember": {
            "id": body.userId,
            "name": member_name
        }
    })


@router.post("/pools/{pool_id}/groups/{group_id}/delete")
async def delete_group(
    pool_id: str,
    group_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """
    Delete a circle group.

    Only organization admins can delete groups.
    The group must belong to the specified pool.

    Returns:
        - 200: Group deleted successfully
        - 403: Not authorized (not org admin)
        - 404: Group or pool not found
    """
    group_service = get_group_service()
    pool_service = get_pool_service()
    db = get_main_db()

    user_id = str(user["_id"])

    # Verify pool exists
    pool = await pool_service.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Get the group to verify it exists and belongs to this pool
    group = await group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Verify group belongs to this pool
    group_pool_id = str(group.get("poolId"))
    if group_pool_id != pool_id:
        raise HTTPException(status_code=400, detail="Group does not belong to this pool")

    # Get group name for response before deletion
    group_name = group.get("name", "Group")
    member_count = len(group.get("members", []))

    # Delete the group from circlegroups collection
    groups_collection = db["circlegroups"]
    result = await groups_collection.delete_one({"_id": ObjectId(group_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Failed to delete group")

    logger.info(f"Group {group_id} ({group_name}) deleted by user {user_id}")

    return success_response({
        "message": "Group deleted successfully",
        "deletedGroup": {
            "id": group_id,
            "name": group_name,
            "memberCount": member_count
        }
    })
