"""
Pydantic models for Content system request/response validation.

Defines schemas for content items and learning progress.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ContentItemResponse(BaseModel):
    """Content item in API responses."""
    id: str
    contentType: str
    status: str
    category: str
    sortOrder: int = 0
    titleEn: str
    titleSv: Optional[str] = None
    lengthMinutes: Optional[int] = None
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    audioFileEn: Optional[str] = None
    audioFileSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: bool = False
    videoAvailableInSv: bool = False
    steps: Optional[List[str]] = None
    closing: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None
    coachTopics: List[str] = []
    coachPriority: int = 0
    coachEnabled: bool = False
    progress: Optional[int] = None

    class Config:
        from_attributes = True


class ContentItemWithProgressResponse(BaseModel):
    """Content item with user progress."""
    content: ContentItemResponse
    progress: int = 0


class CreateContentRequest(BaseModel):
    """Request body for creating content."""
    contentType: str = Field(..., description="text_article | audio_article | audio_exercise | video_link | exercise")
    status: str = Field(default="draft", description="draft | in_review | published | archived")
    category: str = Field(default="other")
    sortOrder: int = Field(default=0)
    titleEn: str = Field(..., max_length=500)
    titleSv: Optional[str] = Field(None, max_length=500)
    lengthMinutes: Optional[int] = Field(None, ge=1)
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    audioFileEn: Optional[str] = None
    audioFileSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: bool = False
    videoAvailableInSv: bool = False
    steps: Optional[List[str]] = None
    closing: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None
    purpose: Optional[str] = None
    outcome: Optional[str] = None
    relatedFramework: Optional[str] = None
    voiceoverScriptEn: Optional[str] = None
    voiceoverScriptSv: Optional[str] = None
    ttsSpeed: float = Field(default=1.0, ge=0.7, le=1.2)
    ttsVoice: str = Field(default="Aria")
    backgroundMusicTrack: Optional[str] = None
    productionNotes: Optional[str] = None
    coachTopics: List[str] = []
    coachPriority: int = Field(default=0, ge=0)
    coachEnabled: bool = False


class UpdateContentRequest(BaseModel):
    """Request body for updating content."""
    contentType: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    sortOrder: Optional[int] = None
    titleEn: Optional[str] = Field(None, max_length=500)
    titleSv: Optional[str] = Field(None, max_length=500)
    lengthMinutes: Optional[int] = Field(None, ge=1)
    textContentEn: Optional[str] = None
    textContentSv: Optional[str] = None
    audioFileEn: Optional[str] = None
    audioFileSv: Optional[str] = None
    videoUrl: Optional[str] = None
    videoEmbedCode: Optional[str] = None
    videoAvailableInEn: Optional[bool] = None
    videoAvailableInSv: Optional[bool] = None
    steps: Optional[List[str]] = None
    closing: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None
    purpose: Optional[str] = None
    outcome: Optional[str] = None
    relatedFramework: Optional[str] = None
    voiceoverScriptEn: Optional[str] = None
    voiceoverScriptSv: Optional[str] = None
    ttsSpeed: Optional[float] = Field(None, ge=0.7, le=1.2)
    ttsVoice: Optional[str] = None
    backgroundMusicTrack: Optional[str] = None
    productionNotes: Optional[str] = None
    coachTopics: Optional[List[str]] = None
    coachPriority: Optional[int] = Field(None, ge=0)
    coachEnabled: Optional[bool] = None


class ProgressUpdateRequest(BaseModel):
    """Request body for updating progress."""
    progress: int = Field(..., ge=0, le=100)


class ProgressResponse(BaseModel):
    """Learning progress in API responses."""
    id: str
    userId: str
    contentId: str
    contentType: Optional[str] = None
    progress: int
    completedAt: Optional[datetime] = None
    lastAccessedAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompletionStatsResponse(BaseModel):
    """User's learning completion statistics."""
    totalCompleted: int
    byType: Dict[str, int]
    lastCompletedAt: Optional[datetime] = None


class ContentListResponse(BaseModel):
    """List of content items with progress."""
    items: List[ContentItemResponse]
    total: int


class CoachRecommendationsRequest(BaseModel):
    """Request for coach content recommendations."""
    topics: List[str]
    limit: int = Field(default=2, ge=1, le=10)


class ContentFilters(BaseModel):
    """Query filters for content."""
    contentType: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
