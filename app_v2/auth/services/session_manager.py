"""
Session management for user authentication.

Manages session lifecycle within the User document's embedded sessions array.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.auth.services.token_hasher import TokenHasher
from app_v2.auth.services.device_detector import DeviceDetector
from app_v2.auth.services.geo_ip_service import GeoIPService

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Handles session CRUD operations.
    Sessions are stored as embedded array in user document.
    """

    # Session expiration times
    DEFAULT_EXPIRATION_DAYS = 7
    REMEMBER_ME_EXPIRATION_DAYS = 30

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        device_detector: DeviceDetector,
        geo_service: GeoIPService
    ):
        """
        Initialize SessionManager.

        Args:
            db: MongoDB database connection
            device_detector: Service for parsing User-Agent
            geo_service: Service for IP-to-location lookup
        """
        self._db = db
        self._device_detector = device_detector
        self._geo_service = geo_service
        self._users_collection = db["users"]

    async def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False
    ) -> Tuple[str, datetime]:
        """
        Create a new session for a user.

        Args:
            user_id: MongoDB user ID
            ip_address: Client IP address
            user_agent: Client User-Agent header
            remember_me: If True, session expires in 30 days; else 7 days

        Returns:
            tuple of (session_token, expires_at)

        Side Effects:
            - Generates secure random token
            - Hashes token for storage (SHA-256)
            - Detects device type from user_agent
            - Looks up location from IP
            - Pushes session object to user.sessions[] array
        """
        token = TokenHasher.generate_token()
        token_hash = TokenHasher.hash_token(token)

        device_info = self._device_detector.detect(user_agent)
        location_info = self._geo_service.lookup(ip_address)

        expiration_days = (
            self.REMEMBER_ME_EXPIRATION_DAYS if remember_me
            else self.DEFAULT_EXPIRATION_DAYS
        )
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expiration_days)

        session = {
            "_id": ObjectId(),
            "tokenHash": token_hash,
            "device": device_info,
            "location": location_info,
            "ipAddress": ip_address,
            "createdAt": now,
            "expiresAt": expires_at,
            "lastActiveAt": now
        }

        await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"sessions": session}}
        )

        logger.info(f"Session created for user {user_id}")
        return token, expires_at

    async def validate_session(
        self,
        token_hash: str
    ) -> Optional[Tuple[dict, dict]]:
        """
        Find user and session by token hash.

        Args:
            token_hash: SHA-256 hash of session token

        Returns:
            tuple of (user_dict, session_dict) if valid, None if not found or expired
        """
        now = datetime.now(timezone.utc)

        user = await self._users_collection.find_one({
            "sessions": {
                "$elemMatch": {
                    "tokenHash": token_hash,
                    "expiresAt": {"$gt": now}
                }
            }
        })

        if not user:
            return None

        session = None
        for s in user.get("sessions", []):
            if s.get("tokenHash") == token_hash:
                session = s
                break

        if not session:
            return None

        return user, session

    async def update_last_active(
        self,
        user_id: str,
        token_hash: str
    ) -> None:
        """
        Update the lastActiveAt timestamp for a session.

        Args:
            user_id: MongoDB user ID
            token_hash: Hash of the session token to update
        """
        now = datetime.now(timezone.utc)

        await self._users_collection.update_one(
            {
                "_id": ObjectId(user_id),
                "sessions.tokenHash": token_hash
            },
            {
                "$set": {"sessions.$.lastActiveAt": now}
            }
        )

    async def get_user_sessions(self, user_id: str) -> list[dict]:
        """
        Get all active (non-expired) sessions for a user.

        Args:
            user_id: MongoDB user ID

        Returns:
            List of session dicts from user.sessions[], filtered for non-expired
        """
        now = datetime.now(timezone.utc)

        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"sessions": 1}
        )

        if not user:
            return []

        sessions = user.get("sessions", [])
        active_sessions = [
            s for s in sessions
            if s.get("expiresAt") and s["expiresAt"] > now
        ]

        return active_sessions

    async def revoke_session(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Remove a specific session from user.sessions[].

        Args:
            user_id: MongoDB user ID
            session_id: ID of session to remove

        Returns:
            True if removed, False if not found
        """
        result = await self._users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"sessions": {"_id": ObjectId(session_id)}}}
        )

        if result.modified_count > 0:
            logger.info(f"Session {session_id} revoked for user {user_id}")
            return True

        return False

    async def revoke_all_sessions(
        self,
        user_id: str,
        except_token_hash: Optional[str] = None
    ) -> int:
        """
        Remove all sessions from user.sessions[].

        Args:
            user_id: MongoDB user ID
            except_token_hash: Optional token hash to keep (current session)

        Returns:
            Number of sessions removed
        """
        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"sessions": 1}
        )

        if not user:
            return 0

        sessions = user.get("sessions", [])
        original_count = len(sessions)

        if except_token_hash:
            sessions_to_keep = [
                s for s in sessions
                if s.get("tokenHash") == except_token_hash
            ]
            await self._users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"sessions": sessions_to_keep}}
            )
            removed_count = original_count - len(sessions_to_keep)
        else:
            await self._users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"sessions": []}}
            )
            removed_count = original_count

        logger.info(f"Revoked {removed_count} sessions for user {user_id}")
        return removed_count

    async def cleanup_expired_sessions(self, user_id: str) -> int:
        """
        Remove expired sessions from user.sessions[] array.

        Args:
            user_id: MongoDB user ID

        Returns:
            Number of sessions removed
        """
        now = datetime.now(timezone.utc)

        user = await self._users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"sessions": 1}
        )

        if not user:
            return 0

        sessions = user.get("sessions", [])
        original_count = len(sessions)

        active_sessions = [
            s for s in sessions
            if s.get("expiresAt") and s["expiresAt"] > now
        ]

        if len(active_sessions) < original_count:
            await self._users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"sessions": active_sessions}}
            )

        removed_count = original_count - len(active_sessions)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired sessions for user {user_id}")

        return removed_count
