"""
Deburn FastAPI Application v2

Main entry point for the Deburn API v2.
Uses the refactored app_v2/ structure with SOLID principles.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Common library imports
from common.database import MongoDB
from common.utils import success_response

# App-specific imports
from app_v1.config import settings  # Shared settings

# Import routers
from app_v2.routers import (
    auth_router,
    user_router,
    i18n_router,
    checkin_router,
    circles_router,
    calendar_router,
    content_router,
    coach_router,
    progress_router,
    media_router,
    organization_router,
    hub_router,
)

# Import service initialization
from app_v2.dependencies import init_all_services


# =============================================================================
# Database Instances
# =============================================================================
# Main database for user data, check-ins, etc.
main_db = MongoDB()

# Hub database for admin/organization management
hub_db = MongoDB()


# =============================================================================
# Application Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown tasks like database connections
    and service initialization.
    """
    # Startup
    print("Starting Deburn API v2...")

    # Connect to main database
    await main_db.connect(
        uri=settings.MONGODB_URI,
        database_name=settings.MONGODB_DATABASE,
        document_models=[],
    )
    print(f"Connected to main database: {settings.MONGODB_DATABASE}")

    # Connect to hub database (if different from main)
    hub_uri = settings.HUB_MONGODB_URI or settings.MONGODB_URI
    hub_db_name = settings.HUB_MONGODB_DATABASE

    if hub_uri != settings.MONGODB_URI:
        await hub_db.connect(
            uri=hub_uri,
            database_name=hub_db_name,
            document_models=[],
        )
        print(f"Connected to hub database: {hub_db_name}")
        hub_db_instance = hub_db.db
    else:
        # Use main database for hub if not configured separately
        hub_db_instance = main_db.db

    # Initialize all services
    init_all_services(
        db=main_db.db,
        hub_db=hub_db_instance,
        firebase_credentials_path=settings.FIREBASE_CREDENTIALS_PATH if hasattr(settings, 'FIREBASE_CREDENTIALS_PATH') else None,
        geoip_database_path=settings.GEOIP_DATABASE_PATH if hasattr(settings, 'GEOIP_DATABASE_PATH') else None,
    )
    print("All services initialized successfully!")

    print("Deburn API v2 started successfully!")

    yield

    # Shutdown
    print("Shutting down Deburn API v2...")
    await main_db.disconnect()
    if hub_db.is_connected:
        await hub_db.disconnect()
    print("Deburn API v2 shut down complete.")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="Deburn API v2",
    description="AI-powered personal development and coaching platform - Refactored",
    version="2.0.0",
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
# Include Routers (all under /api/v2 prefix)
# =============================================================================
API_PREFIX = "/api/v2"

app.include_router(auth_router, prefix=API_PREFIX, tags=["Authentication"])
app.include_router(user_router, prefix=API_PREFIX, tags=["User"])
app.include_router(i18n_router, prefix=API_PREFIX, tags=["i18n"])
app.include_router(checkin_router, prefix=API_PREFIX, tags=["Check-in"])
app.include_router(circles_router, prefix=API_PREFIX, tags=["Circles"])
app.include_router(calendar_router, prefix=API_PREFIX, tags=["Calendar"])
app.include_router(content_router, prefix=API_PREFIX, tags=["Learning"])
app.include_router(coach_router, prefix=API_PREFIX, tags=["Coach"])
app.include_router(progress_router, prefix=API_PREFIX, tags=["Progress"])
app.include_router(media_router, prefix=API_PREFIX, tags=["Media"])
app.include_router(organization_router, prefix=API_PREFIX, tags=["Organizations"])
app.include_router(hub_router, prefix=API_PREFIX, tags=["Hub"])


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
        "version": "2.0.0",
        "database": main_db.is_connected,
        "hub_database": hub_db.is_connected if hub_db.is_connected else main_db.is_connected,
    })


# =============================================================================
# Run with Uvicorn
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_v2:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development(),
    )
