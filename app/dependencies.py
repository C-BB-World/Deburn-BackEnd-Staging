"""
FastAPI Dependencies.

Provides dependency injection for authentication, AI providers, and other services.
"""

from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from common.auth import AuthProvider, JWTAuth, FirebaseAuth
from common.ai import AIProvider, ClaudeProvider, OpenAIProvider

from app.config import settings
from app.models import User
from app.services.coach_service import CoachService


# =============================================================================
# Auth Provider Dependencies
# =============================================================================
@lru_cache()
def get_auth_provider() -> AuthProvider:
    """
    Get the configured authentication provider.

    Returns JWTAuth or FirebaseAuth based on settings.AUTH_PROVIDER.
    """
    if settings.AUTH_PROVIDER == "firebase":
        if not settings.FIREBASE_CREDENTIALS_PATH:
            raise ValueError("FIREBASE_CREDENTIALS_PATH is required for Firebase auth")
        return FirebaseAuth(credentials_path=settings.FIREBASE_CREDENTIALS_PATH)

    # Default to JWT
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is required for JWT auth")

    return JWTAuth(
        secret_key=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
        access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )


# =============================================================================
# AI Provider Dependencies
# =============================================================================
@lru_cache()
def get_ai_provider() -> AIProvider:
    """
    Get the configured AI provider.

    Returns ClaudeProvider or OpenAIProvider based on settings.AI_PROVIDER.
    """
    if settings.AI_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )

    # Default to Claude
    if not settings.CLAUDE_API_KEY:
        raise ValueError("CLAUDE_API_KEY is required for Claude")

    return ClaudeProvider(
        api_key=settings.CLAUDE_API_KEY,
        model=settings.CLAUDE_MODEL,
    )


# =============================================================================
# User Authentication Dependencies
# =============================================================================
async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    auth: AuthProvider = Depends(get_auth_provider),
) -> User:
    """
    Get the current authenticated user from the Authorization header.

    Raises:
        HTTPException: If token is missing, invalid, or user not found.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authorization header is required",
                },
            },
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid authorization header format",
                },
            },
        )

    token = authorization.replace("Bearer ", "")

    try:
        payload = await auth.verify_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": str(e),
                },
            },
        )

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Token missing user ID",
                },
            },
        )

    user = await User.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                },
            },
        )

    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "ACCOUNT_INACTIVE",
                    "message": "Account is not active",
                },
            },
        )

    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    auth: AuthProvider = Depends(get_auth_provider),
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.

    Use this for endpoints that work with or without authentication.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        return await get_current_user(authorization, auth)
    except HTTPException:
        return None


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    Require the current user to be an admin.

    Raises:
        HTTPException: If user is not an admin.
    """
    # Check if user has admin flag or is in org admin role
    # This is a simplified check - in production you'd check OrganizationMember
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Admin access required",
                },
            },
        )

    return user


# =============================================================================
# Service Dependencies
# =============================================================================
def get_coach_service(
    ai: AIProvider = Depends(get_ai_provider),
) -> CoachService:
    """
    Get the coach service instance.

    Injects the AI provider for flexibility.
    """
    # Import i18n from api module to avoid circular imports
    from api import i18n

    return CoachService(
        ai_provider=ai,
        i18n=i18n,
        prompts_dir="app/prompts",
    )
