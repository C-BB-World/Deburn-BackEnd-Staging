"""
Authentication module - Pluggable auth providers (JWT, Firebase).
"""

from common.auth.base import AuthProvider
from common.auth.jwt_auth import JWTAuth
from common.auth.firebase_auth import FirebaseAuth
from common.auth.dependencies import create_auth_dependency

__all__ = ["AuthProvider", "JWTAuth", "FirebaseAuth", "create_auth_dependency"]
