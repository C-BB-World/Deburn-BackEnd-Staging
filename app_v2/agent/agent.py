"""
Abstract AI agent interface.

Defines the contract for AI coaching agents.
All AI operations go through this abstraction.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Union

from app_v2.agent.types import CoachingContext, CheckinInsightContext, CheckinInsight


class Agent(ABC):
    """
    Abstract AI agent for coaching operations.

    Implementations may use different LLM providers (Claude, OpenAI, etc.)
    while maintaining a consistent interface for the coaching system.
    """

    @abstractmethod
    async def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> Union[AsyncIterator[str], str]:
        """
        Generate a coaching response.

        Args:
            context: CoachingContext with user data, history, follow-ups
            message: User's message
            stream: Whether to stream response

        Returns:
            AsyncIterator of text chunks if streaming, else full response string
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
            List of topic strings from COACHING_TOPICS enum
        """
        pass
