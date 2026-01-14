"""
FastAPI dependencies for AI Coaching system.

Provides dependency injection for coaching-related services.
"""

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.ai.services.agent import Agent
from app_v2.ai.services.claude_agent import ClaudeAgent
from app_v2.ai.services.safety_checker import SafetyChecker
from app_v2.ai.services.conversation_service import ConversationService
from app_v2.ai.services.commitment_service import CommitmentService
from app_v2.ai.services.commitment_extractor import CommitmentExtractor
from app_v2.ai.services.quick_reply_generator import QuickReplyGenerator
from app_v2.ai.services.coach_service import CoachService
from app_v2.ai.services.pattern_detector import PatternDetector


_agent: Optional[Agent] = None
_safety_checker: Optional[SafetyChecker] = None
_conversation_service: Optional[ConversationService] = None
_commitment_service: Optional[CommitmentService] = None
_commitment_extractor: Optional[CommitmentExtractor] = None
_quick_reply_generator: Optional[QuickReplyGenerator] = None
_coach_service: Optional[CoachService] = None
_pattern_detector: Optional[PatternDetector] = None


def init_ai_services(db: AsyncIOMotorDatabase) -> None:
    """
    Initialize AI coaching services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
    """
    global _agent, _safety_checker, _conversation_service, _commitment_service
    global _commitment_extractor, _quick_reply_generator, _coach_service, _pattern_detector

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("AGENT_MODEL", "claude-sonnet-4-5-20250514")
    max_tokens = int(os.getenv("AGENT_MAX_TOKENS", "1024"))
    daily_limit = int(os.getenv("COACH_DAILY_LIMIT", "15"))

    if api_key:
        _agent = ClaudeAgent(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens
        )
    else:
        _agent = None

    _safety_checker = SafetyChecker()
    _conversation_service = ConversationService(db=db)
    _commitment_service = CommitmentService(db=db)
    _commitment_extractor = CommitmentExtractor()
    _quick_reply_generator = QuickReplyGenerator()
    _pattern_detector = PatternDetector(db=db)

    if _agent:
        _coach_service = CoachService(
            agent=_agent,
            safety_checker=_safety_checker,
            conversation_service=_conversation_service,
            commitment_service=_commitment_service,
            commitment_extractor=_commitment_extractor,
            quick_reply_generator=_quick_reply_generator,
            db=db,
            daily_limit=daily_limit
        )


def get_agent() -> Agent:
    """Get AI agent instance."""
    if _agent is None:
        raise RuntimeError("AI agent not initialized. Check ANTHROPIC_API_KEY.")
    return _agent


def get_safety_checker() -> SafetyChecker:
    """Get safety checker instance."""
    if _safety_checker is None:
        raise RuntimeError("AI services not initialized.")
    return _safety_checker


def get_conversation_service() -> ConversationService:
    """Get conversation service instance."""
    if _conversation_service is None:
        raise RuntimeError("AI services not initialized.")
    return _conversation_service


def get_commitment_service() -> CommitmentService:
    """Get commitment service instance."""
    if _commitment_service is None:
        raise RuntimeError("AI services not initialized.")
    return _commitment_service


def get_coach_service() -> CoachService:
    """Get coach service instance."""
    if _coach_service is None:
        raise RuntimeError("AI services not initialized. Check ANTHROPIC_API_KEY.")
    return _coach_service


def get_pattern_detector() -> PatternDetector:
    """Get pattern detector instance."""
    if _pattern_detector is None:
        raise RuntimeError("AI services not initialized.")
    return _pattern_detector
