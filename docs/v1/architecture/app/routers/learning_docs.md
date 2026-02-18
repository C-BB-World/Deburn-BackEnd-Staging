# Learning Router

Learning content and article endpoints.

---

## Endpoints

### GET /api/learning/content

- **Inputs:**
  - Header: Authorization (Bearer token)
- **Outputs:** (dict) `{ success, data: { items: [...] } }`
- **Description:** Get published learning content items with:
  - id: Content item ID (ObjectId as string)
  - contentType: `text_article`, `audio_article`, `audio_exercise`, `video_link`
  - category: `featured`, `leadership`, `breath`, `meditation`, `burnout`, `wellbeing`, `other`
  - titleEn/titleSv: Localized titles
  - lengthMinutes: Duration
  - textContentEn/textContentSv: Article text (for text_article)
  - audioFileEn/audioFileSv: Audio URLs
  - videoUrl/videoEmbedCode: Video data
  - hasContent: Computed availability flag
  - hasImage/hasImageEn/hasImageSv: Image availability flags

### GET /api/learning/content/{content_id}

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Path: content_id (ObjectId string)
- **Outputs:** (dict) `{ success, data: { item: {...} } }`
- **Description:** Get single content item by ID
- **Errors:**
  - 400: Invalid content ID format
  - 404: Content not found

### GET /api/learning/content/{content_id}/audio/{language}

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Path: content_id (ObjectId string), language (`en` or `sv`)
- **Outputs:** Binary audio data with Content-Type header
- **Description:** Stream audio content for playback
- **Errors:**
  - 400: Invalid language
  - 404: Audio not found

---

## Article Image Router

Separate router mounted at `/api/article-image`.

### GET /api/article-image/{content_id}/{language}

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Path: content_id (ObjectId string), language (`en` or `sv`)
- **Outputs:** Binary image data with Content-Type header
- **Headers:**
  - Content-Type: Image MIME type
  - Cache-Control: public, max-age=86400
- **Description:** Fetch article image for content item
- **Fallback:** Swedish requests fall back to English image if Swedish not available
- **Errors:**
  - 400: Invalid content ID or language
  - 404: Content not found or no image

---

## Helper Functions

### _compute_has_content(item: dict) -> bool

Computes whether content is available based on type:
- `text_article`: Returns `True` if `textContentEn` is not empty
- `audio_article` / `audio_exercise`: Returns `True` if `audioFileEn` exists
- `video_link`: Returns `True` if `videoUrl` exists

---

## Database Projections

Binary data fields are excluded from list queries for performance:
- `audioDataEn`
- `audioDataSv`
- `articleImageEn`
- `articleImageSv`

---

## Files

- `app_v2/routers/learning.py` - Main router and article_image_router
- `app_v2/services/content/content_service.py` - ContentService class
