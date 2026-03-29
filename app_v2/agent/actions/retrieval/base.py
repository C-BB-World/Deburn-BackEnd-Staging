"""
Abstract base class for action retrieval.

Designed for easy RAG integration in the future.
"""

from abc import ABC, abstractmethod
from typing import List

from ..base import Action


class ActionRetriever(ABC):
    """
    Abstract interface for action retrieval.

    Implementations can use static data, database queries,
    or vector search (RAG) to retrieve relevant actions.
    """

    @abstractmethod
    async def retrieve(
        self,
        topics: List[str],
        language: str,
        limit: int = 2
    ) -> List[Action]:
        """
        Retrieve relevant actions for given topics.

        Args:
            topics: List of detected topic strings
            language: Language code ('en' or 'sv')
            limit: Maximum number of actions to return

        Returns:
            List of Action objects
        """
        pass
