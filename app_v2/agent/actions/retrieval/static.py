"""
Static retriever using hardcoded knowledge.

Uses the Knowledge store for fallback actions.
"""

from typing import List

from ..base import Action
from .base import ActionRetriever
from app_v2.agent.memory.knowledge import Knowledge, get_knowledge


class StaticRetriever(ActionRetriever):
    """
    Retrieves actions from static knowledge store.

    Uses hardcoded fallback actions from memory/knowledge.py.
    This is the default retriever until RAG is implemented.
    """

    def __init__(self, knowledge: Knowledge | None = None):
        """
        Initialize StaticRetriever.

        Args:
            knowledge: Knowledge instance (uses singleton if not provided)
        """
        self._knowledge = knowledge or get_knowledge()

    async def retrieve(
        self,
        topics: List[str],
        language: str,
        limit: int = 2
    ) -> List[Action]:
        """
        Retrieve fallback actions for topics.

        Args:
            topics: List of detected topic strings
            language: Language code ('en' or 'sv')
            limit: Maximum number of actions to return

        Returns:
            List of Action objects
        """
        actions: List[Action] = []
        seen_ids: set[str] = set()

        for topic in topics:
            fallbacks = self._knowledge.get_fallback_actions(topic, language)
            for action_dict in fallbacks:
                # Avoid duplicates
                if action_dict["id"] not in seen_ids:
                    seen_ids.add(action_dict["id"])
                    actions.append(Action(**action_dict))

                if len(actions) >= limit:
                    return actions

        return actions
