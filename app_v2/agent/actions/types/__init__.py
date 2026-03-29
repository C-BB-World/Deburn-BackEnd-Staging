"""
Action type handlers.

Each handler is responsible for generating actions of a specific type.
"""

from .learning import LearningHandler
from .exercise import ExerciseHandler

__all__ = [
    "LearningHandler",
    "ExerciseHandler",
]
