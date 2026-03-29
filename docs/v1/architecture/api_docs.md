# api.py

BrainBank FastAPI application main entry point.

---

## Module Variables

### main_db

- **Type:** MongoDB
- **Description:** Main database instance for user data, check-ins, etc.

### hub_db

- **Type:** MongoDB
- **Description:** Hub database instance for admin/organization management (can be same as main).

### i18n

- **Type:** I18nService
- **Description:** Internationalization service instance loaded from app/locales.

### app

- **Type:** FastAPI
- **Description:** FastAPI application instance.

---

## Functions

### lifespan

- **Inputs:**
  - `app` (FastAPI): FastAPI application instance
- **Outputs:** (AsyncContextManager) Lifespan context manager
- **Description:** Application lifespan context manager. Handles startup (database connections, logging) and shutdown (disconnect databases).

---

## Application Configuration

### FastAPI Settings

- **title:** "BrainBank API"
- **description:** "AI-powered personal development and coaching platform"
- **version:** "1.0.0"
- **docs_url:** "/docs" (development only)
- **redoc_url:** "/redoc" (development only)

### CORS Middleware

- **allow_origins:** From settings.get_cors_origins()
- **allow_credentials:** From settings.CORS_ALLOW_CREDENTIALS
- **allow_methods:** ["*"]
- **allow_headers:** ["*"]

---

## Routers

| Router | Prefix | Tags |
|--------|--------|------|
| auth_router | /api/auth | Authentication |
| admin_router | /api/admin | Admin |
| checkin_router | /api/checkin | Check-in |
| circles_router | /api/circles | Circles |
| coach_router | /api/coach | Coach |
| dashboard_router | /api/dashboard | Dashboard |
| hub_router | /api/hub | Hub |
| learning_router | /api/learning | Learning |
| profile_router | /api/profile | Profile |
| progress_router | /api/progress | Progress |

---

## Endpoints

### GET /health

- **Inputs:** None
- **Outputs:** (dict) {status: "ok", database: bool, hub_database: bool}
- **Description:** Health check endpoint. Returns status of API and database connections.

---

## Running the Application

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development(),
    )
```

Or via command line:
```bash
uvicorn api:app --reload --port 8000
```
