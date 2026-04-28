"""
Pydantic models for Hub system request/response validation.

Matches the API documentation in docs/v2/architecture/api/hub.md
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# =============================================================================
# Request Schemas
# =============================================================================

class AddHubAdminRequest(BaseModel):
    """POST /api/hub/admins"""
    email: str


class CreateOrganizationRequest(BaseModel):
    """POST /api/hub/organizations"""
    name: str
    domain: str


class AddOrgAdminRequest(BaseModel):
    """POST /api/hub/org-admins"""
    email: str
    organizationId: str


class UpdateCoachSettingsRequest(BaseModel):
    """PUT /api/hub/settings/coach"""
    model: Optional[str] = None
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    systemPrompt: Optional[str] = None


class UpdatePromptRequest(BaseModel):
    """PUT /api/hub/coach/prompts/:language/:promptName"""
    content: str


class Exercise(BaseModel):
    """Individual exercise."""
    id: str
    title: str
    description: str
    duration: int  # Duration in minutes
    category: str
    instructions: List[str]


class UpdateExercisesRequest(BaseModel):
    """PUT /api/hub/coach/exercises"""
    exercises: List[Exercise]


class CreateContentRequest(BaseModel):
    """POST /api/hub/content"""
    title: str
    description: str
    contentType: str  # "video" | "audio" | "article" | "exercise"
    category: str
    duration: Optional[int] = None  # Duration in minutes
    thumbnail: Optional[str] = None
    status: str  # "draft" | "published"
    content: Optional[Dict[str, Any]] = None


class UpdateContentRequest(BaseModel):
    """PUT /api/hub/content/:id"""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    status: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
