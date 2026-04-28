"""
AI-powered insight generator for check-ins.

Generates bilingual insights and tips based on check-in data using AI.
"""

import logging
import os
from typing import Dict, Any, Optional, TYPE_CHECKING

from app_v2.services.checkin.checkin_service import CheckInService

if TYPE_CHECKING:
    from common.ai.claude import ClaudeAI

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Generates AI-powered insights and tips based on check-in data.
    Called after check-in submission to provide immediate feedback.
    Supports bilingual output (English and Swedish).
    """

    def __init__(
        self,
        ai_client: Optional["ClaudeAI"],
        checkin_service: CheckInService,
        lookback_days: Optional[int] = None,
        prompts_dir: Optional[str] = None
    ):
        """
        Initialize InsightGenerator.

        Args:
            ai_client: AI service client (Claude API)
            checkin_service: For fetching historical data
            lookback_days: Days of history to consider (default from env)
            prompts_dir: Directory containing prompt files
        """
        self._ai_client = ai_client
        self._checkin_service = checkin_service
        self._lookback_days = lookback_days or int(os.environ.get("INSIGHT_LOOKBACK_DAYS", "7"))
        self._prompts_dir = prompts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "prompts", "system"
        )
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load prompt template from file."""
        prompt_path = os.path.join(self._prompts_dir, "en", "checkin-insight.md")

        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    logger.debug(f"Loaded insight prompt from {prompt_path}")
                    return content
        except Exception as e:
            logger.warning(f"Failed to load prompt from file: {e}")

        # Fallback to hardcoded prompt
        logger.warning("Using fallback hardcoded prompt template")
        return """Based on the user's check-in data, provide a brief insight about their patterns and a practical tip.

Current check-in:
- Mood: {mood}/5
- Physical Energy: {physical_energy}/10
- Mental Energy: {mental_energy}/10
- Sleep Quality: {sleep}/5
- Stress Level: {stress}/10

Recent history (last {lookback_days} days):
{history}

Provide your response in the following format (all four lines are required):
INSIGHT_EN: [One sentence observation about their patterns in English]
INSIGHT_SV: [Same insight translated to Swedish]
TIP_EN: [One actionable recommendation in English]
TIP_SV: [Same tip translated to Swedish]

Keep insights and tips concise (under 100 characters each). Use a supportive, coaching tone."""

    async def generate_insight(
        self,
        user_id: str,
        current_checkin: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate bilingual insight and tip for a check-in.

        Args:
            user_id: MongoDB user ID
            current_checkin: The just-submitted check-in data

        Returns:
            dict with keys:
                - insight: str (English pattern observation)
                - insightSv: str (Swedish pattern observation)
                - tip: str (English actionable recommendation)
                - tipSv: str (Swedish actionable recommendation)
        """
        if not self._ai_client:
            return self._generate_fallback_insight(current_checkin)

        try:
            history = await self._checkin_service.get_checkins_for_period(
                user_id, self._lookback_days
            )
            history_text = self._format_history(history)

            metrics = current_checkin.get("metrics", {})
            prompt = self._prompt_template.format(
                mood=metrics.get("mood", 3),
                physical_energy=metrics.get("physicalEnergy", 5),
                mental_energy=metrics.get("mentalEnergy", 5),
                sleep=metrics.get("sleep", 3),
                stress=metrics.get("stress", 5),
                lookback_days=self._lookback_days,
                history=history_text
            )

            response = await self._ai_client.chat(prompt, max_tokens=300)
            return self._parse_response(response)

        except Exception as e:
            logger.warning(f"AI insight generation failed: {e}")
            return self._generate_fallback_insight(current_checkin)

    def _format_history(self, checkins: list) -> str:
        """Format check-in history for the prompt."""
        if not checkins:
            return "No recent history available."

        lines = []
        for checkin in checkins[-self._lookback_days:]:
            metrics = checkin.get("metrics", {})
            date = checkin.get("date", "Unknown")
            # Include day of week for pattern detection
            try:
                from datetime import datetime
                dt = datetime.strptime(date, "%Y-%m-%d")
                day_name = dt.strftime("%A")
                date_str = f"{date} ({day_name})"
            except:
                date_str = date

            lines.append(
                f"- {date_str}: Mood {metrics.get('mood')}, "
                f"Energy {(metrics.get('physicalEnergy', 0) + metrics.get('mentalEnergy', 0)) / 2:.1f}, "
                f"Sleep {metrics.get('sleep')}, Stress {metrics.get('stress')}"
            )

        return "\n".join(lines)

    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse AI response to extract bilingual insight and tip."""
        insight_en = ""
        insight_sv = ""
        tip_en = ""
        tip_sv = ""

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("INSIGHT_EN:"):
                insight_en = line.replace("INSIGHT_EN:", "").strip()
            elif line.startswith("INSIGHT_SV:"):
                insight_sv = line.replace("INSIGHT_SV:", "").strip()
            elif line.startswith("TIP_EN:"):
                tip_en = line.replace("TIP_EN:", "").strip()
            elif line.startswith("TIP_SV:"):
                tip_sv = line.replace("TIP_SV:", "").strip()

        # Fallbacks for missing fields
        if not insight_en:
            insight_en = "Keep tracking your wellness to discover patterns."
        if not insight_sv:
            insight_sv = "Fortsätt spåra ditt välmående för att upptäcka mönster."
        if not tip_en:
            tip_en = "Try to maintain consistent sleep and exercise habits."
        if not tip_sv:
            tip_sv = "Försök att upprätthålla regelbundna sömn- och träningsvanor."

        return {
            "insight": insight_en[:150],
            "insightSv": insight_sv[:150],
            "tip": tip_en[:150],
            "tipSv": tip_sv[:150]
        }

    def _generate_fallback_insight(self, checkin: Dict[str, Any]) -> Dict[str, str]:
        """Generate a simple bilingual fallback insight without AI."""
        metrics = checkin.get("metrics", {})
        mood = metrics.get("mood", 3)
        stress = metrics.get("stress", 5)
        sleep = metrics.get("sleep", 3)

        if stress >= 7:
            return {
                "insight": "Your stress levels are elevated today.",
                "insightSv": "Din stressnivå är förhöjd idag.",
                "tip": "Try a 5-minute breathing exercise to help you relax.",
                "tipSv": "Prova en 5-minuters andningsövning för att slappna av."
            }
        elif mood <= 2:
            return {
                "insight": "You're having a challenging day.",
                "insightSv": "Du har en utmanande dag.",
                "tip": "Consider taking a short walk or reaching out to a friend.",
                "tipSv": "Överväg att ta en kort promenad eller kontakta en vän."
            }
        elif sleep <= 2:
            return {
                "insight": "Your sleep quality was low last night.",
                "insightSv": "Din sömnkvalitet var låg i natt.",
                "tip": "Try to wind down earlier tonight with no screens before bed.",
                "tipSv": "Försök att varva ner tidigare ikväll utan skärmar före sänggåendet."
            }
        else:
            return {
                "insight": "You're maintaining steady wellness levels.",
                "insightSv": "Du upprätthåller stabila välmåendenivåer.",
                "tip": "Keep up your current routines and stay consistent.",
                "tipSv": "Fortsätt med dina nuvarande rutiner och var konsekvent."
            }
