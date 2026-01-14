"""
Auth system pipeline functions.

Stateless orchestration logic for authentication flows.
"""

import logging
from typing import TYPE_CHECKING

from common.auth.firebase_auth import FirebaseAuth
from common.utils.exceptions import (
    UnauthorizedException,
    NotFoundException,
    ConflictException,
    ForbiddenException,
)
from app_v2.auth.services.session_manager import SessionManager

if TYPE_CHECKING:
    from app_v2.user.services.user_service import UserService

logger = logging.getLogger(__name__)


async def registration_pipeline(
    firebase_auth: FirebaseAuth,
    user_service: "UserService",
    session_manager: SessionManager,
    firebase_token: str,
    profile: dict,
    consents: list[dict],
    organization: str,
    country: str,
    ip_address: str,
    user_agent: str
) -> dict:
    """
    Orchestrates the user registration flow.

    Args:
        firebase_auth: Firebase authentication client
        user_service: User service for creating user record
        session_manager: For creating session
        firebase_token: Firebase ID token from frontend
        profile: Initial profile data
        consents: List of consents accepted at registration
        organization: User's organization name
        country: User's country code (ISO 3166-1 alpha-2)
        ip_address: Client IP address
        user_agent: Client User-Agent header

    Returns:
        dict with user, sessionToken, and expiresAt

    Raises:
        UnauthorizedException: Firebase token invalid
        ConflictException: Firebase UID already linked to existing user
        BadRequestException: Invalid profile or missing consents
    """
    try:
        firebase_claims = await firebase_auth.verify_token(firebase_token)
    except ValueError as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise UnauthorizedException(
            message="Invalid Firebase token",
            code="INVALID_FIREBASE_TOKEN"
        )

    firebase_uid = firebase_claims.get("uid")
    email = firebase_claims.get("email")

    if not firebase_uid or not email:
        raise UnauthorizedException(
            message="Invalid Firebase token claims",
            code="INVALID_TOKEN_CLAIMS"
        )

    existing_user = await user_service.get_user_by_firebase_uid(firebase_uid)
    if existing_user:
        raise ConflictException(
            message="User already registered",
            code="USER_ALREADY_EXISTS"
        )

    user = await user_service.create_user(
        firebase_uid=firebase_uid,
        email=email,
        organization=organization,
        country=country,
        profile=profile,
        consents=consents
    )

    session_token, expires_at = await session_manager.create_session(
        user_id=str(user["_id"]),
        ip_address=ip_address,
        user_agent=user_agent,
        remember_me=False
    )

    logger.info(f"User registered: {user['_id']}")

    return {
        "user": _format_user_response(user),
        "sessionToken": session_token,
        "expiresAt": expires_at
    }


async def login_pipeline(
    firebase_auth: FirebaseAuth,
    user_service: "UserService",
    session_manager: SessionManager,
    firebase_token: str,
    remember_me: bool,
    ip_address: str,
    user_agent: str
) -> dict:
    """
    Orchestrates the user login flow.

    Args:
        firebase_auth: Firebase authentication client
        user_service: User service for user lookup
        session_manager: For creating session
        firebase_token: Firebase ID token from frontend
        remember_me: If True, session expires in 30 days
        ip_address: Client IP address
        user_agent: Client User-Agent header

    Returns:
        dict with user, sessionToken, and expiresAt

    Raises:
        UnauthorizedException: Firebase token invalid
        NotFoundException: User not found in MongoDB
        ForbiddenException: User is suspended
    """
    try:
        firebase_claims = await firebase_auth.verify_token(firebase_token)
    except ValueError as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise UnauthorizedException(
            message="Invalid Firebase token",
            code="INVALID_FIREBASE_TOKEN"
        )

    firebase_uid = firebase_claims.get("uid")

    if not firebase_uid:
        raise UnauthorizedException(
            message="Invalid Firebase token claims",
            code="INVALID_TOKEN_CLAIMS"
        )

    user = await user_service.get_user_by_firebase_uid(firebase_uid)

    if not user:
        raise NotFoundException(
            message="User not found. Please register first.",
            code="USER_NOT_FOUND"
        )

    user_status = user.get("status")

    if user_status == "suspended":
        raise ForbiddenException(
            message="Account suspended",
            code="ACCOUNT_SUSPENDED"
        )

    if user_status == "pendingDeletion":
        await user_service.cancel_deletion(str(user["_id"]))
        user["status"] = "active"
        logger.info(f"Deletion cancelled for user {user['_id']} on login")

    session_token, expires_at = await session_manager.create_session(
        user_id=str(user["_id"]),
        ip_address=ip_address,
        user_agent=user_agent,
        remember_me=remember_me
    )

    await user_service.update_last_login(str(user["_id"]))

    logger.info(f"User logged in: {user['_id']}")

    return {
        "user": _format_user_response(user),
        "sessionToken": session_token,
        "expiresAt": expires_at
    }


async def logout_pipeline(
    session_manager: SessionManager,
    user_id: str,
    token_hash: str
) -> dict:
    """
    Orchestrates the logout flow.

    Args:
        session_manager: For session revocation
        user_id: MongoDB user ID
        token_hash: Hash of current session token

    Returns:
        dict with success message
    """
    await session_manager.revoke_all_sessions(
        user_id=user_id,
        except_token_hash=None
    )

    for session in await session_manager.get_user_sessions(user_id):
        if session.get("tokenHash") == token_hash:
            await session_manager.revoke_session(user_id, str(session["_id"]))
            break

    logger.info(f"User logged out: {user_id}")

    return {"message": "Logged out successfully"}


async def get_sessions_pipeline(
    session_manager: SessionManager,
    user_id: str,
    current_token_hash: str
) -> list[dict]:
    """
    Get all active sessions for a user.

    Args:
        session_manager: For session retrieval
        user_id: MongoDB user ID
        current_token_hash: Hash of current session token (to mark as current)

    Returns:
        List of session dicts with isCurrent flag
    """
    sessions = await session_manager.get_user_sessions(user_id)

    result = []
    for session in sessions:
        session_data = {
            "id": str(session["_id"]),
            "device": session.get("device", {}),
            "location": session.get("location"),
            "createdAt": session.get("createdAt"),
            "lastActiveAt": session.get("lastActiveAt"),
            "isCurrent": session.get("tokenHash") == current_token_hash
        }
        result.append(session_data)

    return result


async def revoke_session_pipeline(
    session_manager: SessionManager,
    user_id: str,
    session_id: str,
    current_token_hash: str
) -> dict:
    """
    Revoke a specific session.

    Args:
        session_manager: For session revocation
        user_id: MongoDB user ID
        session_id: ID of session to revoke
        current_token_hash: Hash of current session token

    Returns:
        dict with success message

    Raises:
        BadRequestException: Trying to revoke current session
        NotFoundException: Session not found
    """
    from common.utils.exceptions import BadRequestException

    sessions = await session_manager.get_user_sessions(user_id)

    target_session = None
    for session in sessions:
        if str(session["_id"]) == session_id:
            target_session = session
            break

    if not target_session:
        raise NotFoundException(
            message="Session not found",
            code="SESSION_NOT_FOUND"
        )

    if target_session.get("tokenHash") == current_token_hash:
        raise BadRequestException(
            message="Cannot revoke current session. Use logout instead.",
            code="CANNOT_REVOKE_CURRENT"
        )

    success = await session_manager.revoke_session(user_id, session_id)

    if not success:
        raise NotFoundException(
            message="Session not found",
            code="SESSION_NOT_FOUND"
        )

    logger.info(f"Session {session_id} revoked for user {user_id}")

    return {"message": "Session revoked successfully"}


async def revoke_all_sessions_pipeline(
    session_manager: SessionManager,
    user_id: str,
    current_token_hash: str,
    except_current: bool = True
) -> dict:
    """
    Revoke all sessions for a user.

    Args:
        session_manager: For session revocation
        user_id: MongoDB user ID
        current_token_hash: Hash of current session token
        except_current: If True, keep current session

    Returns:
        dict with revoked count and message
    """
    revoked_count = await session_manager.revoke_all_sessions(
        user_id=user_id,
        except_token_hash=current_token_hash if except_current else None
    )

    logger.info(f"Revoked {revoked_count} sessions for user {user_id}")

    return {
        "revokedCount": revoked_count,
        "message": "Sessions revoked successfully"
    }


def _format_user_response(user: dict) -> dict:
    """Format user document for API response."""
    return {
        "id": str(user["_id"]),
        "email": user.get("email"),
        "status": user.get("status"),
        "profile": user.get("profile", {}),
        "organization": user.get("organization"),
        "country": user.get("country"),
        "createdAt": user.get("createdAt"),
        "lastLoginAt": user.get("lastLoginAt")
    }
