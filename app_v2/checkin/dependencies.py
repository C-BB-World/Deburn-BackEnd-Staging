"""
FastAPI dependencies for Check-in system.

Provides dependency injection for check-in-related services.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app_v2.checkin.services.checkin_service import CheckInService
from app_v2.checkin.services.checkin_analytics import CheckInAnalytics
from app_v2.checkin.services.insight_generator import InsightGenerator


_checkin_service: Optional[CheckInService] = None
_checkin_analytics: Optional[CheckInAnalytics] = None
_insight_generator: Optional[InsightGenerator] = None


def init_checkin_services(
    db: AsyncIOMotorDatabase,
    ai_client=None
) -> None:
    """
    Initialize check-in services with database connection.

    Called once at application startup.

    Args:
        db: MongoDB database connection
        ai_client: Optional AI client for insight generation
    """
    global _checkin_service, _checkin_analytics, _insight_generator

    _checkin_service = CheckInService(db=db)
    _checkin_analytics = CheckInAnalytics(checkin_service=_checkin_service)
    _insight_generator = InsightGenerator(
        ai_client=ai_client,
        checkin_service=_checkin_service
    )


def get_checkin_service() -> CheckInService:
    """Get check-in service instance."""
    if _checkin_service is None:
        raise RuntimeError("Check-in services not initialized. Call init_checkin_services first.")
    return _checkin_service


def get_checkin_analytics() -> CheckInAnalytics:
    """Get check-in analytics instance."""
    if _checkin_analytics is None:
        raise RuntimeError("Check-in services not initialized. Call init_checkin_services first.")
    return _checkin_analytics


def get_insight_generator() -> InsightGenerator:
    """Get insight generator instance."""
    if _insight_generator is None:
        raise RuntimeError("Check-in services not initialized. Call init_checkin_services first.")
    return _insight_generator
