"""
AI-powered insight generator for check-ins.

Generates insights and tips based on check-in data using AI.
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from app_v2.checkin.services.checkin_service import CheckInService

if TYPE_CHECKING:
    from common.ai.claude import ClaudeAI

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Generates AI-powered insights and tips based on check-in data.
    Called after check-in submission to provide immediate feedback.
    """

    INSIGHT_PROMPT_TEMPLATE = """Based on the user's check-in data, provide a brief insight about their patterns and a practical tip.

Current check-in:
- Mood: {mood}/5
- Physical Energy: {physical_energy}/10
- Mental Energy: {mental_energy}/10
- Sleep Quality: {sleep}/5
- Stress Level: {stress}/10

Recent history (last 7 days):
{history}

Provide your response in the following format:
INSIGHT: [One sentence observation about their patterns]
TIP: [One actionable recommendation]

Keep both the insight and tip concise (under 100 characters each)."""

    def __init__(
        self,
        ai_client: Optional["ClaudeAI"],
        checkin_service: CheckInService
    ):
        """
        Initialize InsightGenerator.

        Args:
            ai_client: AI service client (Claude API)
            checkin_service: For fetching historical data
        """
        self._ai_client = ai_client
        self._checkin_service = checkin_service

    async def generate_insight(
        self,
        user_id: str,
        current_checkin: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate insight and tip for a check-in.

        Args:
            user_id: MongoDB user ID
            current_checkin: The just-submitted check-in data

        Returns:
            dict with keys:
                - insight: str (pattern observation)
                - tip: str (actionable recommendation)
        """
        if not self._ai_client:
            return self._generate_fallback_insight(current_checkin)

        try:
            history = await self._checkin_service.get_checkins_for_period(user_id, 7)
            history_text = self._format_history(history)

            metrics = current_checkin.get("metrics", {})
            prompt = self.INSIGHT_PROMPT_TEMPLATE.format(
                mood=metrics.get("mood", 3),
                physical_energy=metrics.get("physicalEnergy", 5),
                mental_energy=metrics.get("mentalEnergy", 5),
                sleep=metrics.get("sleep", 3),
                stress=metrics.get("stress", 5),
                history=history_text
            )

            response = await self._ai_client.generate(prompt, max_tokens=200)
            return self._parse_response(response)

        except Exception as e:
            logger.warning(f"AI insight generation failed: {e}")
            return self._generate_fallback_insight(current_checkin)

    def _format_history(self, checkins: list) -> str:
        """Format check-in history for the prompt."""
        if not checkins:
            return "No recent history available."

        lines = []
        for checkin in checkins[-7:]:
            metrics = checkin.get("metrics", {})
            date = checkin.get("date", "Unknown")
            lines.append(
                f"- {date}: Mood {metrics.get('mood')}, "
                f"Energy {(metrics.get('physicalEnergy', 0) + metrics.get('mentalEnergy', 0)) / 2:.1f}, "
                f"Stress {metrics.get('stress')}"
            )

        return "\n".join(lines)

    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse AI response to extract insight and tip."""
        insight = ""
        tip = ""

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("INSIGHT:"):
                insight = line.replace("INSIGHT:", "").strip()
            elif line.startswith("TIP:"):
                tip = line.replace("TIP:", "").strip()

        if not insight:
            insight = "Keep tracking your wellness to discover patterns."
        if not tip:
            tip = "Try to maintain consistent sleep and exercise habits."

        return {
            "insight": insight[:150],
            "tip": tip[:150]
        }

    def _generate_fallback_insight(self, checkin: Dict[str, Any]) -> Dict[str, str]:
        """Generate a simple fallback insight without AI."""
        metrics = checkin.get("metrics", {})
        mood = metrics.get("mood", 3)
        stress = metrics.get("stress", 5)
        sleep = metrics.get("sleep", 3)

        if stress >= 7:
            return {
                "insight": "Your stress levels are elevated today.",
                "tip": "Try a 5-minute breathing exercise to help you relax."
            }
        elif mood <= 2:
            return {
                "insight": "You're having a challenging day.",
                "tip": "Consider taking a short walk or reaching out to a friend."
            }
        elif sleep <= 2:
            return {
                "insight": "Your sleep quality was low last night.",
                "tip": "Try to wind down earlier tonight with no screens before bed."
            }
        else:
            return {
                "insight": "You're maintaining steady wellness levels.",
                "tip": "Keep up your current routines and stay consistent."
            }
