"""
Group message pipeline functions.

Orchestrates sending and listing messages within Think Tank groups,
including fan-out of notifications and emails to group members.
"""

import logging
from typing import Optional, Dict, Any

from bson import ObjectId

from common.utils.exceptions import ForbiddenException
from app_v2.services.circles.message_service import GroupMessageService
from app_v2.services.circles.group_service import GroupService
from app_v2.services.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def send_group_message(
    message_service: GroupMessageService,
    group_service: GroupService,
    notification_service: NotificationService,
    email_service,
    db,
    user_id: str,
    group_id: str,
    content: str,
) -> Dict[str, Any]:
    """
    Send a message to a Think Tank group.

    1. Validate the sender is a group member
    2. Find the sender's name from the group member list
    3. Save the message
    4. Notify other group members (in-app + email)
    5. Return the saved message
    """
    # 1. Validate membership
    has_access = await group_service.user_has_group_access(group_id, user_id)
    if not has_access:
        raise ForbiddenException(
            message="You are not a member of this group",
            code="NOT_GROUP_MEMBER",
        )

    # 2. Get group details and find sender name
    group = await group_service.get_group(group_id)
    members = group.get("members", [])
    group_name = group.get("name", "your Think Tank group")

    sender_name = "A group member"
    for member in members:
        if isinstance(member, dict) and ObjectId(user_id) == member.get("userId"):
            sender_name = member.get("name", sender_name)
            break

    # 3. Save message
    saved_message = await message_service.create_message(
        group_id=group_id,
        user_id=user_id,
        user_name=sender_name,
        content=content,
    )

    # 4. Fan out notifications and collect email recipients
    users_collection = db["users"] if db is not None else None
    email_recipients = []

    for member in members:
        if not isinstance(member, dict):
            continue
        member_user_id = member.get("userId")
        if not member_user_id or ObjectId(user_id) == member_user_id:
            continue

        member_id_str = str(member_user_id)

        # In-app notification
        try:
            await notification_service.create_notification(
                user_id=member_id_str,
                notification_type="group_message",
                title=f"{sender_name} in {group_name}",
                message=f"{sender_name} left a message in {group_name}.",
                metadata={
                    "groupId": group_id,
                    "messageId": saved_message["id"],
                },
            )
        except Exception as e:
            logger.warning(
                f"Failed to create notification for user {member_id_str}: {e}"
            )

        # Collect email recipient info
        try:
            if email_service and users_collection is not None:
                user_doc = await users_collection.find_one({"_id": member_user_id})
                if user_doc:
                    member_email = user_doc.get("email")
                    member_name = member.get("name")
                    if not member_name:
                        profile = user_doc.get("profile", {})
                        member_name = profile.get("firstName") or member_name
                    if member_email:
                        email_recipients.append({
                            "email": member_email,
                            "name": member_name,
                        })
        except Exception as e:
            logger.warning(
                f"Failed to look up email for user {member_id_str}: {e}"
            )

    # 5. Send email notifications in a single batch
    if email_service and email_recipients:
        try:
            await email_service.send_group_message_emails_batch(
                recipients=email_recipients,
                sender_name=sender_name,
                group_name=group_name,
                message_preview=content[:100],
            )
        except Exception as e:
            logger.warning(f"Failed to send batch email for group {group_id}: {e}")

    return saved_message


async def list_group_messages(
    message_service: GroupMessageService,
    group_service: GroupService,
    user_id: str,
    group_id: str,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List messages for a Think Tank group with pagination.

    1. Validate the requester is a group member
    2. Fetch messages and total count
    3. Return paginated result
    """
    # 1. Validate membership
    has_access = await group_service.user_has_group_access(group_id, user_id)
    if not has_access:
        raise ForbiddenException(
            message="You are not a member of this group",
            code="NOT_GROUP_MEMBER",
        )

    # 2. Fetch messages and count
    messages = await message_service.get_messages(
        group_id=group_id, limit=limit, offset=offset
    )
    total = await message_service.get_message_count(group_id)

    # 3. Return with pagination metadata
    return {
        "messages": messages,
        "total": total,
        "hasMore": (offset + limit) < total,
    }
