"""
Learning action handler.

Generates learning module recommendations based on topics.
"""

from typing import List, Dict, Any

from ..base import Action, ActionHandler
from ..retrieval.base import ActionRetriever


class LearningHandler(ActionHandler):
    """
    Handles learning/module action recommendations.

    Uses an ActionRetriever to find relevant learning content
    based on detected topics.
    """

    def __init__(self, retriever: ActionRetriever):
        """
        Initialize LearningHandler.

        Args:
            retriever: ActionRetriever to use for content lookup
        """
        self._retriever = retriever

    @property
    def action_type(self) -> str:
        """Return action type identifier."""
        return "learning"

    async def generate(
        self,
        topics: List[str],
        language: str,
        context: Dict[str, Any]
    ) -> List[Action]:
        """
        Generate learning recommendations.

        Retrieves actions and filters to learning type only.

        Args:
            topics: List of detected topic strings
            language: Language code ('en' or 'sv')
            context: Additional context

        Returns:
            List of learning Action objects
        """
        actions = await self._retriever.retrieve(topics, language, limit=4)

        # Filter to learning type only
        learning_actions = [
            a for a in actions
            if a.type == "learning"
        ]

        # Limit to 2 learning recommendations
        return learning_actions[:2]
