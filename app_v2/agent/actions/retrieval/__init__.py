"""
Retrieval subsystem for actions.

Provides interfaces and implementations for retrieving relevant content.
"""

from .base import ActionRetriever
from .static import StaticRetriever

__all__ = [
    "ActionRetriever",
    "StaticRetriever",
]
