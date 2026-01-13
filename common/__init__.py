"""
Common library for reusable infrastructure components.

This package provides generic, SOLID-principle modules that can be used
across multiple projects:

- database: Async MongoDB connection with Beanie ODM
- auth: Pluggable authentication (JWT, Firebase)
- ai: Pluggable AI providers (Claude, OpenAI)
- i18n: Internationalization service
- utils: Standard responses, exceptions, password validation
- config: Base settings class
"""

from common.database import MongoDB, BaseDocument
from common.auth import AuthProvider, JWTAuth, FirebaseAuth, create_auth_dependency
from common.ai import AIProvider, ClaudeProvider, OpenAIProvider
from common.i18n import I18nService
from common.utils import (
    success_response,
    error_response,
    APIException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
    validate_password,
)
from common.config import BaseAppSettings

__all__ = [
    # Database
    "MongoDB",
    "BaseDocument",
    # Auth
    "AuthProvider",
    "JWTAuth",
    "FirebaseAuth",
    "create_auth_dependency",
    # AI
    "AIProvider",
    "ClaudeProvider",
    "OpenAIProvider",
    # i18n
    "I18nService",
    # Utils
    "success_response",
    "error_response",
    "APIException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "ValidationException",
    "validate_password",
    # Config
    "BaseAppSettings",
]
