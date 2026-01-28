"""
Pydantic models for Auth system request/response validation.

Matches the API documentation in docs/v2/architecture/api/auth.md
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


# =============================================================================
# Request Schemas
# =============================================================================

class ConsentsInput(BaseModel):
    """Consent input at registration."""
    termsOfService: bool
    privacyPolicy: bool
    dataProcessing: bool
    marketing: bool = False  # Optional


class LoginRequest(BaseModel):
    """POST /api/auth/login"""
    email: EmailStr
    password: str
    rememberMe: bool = False


class RegisterRequest(BaseModel):
    """POST /api/auth/register"""
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    passwordConfirm: str
    organization: str
    country: str  # ISO 3166-1 alpha-2
    consents: ConsentsInput


class ForgotPasswordRequest(BaseModel):
    """POST /api/auth/forgot-password"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """POST /api/auth/reset-password"""
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    """POST /api/auth/verify-email"""
    token: str


class ResendVerificationRequest(BaseModel):
    """POST /api/auth/resend-verification"""
    email: EmailStr


class DeleteAccountRequest(BaseModel):
    """POST /api/auth/delete-account"""
    reason: Optional[str] = None


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class UserResponse(BaseModel):
    """User object in responses."""
    id: str
    email: str
    firstName: str
    lastName: str
    isAdmin: bool = False
