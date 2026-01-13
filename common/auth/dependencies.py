"""
FastAPI authentication dependencies.

Provides factory functions to create auth dependencies that can be
injected into route handlers. Works with any AuthProvider implementation.

Example:
    from common.auth import JWTAuth, create_auth_dependency

    auth = JWTAuth(secret="your-secret")
    get_current_user_id = create_auth_dependency(lambda: auth)

    @app.get("/profile")
    async def get_profile(user_id: str = Depends(get_current_user_id)):
        return {"user_id": user_id}
"""

from typing import Callable, Optional
from fastapi import Header, HTTPException

from common.auth.base import AuthProvider


def create_auth_dependency(
    get_auth_provider: Callable[[], AuthProvider],
    header_name: str = "Authorization",
    scheme: str = "Bearer",
):
    """
    Factory to create FastAPI auth dependencies.

    Args:
        get_auth_provider: Callable that returns the AuthProvider instance
        header_name: Header to extract token from (default: Authorization)
        scheme: Auth scheme prefix (default: Bearer)

    Returns:
        A FastAPI dependency function that extracts and verifies the user ID
    """

    async def get_current_user_id(
        authorization: Optional[str] = Header(None, alias=header_name),
    ) -> str:
        """
        Extract and verify user ID from the authorization header.

        Raises:
            HTTPException 401: If token is missing, invalid, or expired
        """
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail={"message": "Missing authorization header", "code": "UNAUTHORIZED"},
            )

        # Extract token from header
        prefix = f"{scheme} "
        if not authorization.startswith(prefix):
            raise HTTPException(
                status_code=401,
                detail={
                    "message": f"Invalid authorization scheme. Expected: {scheme}",
                    "code": "INVALID_AUTH_SCHEME",
                },
            )

        token = authorization[len(prefix) :]

        if not token:
            raise HTTPException(
                status_code=401,
                detail={"message": "Token is empty", "code": "EMPTY_TOKEN"},
            )

        # Verify token
        auth = get_auth_provider()
        try:
            payload = await auth.verify_token(token)
            user_id = payload.get("sub") or payload.get("uid")

            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail={"message": "Token missing user ID", "code": "INVALID_TOKEN"},
                )

            return user_id

        except ValueError as e:
            raise HTTPException(
                status_code=401,
                detail={"message": str(e), "code": "INVALID_TOKEN"},
            )

    return get_current_user_id


def create_optional_auth_dependency(
    get_auth_provider: Callable[[], AuthProvider],
    header_name: str = "Authorization",
    scheme: str = "Bearer",
):
    """
    Factory to create optional auth dependency.

    Unlike create_auth_dependency, this returns None instead of raising
    an exception when no token is provided. Useful for endpoints that
    work for both authenticated and anonymous users.

    Returns:
        A FastAPI dependency that returns user_id or None
    """

    async def get_optional_user_id(
        authorization: Optional[str] = Header(None, alias=header_name),
    ) -> Optional[str]:
        """
        Extract and verify user ID, returning None if not authenticated.
        """
        if not authorization:
            return None

        prefix = f"{scheme} "
        if not authorization.startswith(prefix):
            return None

        token = authorization[len(prefix) :]
        if not token:
            return None

        auth = get_auth_provider()
        try:
            payload = await auth.verify_token(token)
            return payload.get("sub") or payload.get("uid")
        except ValueError:
            return None

    return get_optional_user_id


def create_admin_dependency(
    get_auth_provider: Callable[[], AuthProvider],
    is_admin_check: Callable[[str], bool],
    header_name: str = "Authorization",
    scheme: str = "Bearer",
):
    """
    Factory to create admin-only auth dependency.

    Verifies both authentication and admin status.

    Args:
        get_auth_provider: Callable that returns the AuthProvider instance
        is_admin_check: Callable that checks if user_id is an admin
        header_name: Header to extract token from
        scheme: Auth scheme prefix

    Returns:
        A FastAPI dependency that returns user_id for admin users only
    """

    # First get the regular auth dependency
    get_current_user_id = create_auth_dependency(
        get_auth_provider,
        header_name,
        scheme,
    )

    async def get_admin_user_id(
        authorization: Optional[str] = Header(None, alias=header_name),
    ) -> str:
        """
        Verify user is authenticated and is an admin.

        Raises:
            HTTPException 401: If not authenticated
            HTTPException 403: If not an admin
        """
        # First verify authentication
        user_id = await get_current_user_id(authorization)

        # Then check admin status
        if not is_admin_check(user_id):
            raise HTTPException(
                status_code=403,
                detail={"message": "Admin access required", "code": "FORBIDDEN"},
            )

        return user_id

    return get_admin_user_id
