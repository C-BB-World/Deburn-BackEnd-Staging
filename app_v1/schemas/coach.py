"""
Coach request/response schemas.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class WellbeingContext(BaseModel):
    """User's recent wellbeing data for context."""

    mood: Optional[int] = None
    energy: Optional[int] = None
    stress: Optional[int] = None
    streak: Optional[int] = None


class CoachContext(BaseModel):
    """Additional context for coaching conversation."""

    recentCheckin: Optional[WellbeingContext] = None


class ChatRequest(BaseModel):
    """Coach chat request."""

    message: str = Field(min_length=1, max_length=5000)
    conversationId: Optional[str] = None
    language: Optional[str] = Field(None, pattern=r"^(en|sv)$")
    context: Optional[CoachContext] = None


class SuggestedAction(BaseModel):
    """Suggested action in coach response."""

    type: str  # "setGoal", "startCheckIn", "openLearning"
    label: str


class ChatResponse(BaseModel):
    """Coach chat response."""

    text: str
    conversationId: str
    topics: List[str] = []
    suggestedActions: Optional[List[SuggestedAction]] = None
    isSystemMessage: bool = False


class ConversationStarter(BaseModel):
    """Conversation starter option."""

    id: str
    text: str
    category: str  # "wellness", "goals", "leadership", "work"
