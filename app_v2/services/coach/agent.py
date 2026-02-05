"""
Abstract AI agent for coaching operations.

Provides the interface for AI operations used by the coaching system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterator


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


class Agent(ABC):
    """
    Abstract AI agent for coaching operations.
    Implementation provided separately - may use LLMs, RAG, memory systems.
    """

    @abstractmethod
    async def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> Iterator[str] | str:
        """
        Generate a coaching response.

        Args:
            context: CoachingContext with user data, history, follow-ups
            message: User's message
            stream: Whether to stream response

        Returns:
            Iterator of text chunks if streaming, else full response string
        """
        pass

    @abstractmethod
    async def generate_checkin_insight(
        self,
        context: CheckinInsightContext
    ) -> CheckinInsight:
        """
        Generate insight and tip after check-in.

        Args:
            context: CheckinInsightContext with metrics and trends

        Returns:
            CheckinInsight with insight string and tip string
        """
        pass

    @abstractmethod
    async def enhance_recommendation(
        self,
        base_description: str,
        patterns: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """
        Enhance a recommendation insight with personalized advice.

        Args:
            base_description: Template-generated description
            patterns: Detected patterns dict
            language: 'en' or 'sv'

        Returns:
            Enhanced description string
        """
        pass

    @abstractmethod
    def extract_topics(self, message: str) -> List[str]:
        """
        Extract coaching topics from a message.

        Args:
            message: User message or coach response

        Returns:
            List of topic strings
        """
        pass
