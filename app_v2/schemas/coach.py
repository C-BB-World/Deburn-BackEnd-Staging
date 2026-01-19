"""
Pydantic models for AI Coaching system request/response validation.

Defines schemas for conversations, commitments, and insights.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """Request body for sending a coaching message."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversationId: Optional[str] = None
    language: str = Field(default="en", pattern="^(en|sv)$")


class ConversationMessageResponse(BaseModel):
    """Message in conversation history."""
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    """Conversation in API responses."""
    id: str
    conversationId: str
    userId: str
    messages: List[ConversationMessageResponse]
    topics: List[str]
    status: str
    lastMessageAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None


class ConversationStarterResponse(BaseModel):
    """Conversation starter suggestion."""
    label: str
    context: Optional[str] = None


class StartersResponse(BaseModel):
    """List of conversation starters."""
    starters: List[ConversationStarterResponse]


class CommitmentResponse(BaseModel):
    """Commitment in API responses."""
    id: str
    userId: str
    conversationId: Optional[str] = None
    commitment: str
    reflectionQuestion: Optional[str] = None
    psychologicalTrigger: Optional[str] = None
    circlePrompt: Optional[str] = None
    topic: str
    status: str
    followUpDate: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    reflectionNotes: Optional[str] = None
    helpfulnessRating: Optional[int] = None
    followUpCount: int = 0
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompleteCommitmentRequest(BaseModel):
    """Request to complete a commitment."""
    reflectionNotes: Optional[str] = Field(None, max_length=2000)
    helpfulnessRating: Optional[int] = Field(None, ge=1, le=5)


class CommitmentStatsResponse(BaseModel):
    """Commitment statistics."""
    active: int
    completed: int
    expired: int
    dismissed: int
    total: int
    completionRate: int


class SafetyCheckResponse(BaseModel):
    """Result of safety check."""
    level: int
    isCrisis: bool
    action: str
    triggers: List[str] = []


class PatternResultResponse(BaseModel):
    """Detected patterns from check-in data."""
    streak: Dict[str, int]
    morningCheckins: int
    stressDayPattern: Optional[Dict[str, Any]] = None
    moodChange: Optional[int] = None
    stressChange: Optional[int] = None
    energyChange: Optional[int] = None
    lowEnergyDays: int
    sleepMoodCorrelation: float


class CheckinInsightRequest(BaseModel):
    """Request for check-in insight."""
    mood: int = Field(..., ge=1, le=5)
    energy: int = Field(..., ge=1, le=10)
    stress: int = Field(..., ge=1, le=10)
    sleep: int = Field(..., ge=1, le=5)
    language: str = Field(default="en", pattern="^(en|sv)$")


class CheckinInsightResponse(BaseModel):
    """Generated check-in insight."""
    insight: str
    tip: str


class RecentConversationsResponse(BaseModel):
    """List of recent conversations."""
    conversations: List[ConversationResponse]


class VoiceRequest(BaseModel):
    """Request for text-to-speech conversion."""
    text: str = Field(..., min_length=1, max_length=3000)
    voice: Optional[str] = Field(default="Aria")
    language: str = Field(default="en", pattern="^(en|sv)$")
