"""
Claude-based AI agent implementation.

Uses ClaudeProvider from common/ai/ for API calls.
Loads prompts dynamically from PromptService.
"""

import logging
import re
from typing import List, Dict, Any, AsyncIterator, Union

from common.ai.claude import ClaudeProvider
from app_v2.agent.agent import Agent
from app_v2.agent.prompt_service import PromptService
from app_v2.agent.topics import extract_topics as extract_topics_from_message
from app_v2.agent.types import CoachingContext, CheckinInsightContext, CheckinInsight

logger = logging.getLogger(__name__)


class ClaudeAgent(Agent):
    """
    Claude-based AI agent with dynamic prompt loading.

    Uses ClaudeProvider from common/ai/ for API calls.
    Loads system prompts from MongoDB via PromptService.
    """

    def __init__(
        self,
        provider: ClaudeProvider,
        prompt_service: PromptService,
        max_tokens: int = 1024
    ):
        """
        Initialize ClaudeAgent.

        Args:
            provider: ClaudeProvider instance (from common/ai/)
            prompt_service: For dynamic prompt loading
            max_tokens: Maximum response tokens
        """
        self._provider = provider
        self._prompt_service = prompt_service
        self._max_tokens = max_tokens

    async def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> Union[AsyncIterator[str], str]:
        """
        Generate coaching response.

        1. Load system prompt from PromptService
        2. Inject user context (profile, wellbeing, commitments)
        3. Build message history
        4. Delegate to ClaudeProvider
        """
        system_prompt = await self._build_system_prompt(context)
        history = self._build_history(context)

        if stream:
            return self._provider.stream_chat(
                message=message,
                system_prompt=system_prompt,
                conversation_history=history,
                max_tokens=self._max_tokens
            )
        else:
            return await self._provider.chat(
                message=message,
                system_prompt=system_prompt,
                conversation_history=history,
                max_tokens=self._max_tokens
            )

    async def generate_checkin_insight(
        self,
        context: CheckinInsightContext
    ) -> CheckinInsight:
        """Generate insight and tip after check-in."""
        base_prompt = await self._prompt_service.get_system_prompt(
            "checkin_insight",
            context.language
        )

        prompt = self._build_checkin_prompt(base_prompt, context)

        try:
            response = await self._provider.chat(
                message=prompt,
                max_tokens=300
            )

            insight, tip = self._parse_insight_response(response)
            return CheckinInsight(insight=insight, tip=tip)

        except Exception as e:
            logger.error(f"Failed to generate check-in insight: {e}")
            return self._get_fallback_insight(context.language)

    async def enhance_recommendation(
        self,
        base_description: str,
        patterns: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """Enhance a recommendation with personalized advice."""
        base_prompt = await self._prompt_service.get_system_prompt(
            "recommendation",
            language
        )

        prompt = f"""{base_prompt}

Based on these detected patterns:
{patterns}

Enhance this recommendation:
"{base_description}"
"""

        try:
            response = await self._provider.chat(
                message=prompt,
                max_tokens=150
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to enhance recommendation: {e}")
            return base_description

    def extract_topics(self, message: str) -> List[str]:
        """Extract coaching topics from a message."""
        return extract_topics_from_message(message)

    async def _build_system_prompt(self, context: CoachingContext) -> str:
        """
        Build complete system prompt.

        1. Base prompt from MongoDB (via PromptService)
        2. + User context section
        3. + Wellbeing data
        4. + Due commitments (if any)
        5. + Safety level note (if level 1)
        """
        base_prompt = await self._prompt_service.get_system_prompt(
            "coaching",
            context.language
        )

        parts = [base_prompt, "\n\n## Context About This User\n"]

        # User profile
        if context.user_profile:
            name = context.user_profile.get("firstName", "")
            role = context.user_profile.get("role", "")
            org = context.user_profile.get("organization", "")

            if name:
                parts.append(f"Name: {name}\n")
            if role:
                parts.append(f"Role: {role}\n")
            if org:
                parts.append(f"Organization: {org}\n")

        # Wellbeing data
        if context.wellbeing:
            parts.append("\n## Recent Wellbeing\n")
            for key, value in context.wellbeing.items():
                if value is not None and key != "date":
                    parts.append(f"- {key}: {value}\n")

        # Due commitments
        if context.due_commitments:
            parts.append("\n## Follow-Up on Previous Commitments\n")
            parts.append("The user has pending micro-commitments to follow up on:\n\n")

            for i, commitment in enumerate(context.due_commitments, 1):
                parts.append(f"**{i}. Commitment:**\n")
                parts.append(f'"{commitment.get("commitment", "")}"\n')

                if commitment.get("reflectionQuestion"):
                    parts.append(f'Reflection question: "{commitment["reflectionQuestion"]}"\n')

                parts.append("\n")

            parts.append("Ask how it went and what they learned.\n")

        # Safety level note
        if context.safety_level == 1:
            parts.append("\n## Note\n")
            parts.append("The user seems to be going through a difficult time. ")
            parts.append("Be extra empathetic and supportive.\n")

        return "".join(parts)

    def _build_history(self, context: CoachingContext) -> List[Dict[str, str]]:
        """Convert conversation history to provider format."""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in context.conversation_history[-10:]
        ]

    def _build_checkin_prompt(
        self,
        base_prompt: str,
        context: CheckinInsightContext
    ) -> str:
        """Build prompt for check-in insight generation."""
        checkin = context.current_checkin
        trends = context.trends

        return f"""{base_prompt}

Current check-in:
- Mood: {checkin.get("mood", 3)}/5
- Energy: {checkin.get("energy", 5)}/10
- Stress: {checkin.get("stress", 5)}/10
- Sleep: {checkin.get("sleep", 3)}/5

Trends (last 14 days):
- Mood change: {trends.get("mood_change", 0)}%
- Energy change: {trends.get("energy_change", 0)}%
- Stress change: {trends.get("stress_change", 0)}%

Current streak: {context.streak} days
Day of week: {context.day_of_week}
"""

    def _parse_insight_response(self, text: str) -> tuple:
        """Parse insight and tip from response."""
        insight = ""
        tip = ""

        insight_match = re.search(r'INSIGHT:\s*(.+?)(?=TIP:|$)', text, re.DOTALL)
        if insight_match:
            insight = insight_match.group(1).strip()

        tip_match = re.search(r'TIP:\s*(.+?)$', text, re.DOTALL)
        if tip_match:
            tip = tip_match.group(1).strip()

        if not insight:
            insight = "Keep tracking your wellbeing for personalized insights."
        if not tip:
            tip = "Try taking a few deep breaths before your next meeting."

        return insight, tip

    def _get_fallback_insight(self, language: str) -> CheckinInsight:
        """Get fallback insight when AI fails."""
        if language == "sv":
            return CheckinInsight(
                insight="Fortsätt checka in! Konsekvens hjälper till att bygga självmedvetenhet.",
                tip="Ta en stund idag för att märka hur du mår."
            )

        return CheckinInsight(
            insight="Keep checking in! Consistency helps build self-awareness.",
            tip="Take a moment today to notice how you're feeling."
        )
