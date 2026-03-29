"""
Authentication middleware for protected routes.

Validates session tokens and attaches user context to requests.
"""

import logging
from typing import Optional

from fastapi import Request

from common.utils.exceptions import UnauthorizedException, ForbiddenException
from app_v2.services.auth.session_manager import SessionManager
from app_v2.services.auth.token_hasher import TokenHasher

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    Middleware that validates session and attaches user to request.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize AuthMiddleware.

        Args:
            session_manager: For session validation
        """
        self._session_manager = session_manager

    async def require_auth(self, request: Request) -> dict:
        """
        Validate request is authenticated.

        Args:
            request: HTTP request object

        Returns:
            User dict attached to request

        Raises:
            UnauthorizedError: No header, invalid session, or expired
            ForbiddenError: User is suspended

        Side Effects:
            - Extracts token from Authorization header
            - Updates session.lastActiveAt
            - Attaches user to request.state.user
            - Attaches current session to request.state.session
        """
        token = self._extract_token(request)

        if not token:
            raise UnauthorizedException(
                message="Authentication required",
                code="AUTH_REQUIRED"
            )

        token_hash = TokenHasher.hash_token(token)
        result = await self._session_manager.validate_session(token_hash)

        if not result:
            raise UnauthorizedException(
                message="Invalid or expired session",
                code="INVALID_SESSION"
            )

        user, session = result

        user_status = user.get("status")
        if user_status == "suspended":
            raise ForbiddenException(
                message="Account suspended",
                code="ACCOUNT_SUSPENDED"
            )

        await self._session_manager.update_last_active(
            str(user["_id"]),
            token_hash
        )

        request.state.user = user
        request.state.session = session
        request.state.token_hash = token_hash

        return user

    async def optional_auth(self, request: Request) -> Optional[dict]:
        """
        Attach user if authenticated, but don't require it.

        Args:
            request: HTTP request object

        Returns:
            User dict if authenticated, None otherwise

        Does not raise errors for missing/invalid auth.
        """
        token = self._extract_token(request)

        if not token:
            return None

        try:
            token_hash = TokenHasher.hash_token(token)
            result = await self._session_manager.validate_session(token_hash)

            if not result:
                return None

            user, session = result

            if user.get("status") == "suspended":
                return None

            await self._session_manager.update_last_active(
                str(user["_id"]),
                token_hash
            )

            request.state.user = user
            request.state.session = session
            request.state.token_hash = token_hash

            return user

        except Exception as e:
            logger.debug(f"Optional auth failed: {e}")
            return None

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract bearer token from Authorization header.

        Args:
            request: HTTP request object

        Returns:
            Token string if present and valid format, None otherwise

        Expected format: "Authorization: Bearer <token>"
        """
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        parts = auth_header.split()

        if len(parts) != 2:
            return None

        scheme, token = parts

        if scheme.lower() != "bearer":
            return None

        return token
