"""
Insight generation engine.

Detects patterns and generates insights based on configurable triggers.
"""

import logging
from typing import List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.progress.services.insight_service import InsightService
from app_v2.ai.services.pattern_detector import PatternDetector, PatternResult

logger = logging.getLogger(__name__)


class InsightEngine:
    """
    Analyzes check-in data for patterns and generates insights.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        insight_service: InsightService,
        pattern_detector: PatternDetector,
        agent=None
    ):
        """
        Initialize InsightEngine.

        Args:
            db: MongoDB database connection
            insight_service: For creating insights and loading triggers
            pattern_detector: For pattern detection
            agent: Optional AI agent for enhancement
        """
        self._db = db
        self._insight_service = insight_service
        self._pattern_detector = pattern_detector
        self._agent = agent

    async def generate_insights(
        self,
        user_id: str,
        use_ai: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns and generate new insights.

        Args:
            user_id: User ID
            use_ai: Whether to enhance recommendations with AI

        Returns:
            List of newly created insight documents
        """
        patterns = await self._pattern_detector.detect(user_id)

        if patterns is None:
            return []

        triggers = await self._insight_service.get_all_triggers()

        if not triggers:
            await self._insight_service.seed_default_triggers()
            triggers = await self._insight_service.get_all_triggers()

        created_insights = []

        for trigger in triggers:
            if not trigger.get("isActive", True):
                continue

            if self._evaluate_condition(trigger["condition"], patterns):
                has_recent = await self._insight_service.has_recent_insight(
                    user_id,
                    trigger["triggerId"],
                    trigger.get("duplicateWindowDays", 7)
                )

                if has_recent:
                    continue

                title, description = self._build_content(trigger, patterns)

                if trigger.get("useAiEnhancement") and use_ai and self._agent:
                    try:
                        description = await self._agent.enhance_recommendation(
                            description,
                            self._patterns_to_dict(patterns),
                            "en"
                        )
                    except Exception as e:
                        logger.warning(f"AI enhancement failed: {e}")

                insight = await self._insight_service.create_insight(
                    user_id=user_id,
                    insight_type=trigger["type"],
                    trigger=trigger["triggerId"],
                    title=title,
                    description=description,
                    metrics=self._patterns_to_dict(patterns)
                )

                created_insights.append(insight)

        return created_insights

    def _evaluate_condition(
        self,
        condition: str,
        patterns: PatternResult
    ) -> bool:
        """Evaluate a condition against patterns."""
        try:
            pattern_dict = self._patterns_to_dict(patterns)

            safe_vars = {
                "streak": pattern_dict.get("streak", {}),
                "morningCheckIns": pattern_dict.get("morningCheckins", 0),
                "stressDayPattern": pattern_dict.get("stressDayPattern"),
                "moodChange": pattern_dict.get("moodChange"),
                "stressChange": pattern_dict.get("stressChange"),
                "energyChange": pattern_dict.get("energyChange"),
                "lowEnergyDays": pattern_dict.get("lowEnergyDays", 0),
                "sleepMoodCorrelation": pattern_dict.get("sleepMoodCorrelation", 0),
                "None": None,
            }

            result = eval(condition, {"__builtins__": {}}, safe_vars)
            return bool(result)

        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition} - {e}")
            return False

    def _build_content(
        self,
        trigger: Dict[str, Any],
        patterns: PatternResult
    ) -> tuple:
        """Build title and description from trigger template."""
        pattern_dict = self._patterns_to_dict(patterns)

        title = trigger["title"]
        description = trigger["template"]

        if pattern_dict.get("stressDayPattern"):
            weekday = pattern_dict["stressDayPattern"].get("weekday", "")
            title = title.replace("{{weekday}}", weekday)
            description = description.replace("{{weekday}}", weekday)

        for key, value in pattern_dict.items():
            if value is not None and not isinstance(value, dict):
                placeholder = "{{" + key + "}}"
                title = title.replace(placeholder, str(value))
                description = description.replace(placeholder, str(value))

        if pattern_dict.get("moodChange") is not None:
            description = description.replace("{{moodChange}}", str(abs(pattern_dict["moodChange"])))

        if pattern_dict.get("lowEnergyDays") is not None:
            description = description.replace("{{lowEnergyDays}}", str(pattern_dict["lowEnergyDays"]))

        return title, description

    def _patterns_to_dict(self, patterns: PatternResult) -> Dict[str, Any]:
        """Convert PatternResult to dict."""
        return {
            "streak": patterns.streak,
            "morningCheckins": patterns.morning_checkins,
            "stressDayPattern": patterns.stress_day_pattern,
            "moodChange": patterns.mood_change,
            "stressChange": patterns.stress_change,
            "energyChange": patterns.energy_change,
            "lowEnergyDays": patterns.low_energy_days,
            "sleepMoodCorrelation": patterns.sleep_mood_correlation,
        }
