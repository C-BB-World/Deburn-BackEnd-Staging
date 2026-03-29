"""
Action generator orchestrator.

Coordinates topic detection and action generation across all handlers.
"""

from typing import List, Dict, Any, Optional

from .base import Action
from .registry import ActionRegistry
from .topic_detector import TopicDetector


class ActionGenerator:
    """
    Orchestrates action generation across all registered handlers.

    Detects topics from user messages and delegates to appropriate
    handlers to generate actions.
    """

    def __init__(
        self,
        registry: ActionRegistry,
        topic_detector: TopicDetector
    ):
        """
        Initialize ActionGenerator.

        Args:
            registry: ActionRegistry with registered handlers
            topic_detector: TopicDetector for extracting topics
        """
        self._registry = registry
        self._topic_detector = topic_detector

    async def generate(
        self,
        message: str,
        language: str,
        context: Optional[Dict[str, Any]] = None,
        action_types: Optional[List[str]] = None
    ) -> List[Action]:
        """
        Generate actions for a user message.

        1. Detects topics from message
        2. Gets all (or filtered) handlers
        3. Collects actions from each handler

        Args:
            message: User message to analyze
            language: Language code ('en' or 'sv')
            context: Additional context (user_id, etc.)
            action_types: Filter to specific action types (optional)

        Returns:
            List of Action objects from all handlers
        """
        context = context or {}

        # Detect topics from message
        topics = self._topic_detector.detect(message)

        # No topics = no actions
        if not topics:
            return []

        # Get handlers
        handlers = self._registry.all_handlers()

        # Filter to specific types if requested
        if action_types:
            handlers = [
                h for h in handlers
                if h.action_type in action_types
            ]

        # Generate actions from each handler
        actions: List[Action] = []
        for handler in handlers:
            handler_actions = await handler.generate(topics, language, context)
            actions.extend(handler_actions)

        return actions

    async def generate_for_topics(
        self,
        topics: List[str],
        language: str,
        context: Optional[Dict[str, Any]] = None,
        action_types: Optional[List[str]] = None
    ) -> List[Action]:
        """
        Generate actions for pre-detected topics.

        Use this when topics are already known.

        Args:
            topics: List of topic strings
            language: Language code ('en' or 'sv')
            context: Additional context
            action_types: Filter to specific action types

        Returns:
            List of Action objects
        """
        context = context or {}

        if not topics:
            return []

        handlers = self._registry.all_handlers()

        if action_types:
            handlers = [
                h for h in handlers
                if h.action_type in action_types
            ]

        actions: List[Action] = []
        for handler in handlers:
            handler_actions = await handler.generate(topics, language, context)
            actions.extend(handler_actions)

        return actions
