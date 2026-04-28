"""
Type definitions for the Agent system.

Contains dataclasses used across Agent and Memory components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A complete conversation with messages."""
    id: str
    conversation_id: str
    user_id: str
    messages: List[Message]
    topics: List[str]
    status: str  # "active" | "archived"
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime


@dataclass
class ConversationSummary:
    """Summary of a conversation for search results."""
    conversation_id: str
    user_id: str
    preview: str  # First ~100 chars of last message
    topics: List[str]
    message_count: int
    last_message_at: Optional[datetime]


@dataclass
class CoachingContext:
    """Context for coaching conversation."""
    user_profile: Dict[str, Any]
    wellbeing: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    due_commitments: List[Dict[str, Any]]
    safety_level: int
    language: str


@dataclass
class CheckinInsightContext:
    """Context for check-in insight generation."""
    current_checkin: Dict[str, Any]
    trends: Dict[str, Any]
    streak: int
    day_of_week: int
    language: str


@dataclass
class CheckinInsight:
    """Generated insight and tip."""
    insight: str
    tip: str
