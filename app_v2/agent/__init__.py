"""
Agent system for AI coaching operations.

Provides the Agent abstraction and Memory system for the coaching AI.
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
]
