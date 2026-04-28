# Session Log - 16/01/26 - Learning System

## Learning Content Router Fixes

Fixed the `/api/learning/content` endpoint not returning data.

### Issues Found

1. **Route conflict**: Both `content_router` and `learning_router` defined `GET /api/learning/content`. Since `content_router` was registered first in `api_v2.py`, it shadowed `learning_router`.

2. **ContentService collection name**: `ContentService` used `db["contentItems"]` (camelCase) but MongoDB collection is `contentitems` (lowercase).

3. **Wrong database**: `learning.py` was using main `deburn` database but content lives in `deburn-hub` database.

### Fixes Applied

**`api_v2.py`**
- Removed `content_router` import and registration
- `learning_router` now handles all `/api/learning` endpoints

**`app_v2/services/content/content_service.py`**
- Fixed collection name from `contentItems` to `contentitems`

**`app_v2/routers/learning.py`**
- Changed from `get_main_db()` to `get_hub_db()` to use `deburn-hub` database
- Removed all comments

**`app_v2/dependencies.py`**
- Added `get_hub_db()` function to expose hub database

---

## API Endpoints

### GET /api/learning/content

Returns list of published content items.

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "...",
        "contentType": "text_article",
        "category": "leadership",
        "titleEn": "...",
        "titleSv": "...",
        "lengthMinutes": 5,
        "hasContent": true
      }
    ]
  }
}
```

### GET /api/learning/content/{content_id}/audio/{language}

Streams audio binary data with Authorization header required.

**Path Parameters:**
- `content_id` - Content item ID
- `language` - `en` or `sv`

**Response:**
- Binary audio data
- `Content-Type: audio/mpeg`

---

## Database

Content is loaded from `deburn-hub` database, `contentitems` collection.

Audio data is stored as BSON Binary in `audioDataEn` and `audioDataSv` fields.
