"""
Auth System

Handles identity verification and access control through Firebase authentication
and session management embedded in User documents.
"""

from app_v2.auth.services.token_hasher import TokenHasher
from app_v2.auth.services.device_detector import DeviceDetector
from app_v2.auth.services.geo_ip_service import GeoIPService
from app_v2.auth.services.session_manager import SessionManager
from app_v2.auth.middleware import AuthMiddleware

__all__ = [
    "TokenHasher",
    "DeviceDetector",
    "GeoIPService",
    "SessionManager",
    "AuthMiddleware",
]
