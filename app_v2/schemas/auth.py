"""
Pydantic models for Auth system request/response validation.

Defines schemas for registration, login, sessions, and related operations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class DeviceSchema(BaseModel):
    """Device information for a session."""
    deviceType: str = Field(..., description="mobile | tablet | desktop")
    os: str = Field(..., description="iOS | Android | Windows | macOS | Linux")
    browser: str = Field(..., description="Chrome | Safari | Firefox | Edge | etc.")
    displayName: str = Field(..., description="Human-readable device description")


class LocationSchema(BaseModel):
    """Geographic location for a session."""
    city: Optional[str] = None
    country: str
    countryCode: str = Field(..., description="ISO 3166-1 alpha-2")


class ConsentInput(BaseModel):
    """Consent input at registration."""
    type: str = Field(..., description="Consent type (e.g., termsOfService)")
    accepted: bool
    version: str


class ProfileInput(BaseModel):
    """Profile input at registration."""
    firstName: str = Field(..., min_length=1, max_length=50)
    lastName: Optional[str] = Field(None, max_length=50)
    jobTitle: Optional[str] = Field(None, max_length=100)
    leadershipLevel: Optional[str] = Field(
        None,
        description="individual_contributor | team_lead | manager | director | executive"
    )
    timezone: str = Field(default="UTC", description="IANA timezone")
    preferredLanguage: str = Field(default="en", description="en | sv")


class RegisterRequest(BaseModel):
    """Request body for user registration."""
    firebaseToken: str = Field(..., description="Firebase ID token from frontend")
    profile: ProfileInput
    consents: List[ConsentInput]
    organization: str = Field(..., min_length=1)
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")


class LoginRequest(BaseModel):
    """Request body for user login."""
    firebaseToken: str = Field(..., description="Firebase ID token from frontend")
    rememberMe: bool = Field(default=False, description="Extend session to 30 days")


class SessionResponse(BaseModel):
    """Session information in API responses."""
    id: str = Field(..., description="Session ID")
    device: DeviceSchema
    location: Optional[LocationSchema] = None
    createdAt: datetime
    lastActiveAt: datetime
    isCurrent: bool = Field(default=False)

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[SessionResponse]


class AuthResponse(BaseModel):
    """Response for successful authentication (login/register)."""
    user: dict
    sessionToken: str
    expiresAt: datetime


class LogoutResponse(BaseModel):
    """Response for logout."""
    message: str = "Logged out successfully"


class RevokeSessionResponse(BaseModel):
    """Response for revoking a single session."""
    message: str = "Session revoked successfully"


class RevokeAllSessionsResponse(BaseModel):
    """Response for revoking all sessions."""
    revokedCount: int
    message: str = "Sessions revoked successfully"


class UserBasicResponse(BaseModel):
    """Basic user information in responses."""
    id: str
    email: EmailStr
    status: str
    profile: dict
    organization: str
    country: str
    createdAt: datetime
    lastLoginAt: Optional[datetime] = None

    class Config:
        from_attributes = True
