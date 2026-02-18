"""
BrainBank API Routers.

All routers are imported here for easy access from api.py.
"""

from app_v1.routers.auth import router as auth_router
from app_v1.routers.admin import router as admin_router
from app_v1.routers.checkin import router as checkin_router
from app_v1.routers.circles import router as circles_router
from app_v1.routers.coach import router as coach_router
from app_v1.routers.dashboard import router as dashboard_router
from app_v1.routers.hub import router as hub_router
from app_v1.routers.learning import router as learning_router
from app_v1.routers.profile import router as profile_router
from app_v1.routers.progress import router as progress_router

__all__ = [
    "auth_router",
    "admin_router",
    "checkin_router",
    "circles_router",
    "coach_router",
    "dashboard_router",
    "hub_router",
    "learning_router",
    "profile_router",
    "progress_router",
]
