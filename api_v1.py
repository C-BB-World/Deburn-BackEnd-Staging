"""
BrainBank FastAPI Application

Main entry point for the BrainBank API.
Uses the generic common/ library for infrastructure and app/ for business logic.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Common library imports
from common.database import MongoDB
from common.i18n import I18nService
from common.utils import success_response

# App-specific imports
from app_v1.config import settings
from app_v1.models import User, CheckIn, Organization

# Import routers
from app_v1.routers import (
    auth_router,
    admin_router,
    checkin_router,
    circles_router,
    coach_router,
    dashboard_router,
    hub_router,
    learning_router,
    profile_router,
    progress_router,
)

# =============================================================================
# Database Instances
# =============================================================================
# Main database for user data, check-ins, etc.
main_db = MongoDB()

# Hub database for admin/organization management (can be same as main)
hub_db = MongoDB()

# =============================================================================
# i18n Service
# =============================================================================
i18n = I18nService(
    locales_dir="app/locales",
    default_language=settings.DEFAULT_LANGUAGE,
    supported_languages=settings.get_supported_languages(),
)


# =============================================================================
# Application Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown tasks like database connections.
    """
    # Startup
    print("Starting BrainBank API...")

    # Connect to main database
    await main_db.connect(
        uri=settings.MONGODB_URI,
        database_name=settings.MONGODB_DATABASE,
        document_models=[User, CheckIn, Organization],
    )
    print(f"Connected to main database: {settings.MONGODB_DATABASE}")

    # Connect to hub database (if different from main)
    if settings.HUB_MONGODB_URI and settings.HUB_MONGODB_URI != settings.MONGODB_URI:
        await hub_db.connect(
            uri=settings.HUB_MONGODB_URI,
            database_name=settings.HUB_MONGODB_DATABASE,
            document_models=[],  # Hub models can be added here
        )
        print(f"Connected to hub database: {settings.HUB_MONGODB_DATABASE}")

    print(f"Loaded languages: {i18n.get_languages()}")
    print("BrainBank API started successfully!")

    yield

    # Shutdown
    print("Shutting down BrainBank API...")
    await main_db.disconnect()
    if hub_db.is_connected:
        await hub_db.disconnect()
    print("BrainBank API shut down complete.")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="BrainBank API",
    description="AI-powered personal development and coaching platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development() else None,
    redoc_url="/redoc" if settings.is_development() else None,
)

# =============================================================================
# CORS Middleware
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Include Routers
# =============================================================================
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(checkin_router, prefix="/api/checkin", tags=["Check-in"])
app.include_router(circles_router, prefix="/api/circles", tags=["Circles"])
app.include_router(coach_router, prefix="/api/coach", tags=["Coach"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(hub_router, prefix="/api/hub", tags=["Hub"])
app.include_router(learning_router, prefix="/api/learning", tags=["Learning"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(progress_router, prefix="/api/progress", tags=["Progress"])


# =============================================================================
# Health Check Endpoint
# =============================================================================
@app.get("/health", tags=["Health"])
async def health():
    """
    Health check endpoint.

    Returns the status of the API and database connections.
    """
    return success_response({
        "status": "ok",
        "database": main_db.is_connected,
        "hub_database": hub_db.is_connected,
    })


# =============================================================================
# Run with Uvicorn
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development(),
    )
