"""
Agent system for AI coaching operations.

Provides the Agent abstraction, Memory system, and Actions system for the coaching AI.
"""

from app_v2.agent.agent import Agent
from app_v2.agent.claude_agent import ClaudeAgent
from app_v2.agent.prompt_service import PromptService
from app_v2.agent.types import (
    CoachingContext,
    CheckinInsightContext,
    CheckinInsight,
    Message,
    Conversation,
    ConversationSummary,
)
from app_v2.agent.memory import (
    MemoryProvider,
    EncryptedMemory,
    MemoryEncryptionService,
)
from app_v2.agent.memory.knowledge import Knowledge, get_knowledge
from app_v2.agent.actions import (
    Action,
    ActionHandler,
    ActionRegistry,
    ActionGenerator,
    TopicDetector,
)
from app_v2.agent.actions.retrieval import ActionRetriever, StaticRetriever
from app_v2.agent.actions.types import LearningHandler, ExerciseHandler

__all__ = [
    # Agent
    "Agent",
    "ClaudeAgent",
    "PromptService",
    # Types
    "CoachingContext",
    "CheckinInsightContext",
    "CheckinInsight",
    "Message",
    "Conversation",
    "ConversationSummary",
    # Memory
    "MemoryProvider",
    "EncryptedMemory",
    "MemoryEncryptionService",
    "Knowledge",
    "get_knowledge",
    # Actions
    "Action",
    "ActionHandler",
    "ActionRegistry",
    "ActionGenerator",
    "TopicDetector",
    "ActionRetriever",
    "StaticRetriever",
    "LearningHandler",
    "ExerciseHandler",
]
