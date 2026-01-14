"""
FastAPI dependencies for Auth system.

Provides dependency injection for auth-related services and middleware.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.auth.firebase_auth import FirebaseAuth
from app_v2.auth.services.device_detector import DeviceDetector
from app_v2.auth.services.geo_ip_service import GeoIPService
from app_v2.auth.services.session_manager import SessionManager
from app_v2.auth.middleware import AuthMiddleware


@lru_cache()
def get_device_detector() -> DeviceDetector:
    """Get cached DeviceDetector instance."""
    return DeviceDetector()


@lru_cache()
def get_geo_ip_service() -> GeoIPService:
    """Get cached GeoIPService instance."""
    return GeoIPService()


_firebase_auth: FirebaseAuth | None = None
_session_manager: SessionManager | None = None
_auth_middleware: AuthMiddleware | None = None


def init_auth_services(
    db: AsyncIOMotorDatabase,
    firebase_credentials_path: str | None = None,
    firebase_credentials_dict: dict | None = None,
    geoip_database_path: str | None = None
) -> None:
    """
    Initialize auth services with database and credentials.

    Called once at application startup.

    Args:
        db: MongoDB database connection
        firebase_credentials_path: Path to Firebase service account JSON
        firebase_credentials_dict: Firebase credentials as dict (alternative)
        geoip_database_path: Path to GeoIP database file
    """
    global _firebase_auth, _session_manager, _auth_middleware

    _firebase_auth = FirebaseAuth(
        credentials_path=firebase_credentials_path,
        credentials_dict=firebase_credentials_dict
    )

    device_detector = get_device_detector()
    geo_service = GeoIPService(database_path=geoip_database_path)

    _session_manager = SessionManager(
        db=db,
        device_detector=device_detector,
        geo_service=geo_service
    )

    _auth_middleware = AuthMiddleware(session_manager=_session_manager)


def get_firebase_auth() -> FirebaseAuth:
    """Get Firebase auth client."""
    if _firebase_auth is None:
        raise RuntimeError("Auth services not initialized. Call init_auth_services first.")
    return _firebase_auth


def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    if _session_manager is None:
        raise RuntimeError("Auth services not initialized. Call init_auth_services first.")
    return _session_manager


def get_auth_middleware() -> AuthMiddleware:
    """Get auth middleware instance."""
    if _auth_middleware is None:
        raise RuntimeError("Auth services not initialized. Call init_auth_services first.")
    return _auth_middleware


async def require_auth(
    request: Request,
    auth_middleware: Annotated[AuthMiddleware, Depends(get_auth_middleware)]
) -> dict:
    """
    Dependency that requires authentication.

    Usage:
        @router.get("/protected")
        async def protected_route(user: Annotated[dict, Depends(require_auth)]):
            return {"user_id": str(user["_id"])}
    """
    return await auth_middleware.require_auth(request)


async def optional_auth(
    request: Request,
    auth_middleware: Annotated[AuthMiddleware, Depends(get_auth_middleware)]
) -> dict | None:
    """
    Dependency that optionally authenticates.

    Usage:
        @router.get("/public")
        async def public_route(user: Annotated[dict | None, Depends(optional_auth)]):
            if user:
                return {"logged_in": True}
            return {"logged_in": False}
    """
    return await auth_middleware.optional_auth(request)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "0.0.0.0"


def get_user_agent(request: Request) -> str:
    """Extract User-Agent from request."""
    return request.headers.get("User-Agent", "")
