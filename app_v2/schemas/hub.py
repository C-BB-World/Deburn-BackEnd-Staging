"""
Pydantic models for Hub system request/response validation.

Defines schemas for hub admin, content, coach config, and compliance.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────
# Hub Admin Models
# ─────────────────────────────────────────────────────────────────

class AddHubAdminRequest(BaseModel):
    """Request to add a hub admin."""
    email: str


class RemoveHubAdminRequest(BaseModel):
    """Request to remove a hub admin."""
    email: str


class HubAdminResponse(BaseModel):
    """Hub admin in API responses."""
    id: str
    email: str
    addedBy: Optional[str] = None
    addedAt: Optional[datetime] = None
    status: str
    removedAt: Optional[datetime] = None
    removedBy: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class HubAdminsListResponse(BaseModel):
    """List of hub admins."""
    admins: List[HubAdminResponse]


# ─────────────────────────────────────────────────────────────────
# Content Models
# ─────────────────────────────────────────────────────────────────

class CreateContentRequest(BaseModel):
    """Request to create content item."""
    contentType: str = Field(..., pattern="^(text_article|audio_article|audio_exercise|video_link)$")
    status: str = Field(default="draft", pattern="^(draft|in_review|published|archived)$")
    titleEn: str = Field(default="")
    titleSv: str = Field(default="")
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: bool = True
    videoAvailableInSv: bool = True
    lengthMinutes: int = Field(default=0, ge=0)
    purpose: Optional[str] = None
    outcome: Optional[str] = None
    relatedFramework: Optional[str] = None
    category: str = Field(default="other")
    sortOrder: int = Field(default=0)
    coachTopics: List[str] = Field(default=[])
    coachPriority: int = Field(default=0)
    coachEnabled: bool = True
    ttsSpeed: float = Field(default=1.0, ge=0.7, le=1.2)
    ttsVoice: str = Field(default="Aria")
    voiceoverScriptEn: Optional[str] = None
    voiceoverScriptSv: Optional[str] = None
    backgroundMusicTrack: Optional[str] = None
    productionNotes: Optional[str] = None


class UpdateContentRequest(BaseModel):
    """Request to update content item."""
    contentType: Optional[str] = Field(None, pattern="^(text_article|audio_article|audio_exercise|video_link)$")
    status: Optional[str] = Field(None, pattern="^(draft|in_review|published|archived)$")
    titleEn: Optional[str] = None
    titleSv: Optional[str] = None
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: Optional[bool] = None
    videoAvailableInSv: Optional[bool] = None
    lengthMinutes: Optional[int] = Field(None, ge=0)
    purpose: Optional[str] = None
    outcome: Optional[str] = None
    relatedFramework: Optional[str] = None
    category: Optional[str] = None
    sortOrder: Optional[int] = None
    coachTopics: Optional[List[str]] = None
    coachPriority: Optional[int] = None
    coachEnabled: Optional[bool] = None
    ttsSpeed: Optional[float] = Field(None, ge=0.7, le=1.2)
    ttsVoice: Optional[str] = None
    voiceoverScriptEn: Optional[str] = None
    voiceoverScriptSv: Optional[str] = None
    backgroundMusicTrack: Optional[str] = None
    productionNotes: Optional[str] = None


class ContentResponse(BaseModel):
    """Content item in API responses."""
    id: str
    contentType: Optional[str] = None
    status: Optional[str] = None
    titleEn: Optional[str] = None
    titleSv: Optional[str] = None
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    audioFileEn: Optional[str] = None
    audioFileSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: Optional[bool] = None
    videoAvailableInSv: Optional[bool] = None
    lengthMinutes: Optional[int] = None
    purpose: Optional[str] = None
    outcome: Optional[str] = None
    relatedFramework: Optional[str] = None
    category: Optional[str] = None
    sortOrder: Optional[int] = None
    coachTopics: List[str] = []
    coachPriority: Optional[int] = None
    coachEnabled: Optional[bool] = None
    ttsSpeed: Optional[float] = None
    ttsVoice: Optional[str] = None
    voiceoverScriptEn: Optional[str] = None
    voiceoverScriptSv: Optional[str] = None
    backgroundMusicTrack: Optional[str] = None
    productionNotes: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class ContentListResponse(BaseModel):
    """List of content items."""
    items: List[ContentResponse]


# ─────────────────────────────────────────────────────────────────
# Coach Config Models
# ─────────────────────────────────────────────────────────────────

class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""
    language: str = Field(..., pattern="^(en|sv)$")
    promptName: str
    content: str


class PromptsResponse(BaseModel):
    """System prompts response."""
    prompts: Dict[str, Dict[str, str]]


class ExercisesResponse(BaseModel):
    """Exercises and modules response."""
    exercises: List[Dict[str, Any]]
    modules: List[Dict[str, Any]]


class UpdateExercisesRequest(BaseModel):
    """Request to update exercises."""
    exercises: List[Dict[str, Any]]
    modules: List[Dict[str, Any]]


class CoachSettingsResponse(BaseModel):
    """Coach settings response."""
    id: str
    key: Optional[str] = None
    dailyExchangeLimit: int = 15
    deletionGracePeriodDays: int = 30
    updatedAt: Optional[datetime] = None
    updatedBy: Optional[str] = None
    createdAt: Optional[datetime] = None


class UpdateCoachSettingsRequest(BaseModel):
    """Request to update coach settings."""
    dailyExchangeLimit: Optional[int] = Field(None, ge=1, le=100)
    deletionGracePeriodDays: Optional[int] = Field(None, ge=1, le=365)


class SafetyLevelInfo(BaseModel):
    """Safety escalation level info."""
    level: int
    name: str
    action: str
    description: Optional[str] = None
    keywords: List[str] = []


class SafetyConfigResponse(BaseModel):
    """Safety configuration response."""
    levels: List[SafetyLevelInfo]
    hardBoundaries: List[str] = Field(alias="hard_boundaries")

    class Config:
        populate_by_name = True


# ─────────────────────────────────────────────────────────────────
# Compliance Models
# ─────────────────────────────────────────────────────────────────

class ComplianceStatsResponse(BaseModel):
    """Compliance dashboard stats."""
    totalUsers: int
    pendingDeletions: int
    auditLogCount: int
    activeSessions: int


class UserComplianceResponse(BaseModel):
    """User compliance data."""
    userId: str
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    status: Optional[str] = None
    createdAt: Optional[datetime] = None
    lastLogin: Optional[datetime] = None
    deletionRequestedAt: Optional[datetime] = None
    checkinCount: int = 0
    conversationCount: int = 0
    sessionCount: int = 0


class PendingDeletionResponse(BaseModel):
    """Pending deletion info."""
    userId: str
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    deletionRequestedAt: Optional[datetime] = None
    scheduledDeletionAt: Optional[datetime] = None
    daysRemaining: int
    canDeleteNow: bool


class PendingDeletionsListResponse(BaseModel):
    """List of pending deletions."""
    pendingDeletions: List[PendingDeletionResponse]


class DeletionResultResponse(BaseModel):
    """Account deletion result."""
    success: bool
    deletedCheckIns: int
    deletedConversations: int
    deletedCommitments: int
    deletedInsights: int
    anonymizedAuditLogs: int
    deletedAt: str


class SecurityConfigResponse(BaseModel):
    """Security configuration."""
    tokenExpiryHours: int
    refreshTokenExpiryDays: int
    maxSessionsPerUser: int
    passwordMinLength: int
    corsOrigins: List[str]
    dataRetentionDays: int
    auditLogRetentionDays: int


class LookupUserRequest(BaseModel):
    """Request to lookup user by email."""
    email: str


class DeleteUserRequest(BaseModel):
    """Request to delete user."""
    userId: str


class ExportUserRequest(BaseModel):
    """Request to export user data."""
    userId: str
