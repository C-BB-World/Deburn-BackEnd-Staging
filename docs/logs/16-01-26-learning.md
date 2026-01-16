# Session Log - 16/01/26

## Learning Content Availability & Audio Streaming

Updated the learning modules endpoint to support content availability detection and added audio streaming for the frontend player.

---

## Changes to `app_v2/routers/learning.py`

### Added `_compute_has_content()` function

Determines if a content item has actual content available based on its type:

- `text_article`: Returns `true` if `textContentEn` exists and is not empty
- `audio_article` / `audio_exercise`: Returns `true` if `audioFileEn` exists (streaming URL set when audio uploaded)
- `video_link`: Returns `true` if `videoUrl` exists

This allows the frontend to grey out cards that don't have content yet.

### Updated `GET /api/learning/modules` response

Added new fields to each module in the response:

| Field | Type | Description |
|-------|------|-------------|
| `hasContent` | boolean | Whether content is available (false = grey out) |
| `category` | string | Content category (featured, leadership, breath, meditation, etc.) |
| `contentType` | string | Original content type (text_article, audio_article, etc.) |
| `textContent` | string | Full article text (only for text_article with content) |
| `audioUrl` | string | Streaming endpoint URL (only for audio types with content) |

### Added `GET /api/learning/content/{content_id}/audio/{language}` endpoint

New endpoint to stream audio content for the frontend player:

- Accepts `content_id` and `language` ('en' or 'sv') parameters
- Returns audio binary data with appropriate `Content-Type` header
- Reuses `HubContentService.get_audio()` for data retrieval
- Returns 404 if audio not found, 400 if invalid language

---

## Data Source

Content is loaded from the `deburn-hub` database, `contentitems` collection (shared with deburnalpha).
