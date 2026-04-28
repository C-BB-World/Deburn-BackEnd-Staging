"""
Notification API endpoints.

Handles in-app notification retrieval and management.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from common.utils import success_response

from app_v2.dependencies import require_auth, get_notification_service
from app_v2.services.notifications import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


# =============================================================================
# Notification Endpoints
# =============================================================================

@router.get("")
async def get_notifications(
    user: Annotated[dict, Depends(require_auth)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False)
):
    """
    Get notifications for the current user.

    Args:
        limit: Maximum number of notifications (1-100, default 20)
        offset: Number to skip for pagination
        unread_only: If true, only return unread notifications

    Returns:
        List of notifications with pagination info
    """
    service = get_notification_service()
    user_id = user.get("user_id")

    result = await service.get_notifications(
        user_id=user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only
    )

    return success_response(result)


@router.get("/count")
async def get_unread_count(
    user: Annotated[dict, Depends(require_auth)]
):
    """
    Get count of unread notifications.

    Returns:
        Object with unread count
    """
    service = get_notification_service()
    user_id = user.get("user_id")

    count = await service.get_unread_count(user_id)

    return success_response({"unread": count})


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user: Annotated[dict, Depends(require_auth)]
):
    """
    Mark a notification as read.

    Args:
        notification_id: ID of the notification to mark as read

    Returns:
        Success message
    """
    service = get_notification_service()
    user_id = user.get("user_id")

    await service.mark_as_read(notification_id, user_id)

    return success_response({"message": "Notification marked as read"})


@router.post("/read-all")
async def mark_all_as_read(
    user: Annotated[dict, Depends(require_auth)]
):
    """
    Mark all notifications as read.

    Returns:
        Number of notifications marked as read
    """
    service = get_notification_service()
    user_id = user.get("user_id")

    count = await service.mark_all_as_read(user_id)

    return success_response({
        "message": f"Marked {count} notifications as read",
        "count": count
    })
