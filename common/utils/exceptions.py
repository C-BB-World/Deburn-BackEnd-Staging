"""
Custom HTTP exceptions with error codes.

Extends FastAPI's HTTPException with standardized error codes
for consistent API error responses.

Example:
    from common.utils import NotFoundException, ValidationException

    @app.get("/users/{id}")
    async def get_user(id: str):
        user = await User.find_one({"_id": id})
        if not user:
            raise NotFoundException("User not found", code="USER_NOT_FOUND")
        return user
"""

from typing import Optional, Any, Dict
from fastapi import HTTPException


class APIException(HTTPException):
    """
    Base API exception with error code support.

    Provides consistent error response format across the API.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        code: Optional[str] = None,
        details: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Create an API exception.

        Args:
            status_code: HTTP status code
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            headers: Optional response headers
        """
        detail: Dict[str, Any] = {"message": message}

        if code:
            detail["code"] = code

        if details is not None:
            detail["details"] = details

        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )


class BadRequestException(APIException):
    """400 Bad Request - Invalid input or malformed request."""

    def __init__(
        self,
        message: str = "Bad request",
        code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ):
        super().__init__(400, message, code, details)


class UnauthorizedException(APIException):
    """401 Unauthorized - Missing or invalid authentication."""

    def __init__(
        self,
        message: str = "Unauthorized",
        code: str = "UNAUTHORIZED",
        details: Optional[Any] = None,
    ):
        super().__init__(401, message, code, details)


class ForbiddenException(APIException):
    """403 Forbidden - Valid auth but insufficient permissions."""

    def __init__(
        self,
        message: str = "Forbidden",
        code: str = "FORBIDDEN",
        details: Optional[Any] = None,
    ):
        super().__init__(403, message, code, details)


class NotFoundException(APIException):
    """404 Not Found - Resource doesn't exist."""

    def __init__(
        self,
        message: str = "Not found",
        code: str = "NOT_FOUND",
        details: Optional[Any] = None,
    ):
        super().__init__(404, message, code, details)


class ConflictException(APIException):
    """409 Conflict - Resource already exists or state conflict."""

    def __init__(
        self,
        message: str = "Conflict",
        code: str = "CONFLICT",
        details: Optional[Any] = None,
    ):
        super().__init__(409, message, code, details)


class ValidationException(APIException):
    """422 Validation Error - Request validation failed."""

    def __init__(
        self,
        message: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        details: Optional[Any] = None,
        errors: Optional[list] = None,
    ):
        detail_info = details
        if errors:
            detail_info = {"errors": errors, **(details or {})}
        super().__init__(422, message, code, detail_info)


class RateLimitException(APIException):
    """429 Too Many Requests - Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None,
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=429,
            message=message,
            code=code,
            details={"retryAfter": retry_after} if retry_after else None,
            headers=headers if headers else None,
        )


class InternalServerException(APIException):
    """500 Internal Server Error - Unexpected server error."""

    def __init__(
        self,
        message: str = "Internal server error",
        code: str = "INTERNAL_ERROR",
        details: Optional[Any] = None,
    ):
        super().__init__(500, message, code, details)


# Alias for InternalServerException
ServerException = InternalServerException


class ServiceUnavailableException(APIException):
    """503 Service Unavailable - Service temporarily unavailable."""

    def __init__(
        self,
        message: str = "Service unavailable",
        code: str = "SERVICE_UNAVAILABLE",
        retry_after: Optional[int] = None,
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=503,
            message=message,
            code=code,
            details={"retryAfter": retry_after} if retry_after else None,
            headers=headers if headers else None,
        )
