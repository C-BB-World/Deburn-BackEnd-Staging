"""
Deburn API Routers.

All routers are imported here for easy access.
"""

from app_v2.routers.auth import router as auth_router
from app_v2.routers.user import router as user_router
from app_v2.routers.i18n import router as i18n_router
from app_v2.routers.checkin import router as checkin_router
from app_v2.routers.circles import router as circles_router
from app_v2.routers.calendar import router as calendar_router
from app_v2.routers.content import router as content_router
from app_v2.routers.coach import router as coach_router
from app_v2.routers.progress import router as progress_router
from app_v2.routers.media import router as media_router
from app_v2.routers.organization import router as organization_router
from app_v2.routers.hub import router as hub_router
from app_v2.routers.dashboard import router as dashboard_router
from app_v2.routers.admin import router as admin_router
from app_v2.routers.learning import router as learning_router
from app_v2.routers.profile import router as profile_router
from app_v2.routers.conversations import router as conversations_router
from app_v2.routers.feedback import router as feedback_router

__all__ = [
    "auth_router",
    "user_router",
    "i18n_router",
    "checkin_router",
    "circles_router",
    "calendar_router",
    "content_router",
    "coach_router",
    "progress_router",
    "media_router",
    "organization_router",
    "hub_router",
    "dashboard_router",
    "admin_router",
    "learning_router",
    "profile_router",
    "conversations_router",
    "feedback_router",
]
