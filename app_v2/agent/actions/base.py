"""
Base classes for the actions system.

Defines the Action schema and ActionHandler abstract base class.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class Action(BaseModel):
    """
    Universal action schema.

    Flexible structure that can represent any action type.
    The metadata dict allows type-specific data.
    """

    type: str
    """Action type identifier (e.g., 'learning', 'exercise', 'journal')."""

    id: str
    """Unique identifier for this action."""

    label: str
    """User-facing label to display."""

    metadata: Optional[Dict[str, Any]] = {}
    """
    Flexible metadata for type-specific data.

    Common fields:
    - duration: str (e.g., "5 min")
    - contentType: str (e.g., "audio_exercise", "audio_article")
    - category: str (e.g., "breathing", "leadership")
    """

    class Config:
        extra = "allow"


class ActionHandler(ABC):
    """
    Abstract base class for action type handlers.

    Each handler is responsible for generating actions of a specific type.
    Handlers are registered with ActionRegistry and called by ActionGenerator.
    """

    @property
    @abstractmethod
    def action_type(self) -> str:
        """
        Unique identifier for this action type.

        Returns:
            Type string (e.g., 'learning', 'exercise')
        """
        pass

    @abstractmethod
    async def generate(
        self,
        topics: List[str],
        language: str,
        context: Dict[str, Any]
    ) -> List[Action]:
        """
        Generate actions of this type based on detected topics.

        Args:
            topics: List of detected topic strings
            language: Language code ('en' or 'sv')
            context: Additional context (user_id, conversation_id, etc.)

        Returns:
            List of Action objects
        """
        pass
