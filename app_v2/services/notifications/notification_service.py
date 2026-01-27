"""
Notification service for in-app notifications.

Handles creation, retrieval, and management of user notifications.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Handles in-app notification management.

    Notification types:
    - invitation: User receives a circle invitation
    - group_assignment: User is assigned to a circle group
    - meeting_scheduled: A meeting is scheduled for the user's group
    - meeting_reminder: Reminder for upcoming meeting
    - user_moved: User was moved to a different group
    """

    NOTIFICATION_TYPES = [
        "invitation",
        "group_assignment",
        "meeting_scheduled",
        "meeting_reminder",
        "user_moved"
    ]

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize NotificationService.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._collection = db["notifications"]

    async def create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new notification for a user.

        Args:
            user_id: Target user ID
            notification_type: One of NOTIFICATION_TYPES
            title: Short notification title
            message: Full notification message
            metadata: Optional metadata (poolId, groupId, meetingId, etc.)

        Returns:
            Created notification document
        """
        now = datetime.now(timezone.utc)

        notification_doc = {
            "userId": ObjectId(user_id),
            "type": notification_type,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "read": False,
            "readAt": None,
            "createdAt": now,
            "updatedAt": now
        }

        result = await self._collection.insert_one(notification_doc)
        notification_doc["_id"] = result.inserted_id

        logger.info(f"Created notification for user {user_id}: {notification_type}")
        return notification_doc

    async def get_notifications(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False
    ) -> Dict[str, Any]:
        """
        Get notifications for a user with pagination.

        Args:
            user_id: User ID
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip
            unread_only: If True, only return unread notifications

        Returns:
            Dict with notifications list, total count, and hasMore flag
        """
        query = {"userId": ObjectId(user_id)}
        if unread_only:
            query["read"] = False

        # Get total count
        total = await self._collection.count_documents(query)

        # Get notifications with sorting and pagination
        cursor = self._collection.find(query).sort(
            "createdAt", -1
        ).skip(offset).limit(limit)

        notifications = await cursor.to_list(length=limit)

        # Format notifications for response
        formatted = []
        for notif in notifications:
            formatted.append({
                "id": str(notif["_id"]),
                "type": notif["type"],
                "title": notif["title"],
                "message": notif["message"],
                "metadata": notif.get("metadata", {}),
                "read": notif["read"],
                "readAt": notif["readAt"].isoformat() if notif.get("readAt") else None,
                "createdAt": notif["createdAt"].isoformat() if notif.get("createdAt") else None
            })

        has_more = (offset + len(notifications)) < total

        return {
            "notifications": formatted,
            "total": total,
            "hasMore": has_more
        }

    async def get_unread_count(self, user_id: str) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user_id: User ID

        Returns:
            Number of unread notifications
        """
        count = await self._collection.count_documents({
            "userId": ObjectId(user_id),
            "read": False
        })
        return count

    async def mark_as_read(self, notification_id: str, user_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for ownership verification)

        Returns:
            Updated notification document

        Raises:
            NotFoundException: If notification not found or doesn't belong to user
        """
        notification = await self._collection.find_one({
            "_id": ObjectId(notification_id),
            "userId": ObjectId(user_id)
        })

        if not notification:
            raise NotFoundException(
                message="Notification not found",
                code="NOTIFICATION_NOT_FOUND"
            )

        if notification["read"]:
            # Already read, return as-is
            return notification

        now = datetime.now(timezone.utc)
        await self._collection.update_one(
            {"_id": ObjectId(notification_id)},
            {
                "$set": {
                    "read": True,
                    "readAt": now,
                    "updatedAt": now
                }
            }
        )

        notification["read"] = True
        notification["readAt"] = now
        notification["updatedAt"] = now

        logger.info(f"Notification {notification_id} marked as read for user {user_id}")
        return notification

    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all unread notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        now = datetime.now(timezone.utc)
        result = await self._collection.update_many(
            {
                "userId": ObjectId(user_id),
                "read": False
            },
            {
                "$set": {
                    "read": True,
                    "readAt": now,
                    "updatedAt": now
                }
            }
        )

        logger.info(f"Marked {result.modified_count} notifications as read for user {user_id}")
        return result.modified_count

    async def create_group_assignment_notification(
        self,
        user_id: str,
        group_name: str,
        pool_name: str,
        pool_id: str,
        group_id: str
    ) -> Dict[str, Any]:
        """
        Create a notification for group assignment.

        Args:
            user_id: User being assigned
            group_name: Name of the assigned group
            pool_name: Name of the pool
            pool_id: Pool ID
            group_id: Group ID

        Returns:
            Created notification
        """
        return await self.create_notification(
            user_id=user_id,
            notification_type="group_assignment",
            title=f"Assigned to {group_name}",
            message=f"You have been assigned to {group_name} in the {pool_name} pool.",
            metadata={
                "poolId": pool_id,
                "groupId": group_id
            }
        )

    async def create_user_moved_notification(
        self,
        user_id: str,
        from_group_name: str,
        to_group_name: str,
        pool_id: str,
        from_group_id: str,
        to_group_id: str
    ) -> Dict[str, Any]:
        """
        Create a notification for user being moved between groups.

        Args:
            user_id: User being moved
            from_group_name: Source group name
            to_group_name: Target group name
            pool_id: Pool ID
            from_group_id: Source group ID
            to_group_id: Target group ID

        Returns:
            Created notification
        """
        return await self.create_notification(
            user_id=user_id,
            notification_type="user_moved",
            title=f"Moved to {to_group_name}",
            message=f"You have been moved from {from_group_name} to {to_group_name}.",
            metadata={
                "poolId": pool_id,
                "fromGroupId": from_group_id,
                "toGroupId": to_group_id
            }
        )

    async def create_meeting_scheduled_notification(
        self,
        user_id: str,
        group_name: str,
        meeting_title: str,
        scheduled_at: datetime,
        group_id: str,
        meeting_id: str
    ) -> Dict[str, Any]:
        """
        Create a notification for a scheduled meeting.

        Args:
            user_id: User to notify
            group_name: Name of the group
            meeting_title: Meeting title
            scheduled_at: When the meeting is scheduled
            group_id: Group ID
            meeting_id: Meeting ID

        Returns:
            Created notification
        """
        return await self.create_notification(
            user_id=user_id,
            notification_type="meeting_scheduled",
            title="Meeting Scheduled",
            message=f"{meeting_title} for {group_name} scheduled for {scheduled_at.strftime('%B %d at %I:%M %p')}.",
            metadata={
                "groupId": group_id,
                "meetingId": meeting_id,
                "scheduledAt": scheduled_at.isoformat()
            }
        )

    async def create_meeting_reminder_notification(
        self,
        user_id: str,
        group_name: str,
        meeting_title: str,
        scheduled_at: datetime,
        group_id: str,
        meeting_id: str,
        reminder_type: str = "24h"
    ) -> Dict[str, Any]:
        """
        Create a meeting reminder notification.

        Args:
            user_id: User to notify
            group_name: Name of the group
            meeting_title: Meeting title
            scheduled_at: When the meeting is scheduled
            group_id: Group ID
            meeting_id: Meeting ID
            reminder_type: "24h" or "1h"

        Returns:
            Created notification
        """
        time_text = "in 24 hours" if reminder_type == "24h" else "in 1 hour"

        return await self.create_notification(
            user_id=user_id,
            notification_type="meeting_reminder",
            title=f"Meeting {time_text.title()}",
            message=f"Reminder: {meeting_title} for {group_name} starts {time_text}.",
            metadata={
                "groupId": group_id,
                "meetingId": meeting_id,
                "scheduledAt": scheduled_at.isoformat(),
                "reminderType": reminder_type
            }
        )

    async def create_invitation_notification(
        self,
        user_id: str,
        pool_name: str,
        pool_id: str,
        invitation_token: str
    ) -> Dict[str, Any]:
        """
        Create a notification for accepting an invitation.

        Args:
            user_id: User who accepted
            pool_name: Name of the pool
            pool_id: Pool ID
            invitation_token: Invitation token

        Returns:
            Created notification
        """
        return await self.create_notification(
            user_id=user_id,
            notification_type="invitation",
            title="Invitation Accepted",
            message=f"You joined the {pool_name} pool. You'll be assigned to a group soon.",
            metadata={
                "poolId": pool_id,
                "invitationToken": invitation_token
            }
        )
