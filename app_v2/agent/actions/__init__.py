"""
Actions module for AI agent.

Provides modular, pluggable action recommendations during coaching conversations.
"""

from .base import Action, ActionHandler
from .registry import ActionRegistry
from .generator import ActionGenerator
from .topic_detector import TopicDetector

__all__ = [
    "Action",
    "ActionHandler",
    "ActionRegistry",
    "ActionGenerator",
    "TopicDetector",
]
