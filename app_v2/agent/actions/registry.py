"""
Action registry for pluggable action handlers.

Allows dynamic registration and retrieval of action handlers.
"""

from typing import Dict, List, Optional

from .base import ActionHandler


class ActionRegistry:
    """
    Registry for pluggable action handlers.

    Handlers are registered by their action_type property and can be
    retrieved individually or as a complete list.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._handlers: Dict[str, ActionHandler] = {}

    def register(self, handler: ActionHandler) -> None:
        """
        Register an action handler.

        Args:
            handler: ActionHandler instance to register

        Raises:
            ValueError: If handler with same type already registered
        """
        action_type = handler.action_type
        if action_type in self._handlers:
            raise ValueError(
                f"Handler for action type '{action_type}' already registered"
            )
        self._handlers[action_type] = handler

    def unregister(self, action_type: str) -> None:
        """
        Remove an action handler.

        Args:
            action_type: Type string to unregister
        """
        self._handlers.pop(action_type, None)

    def get(self, action_type: str) -> Optional[ActionHandler]:
        """
        Get handler by type.

        Args:
            action_type: Type string to look up

        Returns:
            ActionHandler or None if not found
        """
        return self._handlers.get(action_type)

    def all_handlers(self) -> List[ActionHandler]:
        """
        Get all registered handlers.

        Returns:
            List of all ActionHandler instances
        """
        return list(self._handlers.values())

    def all_types(self) -> List[str]:
        """
        Get all registered action types.

        Returns:
            List of type strings
        """
        return list(self._handlers.keys())

    def has(self, action_type: str) -> bool:
        """
        Check if handler is registered for type.

        Args:
            action_type: Type string to check

        Returns:
            True if handler exists
        """
        return action_type in self._handlers

    def clear(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()
