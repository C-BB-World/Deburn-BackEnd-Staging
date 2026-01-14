"""
FastAPI dependencies for Progress system.

Provides dependency injection for progress-related services.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.progress.services.stats_service import ProgressStatsService
from app_v2.progress.services.insight_service import InsightService
from app_v2.progress.services.insight_engine import InsightEngine
from app_v2.ai.services.pattern_detector import PatternDetector


_stats_service: Optional[ProgressStatsService] = None
_insight_service: Optional[InsightService] = None
_insight_engine: Optional[InsightEngine] = None


def init_progress_services(
    db: AsyncIOMotorDatabase,
    pattern_detector: Optional[PatternDetector] = None,
    agent=None
) -> None:
    """
    Initialize progress services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
        pattern_detector: Pattern detector from AI system
        agent: Optional AI agent for enhancement
    """
    global _stats_service, _insight_service, _insight_engine

    _stats_service = ProgressStatsService(db=db)
    _insight_service = InsightService(db=db)

    if pattern_detector is None:
        pattern_detector = PatternDetector(db=db)

    _insight_engine = InsightEngine(
        db=db,
        insight_service=_insight_service,
        pattern_detector=pattern_detector,
        agent=agent
    )


def get_stats_service() -> ProgressStatsService:
    """Get progress stats service instance."""
    if _stats_service is None:
        raise RuntimeError("Progress services not initialized.")
    return _stats_service


def get_insight_service() -> InsightService:
    """Get insight service instance."""
    if _insight_service is None:
        raise RuntimeError("Progress services not initialized.")
    return _insight_service


def get_insight_engine() -> InsightEngine:
    """Get insight engine instance."""
    if _insight_engine is None:
        raise RuntimeError("Progress services not initialized.")
    return _insight_engine
