"""
Exercise action handler.

Generates exercise recommendations (breathing, calming, etc.) based on topics.
"""

from typing import List, Dict, Any

from ..base import Action, ActionHandler
from ..retrieval.base import ActionRetriever


class ExerciseHandler(ActionHandler):
    """
    Handles exercise action recommendations.

    Uses an ActionRetriever to find relevant exercises
    based on detected topics.
    """

    def __init__(self, retriever: ActionRetriever):
        """
        Initialize ExerciseHandler.

        Args:
            retriever: ActionRetriever to use for content lookup
        """
        self._retriever = retriever

    @property
    def action_type(self) -> str:
        """Return action type identifier."""
        return "exercise"

    async def generate(
        self,
        topics: List[str],
        language: str,
        context: Dict[str, Any]
    ) -> List[Action]:
        """
        Generate exercise recommendations.

        Retrieves actions and filters to exercise type only.

        Args:
            topics: List of detected topic strings
            language: Language code ('en' or 'sv')
            context: Additional context

        Returns:
            List of exercise Action objects
        """
        actions = await self._retriever.retrieve(topics, language, limit=4)

        # Filter to exercise type only
        exercise_actions = [
            a for a in actions
            if a.type == "exercise"
        ]

        # Limit to 1 exercise recommendation
        return exercise_actions[:1]
