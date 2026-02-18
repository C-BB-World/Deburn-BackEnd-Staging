"""
Calendar connection management service.

Handles OAuth connections, token storage, and webhook management.
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.services.calendar.google_calendar_service import GoogleCalendarService
from app_v2.services.calendar.token_encryption import TokenEncryptionService
from common.utils.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class CalendarConnectionService:
    """
    Manages calendar connections and OAuth tokens.
    """

    WEBHOOK_EXPIRY_DAYS = 7
    WEBHOOK_RENEWAL_THRESHOLD_DAYS = 2

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        google_calendar: GoogleCalendarService,
        token_encryption: TokenEncryptionService
    ):
        """
        Initialize CalendarConnectionService.

        Args:
            db: MongoDB database connection
            google_calendar: Google Calendar API client
            token_encryption: Token encryption service
        """
        self._db = db
        self._google_calendar = google_calendar
        self._token_encryption = token_encryption
        self._connections_collection = db["calendarConnections"]

    def get_auth_url(self, user_id: str, return_url: Optional[str] = None) -> str:
        """
        Get Google OAuth authorization URL.

        Args:
            user_id: User's ID to include in state
            return_url: URL to redirect to after connection

        Returns:
            Authorization URL
        """
        state = f"{user_id}"
        if return_url:
            state = f"{user_id}|{return_url}"

        return self._google_calendar.get_auth_url(state=state)

    async def handle_oauth_callback(
        self,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and store connection.

        Args:
            code: Authorization code from Google
            state: State parameter containing user ID

        Returns:
            Created/updated connection
        """
        parts = state.split("|")
        user_id = parts[0]
        return_url = parts[1] if len(parts) > 1 else None

        tokens = await self._google_calendar.exchange_code(code)

        user_info = await self._google_calendar.get_user_info(tokens["accessToken"])

        calendars = await self._google_calendar.list_calendars(tokens["accessToken"])
        primary_calendar = next(
            (c["id"] for c in calendars if c.get("primary")),
            calendars[0]["id"] if calendars else None
        )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=tokens["expiresIn"])

        encrypted_access = self._token_encryption.encrypt(tokens["accessToken"])
        encrypted_refresh = self._token_encryption.encrypt(tokens["refreshToken"]) if tokens.get("refreshToken") else None

        connection_doc = {
            "userId": ObjectId(user_id),
            "provider": "google",
            "accessTokenEncrypted": encrypted_access,
            "refreshTokenEncrypted": encrypted_refresh,
            "expiresAt": expires_at,
            "scopes": self._google_calendar.SCOPES,
            "calendarIds": [c["id"] for c in calendars],
            "primaryCalendarId": primary_calendar,
            "providerEmail": user_info.get("email"),
            "status": "active",
            "lastError": None,
            "webhook": None,
            "syncToken": None,
            "connectedAt": now,
            "lastSyncAt": now,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self._connections_collection.find_one_and_update(
            {"userId": ObjectId(user_id), "provider": "google"},
            {"$set": {
                **{k: v for k, v in connection_doc.items() if k not in ("createdAt", "connectedAt")},
            }, "$setOnInsert": {
                "createdAt": now,
                "connectedAt": now,
            }},
            upsert=True,
            return_document=True
        )

        if primary_calendar:
            try:
                await self._setup_webhook(result, tokens["accessToken"])
            except Exception as e:
                logger.warning(f"Failed to setup webhook for user {user_id}: {e}")

        logger.info(f"Calendar connected for user {user_id}: {user_info.get('email')}")

        return {
            "connection": result,
            "returnUrl": return_url,
        }

    async def get_connection(
        self,
        user_id: str,
        provider: str = "google"
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's calendar connection.

        Args:
            user_id: User's ID
            provider: Calendar provider

        Returns:
            Connection document or None
        """
        return await self._connections_collection.find_one({
            "userId": ObjectId(user_id),
            "provider": provider,
            "status": {"$in": ["active", "expired"]},
        })

    async def get_valid_access_token(
        self,
        user_id: str,
        provider: str = "google"
    ) -> Optional[str]:
        """
        Get a valid access token, refreshing if needed.

        Args:
            user_id: User's ID
            provider: Calendar provider

        Returns:
            Valid access token or None
        """
        connection = await self.get_connection(user_id, provider)
        if not connection:
            return None

        now = datetime.now(timezone.utc)

        if connection["expiresAt"] > now + timedelta(minutes=5):
            return self._token_encryption.decrypt(connection["accessTokenEncrypted"])

        if not connection.get("refreshTokenEncrypted"):
            await self._mark_connection_error(connection["_id"], "No refresh token")
            return None

        try:
            refresh_token = self._token_encryption.decrypt(connection["refreshTokenEncrypted"])
            new_tokens = await self._google_calendar.refresh_token(refresh_token)

            encrypted_access = self._token_encryption.encrypt(new_tokens["accessToken"])
            expires_at = now + timedelta(seconds=new_tokens["expiresIn"])

            await self._connections_collection.update_one(
                {"_id": connection["_id"]},
                {"$set": {
                    "accessTokenEncrypted": encrypted_access,
                    "expiresAt": expires_at,
                    "status": "active",
                    "lastError": None,
                    "updatedAt": now,
                }}
            )

            logger.info(f"Refreshed token for user {user_id}")
            return new_tokens["accessToken"]

        except Exception as e:
            logger.error(f"Token refresh failed for user {user_id}: {e}")
            await self._mark_connection_error(connection["_id"], str(e))
            return None

    async def disconnect(
        self,
        user_id: str,
        provider: str = "google"
    ) -> bool:
        """
        Disconnect calendar and revoke tokens.

        Args:
            user_id: User's ID
            provider: Calendar provider

        Returns:
            True if disconnected
        """
        connection = await self._connections_collection.find_one({
            "userId": ObjectId(user_id),
            "provider": provider,
        })

        if not connection:
            return False

        if connection.get("webhook"):
            try:
                await self._google_calendar.stop_webhook(
                    connection["webhook"]["channelId"],
                    connection["webhook"]["resourceId"]
                )
            except Exception as e:
                logger.warning(f"Failed to stop webhook: {e}")

        try:
            access_token = self._token_encryption.decrypt(connection["accessTokenEncrypted"])
            if access_token:
                await self._google_calendar.revoke_token(access_token)
        except Exception as e:
            logger.warning(f"Failed to revoke token: {e}")

        now = datetime.now(timezone.utc)
        await self._connections_collection.update_one(
            {"_id": connection["_id"]},
            {"$set": {
                "status": "revoked",
                "accessTokenEncrypted": None,
                "refreshTokenEncrypted": None,
                "webhook": None,
                "updatedAt": now,
            }}
        )

        logger.info(f"Calendar disconnected for user {user_id}")
        return True

    async def get_connections_needing_webhook_renewal(self) -> List[Dict[str, Any]]:
        """
        Find connections with webhooks expiring soon.

        Returns:
            List of connections needing renewal
        """
        threshold = datetime.now(timezone.utc) + timedelta(days=self.WEBHOOK_RENEWAL_THRESHOLD_DAYS)

        return await self._connections_collection.find({
            "status": "active",
            "webhook.expiration": {"$lt": threshold},
        }).to_list(length=100)

    async def renew_webhook(self, connection_id: str) -> bool:
        """
        Renew webhook for a connection.

        Args:
            connection_id: Connection ID

        Returns:
            True if renewed
        """
        connection = await self._connections_collection.find_one({"_id": ObjectId(connection_id)})
        if not connection:
            return False

        access_token = await self.get_valid_access_token(
            str(connection["userId"]),
            connection["provider"]
        )
        if not access_token:
            return False

        if connection.get("webhook"):
            try:
                await self._google_calendar.stop_webhook(
                    connection["webhook"]["channelId"],
                    connection["webhook"]["resourceId"]
                )
            except Exception:
                pass

        return await self._setup_webhook(connection, access_token)

    async def _setup_webhook(
        self,
        connection: Dict[str, Any],
        access_token: str
    ) -> bool:
        """Setup webhook for calendar changes."""
        if not connection.get("primaryCalendarId"):
            return False

        channel_id = self._google_calendar.generate_channel_id()
        channel_token = self._google_calendar.generate_channel_token()
        expiration = datetime.now(timezone.utc) + timedelta(days=self.WEBHOOK_EXPIRY_DAYS)

        try:
            result = await self._google_calendar.setup_webhook(
                access_token=access_token,
                calendar_id=connection["primaryCalendarId"],
                channel_id=channel_id,
                token=channel_token,
                expiration=expiration
            )

            await self._connections_collection.update_one(
                {"_id": connection["_id"]},
                {"$set": {
                    "webhook": {
                        "channelId": channel_id,
                        "resourceId": result["resourceId"],
                        "token": channel_token,
                        "expiration": result["expiration"],
                    },
                    "updatedAt": datetime.now(timezone.utc),
                }}
            )

            return True

        except Exception as e:
            logger.error(f"Webhook setup failed: {e}")
            return False

    async def _mark_connection_error(self, connection_id: ObjectId, error: str) -> None:
        """Mark a connection as having an error."""
        await self._connections_collection.update_one(
            {"_id": connection_id},
            {"$set": {
                "status": "error",
                "lastError": error,
                "updatedAt": datetime.now(timezone.utc),
            }}
        )

    async def handle_webhook(
        self,
        channel_id: str,
        resource_id: str,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle incoming webhook notification.

        Args:
            channel_id: Channel ID from header
            resource_id: Resource ID from header
            token: Verification token from header

        Returns:
            Connection if valid, None otherwise
        """
        connection = await self._connections_collection.find_one({
            "webhook.channelId": channel_id,
            "webhook.resourceId": resource_id,
            "webhook.token": token,
        })

        if not connection:
            logger.warning(f"Webhook validation failed for channel {channel_id}")
            return None

        return connection
