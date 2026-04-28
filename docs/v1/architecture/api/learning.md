## API Description

Endpoints for learning modules and content management.

---

## GET /api/learning/content

Fetches list of available learning content items.

**Request:**
No request body. Requires authentication.

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "679abc123...",
        "contentType": "text_article",
        "category": "leadership",
        "titleEn": "Article Title",
        "titleSv": "Artikelrubrik",
        "lengthMinutes": 5,
        "audioFileEn": null,
        "audioFileSv": null,
        "textContentEn": "Full article text...",
        "textContentSv": "Fullständig artikeltext...",
        "videoUrl": null,
        "videoEmbedCode": null,
        "videoAvailableInEn": true,
        "videoAvailableInSv": true,
        "purpose": "Description of the content purpose",
        "sortOrder": 1,
        "hasContent": true,
        "hasImage": true,
        "hasImageEn": true,
        "hasImageSv": true
      }
    ]
  }
}
```

---

## GET /api/learning/content/{content_id}

Fetches a single content item by ID.

**Path Parameters:**
- `content_id` - Content item ObjectId

**Response:**
```json
{
  "success": true,
  "data": {
    "item": {
      "id": "679abc123...",
      "contentType": "text_article",
      "category": "leadership",
      "titleEn": "Article Title",
      "titleSv": "Artikelrubrik",
      "lengthMinutes": 5,
      "hasContent": true,
      "hasImage": true,
      "hasImageEn": true,
      "hasImageSv": true
    }
  }
}
```

**Error Responses:**
- `400` - Invalid content ID
- `404` - Content not found

---

## GET /api/learning/content/{content_id}/audio/{language}

Streams audio content for playback.

**Path Parameters:**
- `content_id` - Content item ObjectId
- `language` - `en` or `sv`

**Response:**
Binary audio data with appropriate `Content-Type` header.

**Headers:**
- `Content-Type` - Audio MIME type (e.g., `audio/mpeg`)
- `Content-Disposition: inline; filename=audio.mp3`
- `Accept-Ranges: bytes`

**Error Responses:**
- `400` - Invalid language
- `404` - Audio not found

---

## GET /api/article-image/{content_id}/{language}

Fetches article image for a content item.

**Path Parameters:**
- `content_id` - Content item ObjectId
- `language` - `en` or `sv`

**Response:**
Binary image data with appropriate `Content-Type` header.

**Headers:**
- `Content-Type` - Image MIME type (e.g., `image/jpeg`, `image/png`)
- `Cache-Control: public, max-age=86400`

**Fallback Behavior:**
- Swedish (`sv`) falls back to English image if not available
- Returns `404` if no image exists

**Error Responses:**
- `400` - Invalid content ID or language
- `404` - Content not found or no image available

---

## Database Schema

**Collection:** `contentitems`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Content item ID |
| `contentType` | String | `text_article`, `audio_article`, `audio_exercise`, `video_link` |
| `category` | String | `featured`, `leadership`, `breath`, `meditation`, `burnout`, `wellbeing`, `other` |
| `status` | String | `draft`, `in_review`, `published`, `archived` |
| `titleEn` | String | English title |
| `titleSv` | String | Swedish title |
| `textContentEn` | String | English article text |
| `textContentSv` | String | Swedish article text |
| `audioFileEn` | String | English audio URL |
| `audioFileSv` | String | Swedish audio URL |
| `audioDataEn` | Binary | English audio binary data |
| `audioDataSv` | Binary | Swedish audio binary data |
| `audioMimeTypeEn` | String | English audio MIME type |
| `audioMimeTypeSv` | String | Swedish audio MIME type |
| `articleImageEn` | Binary | English article image |
| `articleImageSv` | Binary | Swedish article image |
| `articleImageMimeType` | String | Shared MIME type for article images |
| `videoUrl` | String | Video URL |
| `videoEmbedCode` | String | Video embed code |
| `videoAvailableInEn` | Boolean | Video available in English |
| `videoAvailableInSv` | Boolean | Video available in Swedish |
| `lengthMinutes` | Number | Duration in minutes |
| `purpose` | String | Content purpose description |
| `sortOrder` | Number | Sort order |
| `coachEnabled` | Boolean | Available for coach recommendations |
| `coachTopics` | Array | Topics for coach matching |
| `coachPriority` | Number | Priority for coach recommendations |
| `createdAt` | Date | Creation timestamp |
| `updatedAt` | Date | Last update timestamp |

---

## Content Types

| Type | Description |
|------|-------------|
| `text_article` | Text-based article content |
| `audio_article` | Audio narrated article |
| `audio_exercise` | Guided audio exercise |
| `video_link` | Video content |

---

## Categories

| Category | Description |
|----------|-------------|
| `featured` | Featured/highlighted content |
| `leadership` | Leadership skills |
| `breath` | Breathing exercises |
| `meditation` | Meditation content |
| `burnout` | Burnout prevention/recovery |
| `wellbeing` | General wellbeing |
| `other` | Other content |

---

## Computed Fields

### hasContent

Computed based on content type:
- `text_article`: `true` if `textContentEn` is not empty
- `audio_article` / `audio_exercise`: `true` if `audioFileEn` exists
- `video_link`: `true` if `videoUrl` exists

### hasImage / hasImageEn / hasImageSv

All `true` if `articleImageMimeType` field exists. Currently uses single image for both languages with Swedish falling back to English.
