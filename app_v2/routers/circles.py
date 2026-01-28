"""
FastAPI router for Circles system endpoints.

Provides endpoints for groups, meetings, invitations, and availability.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app_v2.dependencies import (
    require_auth,
    get_pool_service,
    get_group_service,
    get_meeting_service,
    get_invitation_service,
    get_availability_service,
)
from app_v2.schemas.circles import (
    UpdateAvailabilityRequest,
    ScheduleMeetingRequest,
    UpdateAttendanceRequest,
    SendInvitationsRequest,
    CreatePoolRequest,
    MoveMemberRequest,
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
    meeting_service = get_meeting_service()
    user_id = str(user["_id"])

    groups = await group_service.get_groups_for_user(user_id)

    formatted_groups = []
    for g in groups:
        group_id = str(g["_id"])
        next_meeting = await meeting_service.get_next_meeting(group_id)

        next_meeting_data = None
        if next_meeting:
            next_meeting_data = {
                "id": str(next_meeting["_id"]),
                "title": next_meeting.get("title", ""),
                "scheduledAt": next_meeting.get("scheduledAt").isoformat() if next_meeting.get("scheduledAt") else None,
                "duration": next_meeting.get("duration", 60),
                "meetingLink": next_meeting.get("meetingLink"),
                "timezone": next_meeting.get("timezone", "UTC"),
            }

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

    slots = result.get("commonSlots", [])

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
        meeting_link=body.meetingLink,
        meeting_timezone=body.timezone or "UTC"
    )

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

    await invitation_service.decline_invitation(token=token)

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
    from bson import ObjectId
    from app_v2.dependencies import get_main_db

    db = get_main_db()
    user_id = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(str(user["_id"]))

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

    return success_response({
        "id": str(pool["_id"]),
        "name": pool.get("name", ""),
        "status": pool.get("status", "draft"),
        "topic": pool.get("topic"),
        "description": pool.get("description"),
        "organizationId": str(pool.get("organizationId")),
        "targetGroupSize": pool.get("targetGroupSize", 4),
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
    from bson import ObjectId
    from app_v2.dependencies import get_main_db

    db = get_main_db()
    user_id = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(str(user["_id"]))
    org_members = db["organizationmembers"]
    is_admin = await org_members.find_one({
        "organizationId": pool["organizationId"],
        "userId": user_id,
        "role": "admin"
    })

    if not is_admin:
        from fastapi import HTTPException
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
    from app_v2.dependencies import get_main_db

    group_service = get_group_service()
    db = get_main_db()

    groups = await group_service.get_groups_for_pool(pool_id)

    # Get user info for members
    users_collection = db["users"]

    formatted_groups = []
    for g in groups:
        member_ids = g.get("members", [])

        # Get member details
        members = []
        if member_ids:
            member_docs = await users_collection.find({
                "_id": {"$in": member_ids}
            }).to_list(length=50)

            member_map = {str(m["_id"]): m for m in member_docs}

            for mid in member_ids:
                member = member_map.get(str(mid), {})
                profile = member.get("profile", {})
                first_name = profile.get("firstName", "")
                last_name = profile.get("lastName", "")
                name = f"{first_name} {last_name}".strip() or member.get("email", "Member")

                members.append({
                    "id": str(mid),
                    "name": name,
                    "avatar": profile.get("avatar"),
                })

        formatted_groups.append({
            "id": str(g["_id"]),
            "name": g.get("name", ""),
            "memberCount": len(member_ids),
            "members": members,
            "leaderId": str(g.get("leaderId")) if g.get("leaderId") else None,
        })

    return success_response({"groups": formatted_groups})


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
    from bson import ObjectId
    from app_v2.dependencies import get_main_db, get_notification_service

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
    if member_doc:
        profile = member_doc.get("profile", {})
        first_name = profile.get("firstName", "")
        last_name = profile.get("lastName", "")
        member_name = f"{first_name} {last_name}".strip() or member_doc.get("email", "Member")
        member_email = member_doc.get("email")

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
            from app_v2.services.email.email_service import EmailService
            email_service = EmailService()
            await email_service.send_member_moved_email(
                to_email=member_email,
                user_name=member_name.split()[0] if member_name else None,
                from_group_name=from_group_name,
                to_group_name=to_group_name,
                pool_name=pool_name
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
    from bson import ObjectId
    from app_v2.dependencies import get_main_db

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
