"""
Authentication request/response schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    organization: str = Field(min_length=2, max_length=100)
    country: str = Field(pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2 country code")
    firstName: Optional[str] = Field(None, max_length=50)
    lastName: Optional[str] = Field(None, max_length=50)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str
    rememberMe: bool = False


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    token: str
    password: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""

    email: EmailStr


class UserProfileResponse(BaseModel):
    """User profile in response."""

    firstName: Optional[str] = None
    lastName: Optional[str] = None
    jobTitle: Optional[str] = None
    leadershipLevel: Optional[str] = None
    preferredLanguage: str = "en"
    timezone: Optional[str] = None


class UserResponse(BaseModel):
    """User data in response."""

    id: str
    email: str
    organization: str
    country: str
    profile: UserProfileResponse
    displayName: Optional[str] = None
    status: str
    createdAt: Optional[datetime] = None


class LoginResponse(BaseModel):
    """Login response data."""

    user: UserResponse
    accessToken: str
