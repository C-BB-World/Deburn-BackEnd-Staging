## API Description

Endpoints for learning content and audio streaming.

---

## GET /api/learning/content

Fetches list of available learning content items with availability status.

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "679abc123def456789012345",
        "contentType": "text_article",
        "category": "leadership",
        "titleEn": "Time Ninja: Mastering Your Schedule",
        "titleSv": "Tidsninja: Bemästra ditt schema",
        "lengthMinutes": 5,
        "audioFileEn": null,
        "audioFileSv": null,
        "textContentEn": "Full article text here...",
        "textContentSv": "Fullständig artikeltext här...",
        "videoUrl": null,
        "videoEmbedCode": null,
        "videoAvailableInEn": true,
        "videoAvailableInSv": true,
        "purpose": "Learn effective time management techniques",
        "sortOrder": 1,
        "hasContent": true
      },
      {
        "id": "679abc123def456789012346",
        "contentType": "audio_article",
        "category": "meditation",
        "titleEn": "Breathing Exercise",
        "titleSv": "Andningsövning",
        "lengthMinutes": 10,
        "audioFileEn": "/api/v2/hub/content/679abc123def456789012346/audio/en",
        "audioFileSv": "/api/v2/hub/content/679abc123def456789012346/audio/sv",
        "textContentEn": null,
        "textContentSv": null,
        "videoUrl": null,
        "videoEmbedCode": null,
        "videoAvailableInEn": true,
        "videoAvailableInSv": true,
        "purpose": "Guided breathing meditation",
        "sortOrder": 2,
        "hasContent": true
      }
    ]
  }
}
```

---

## GET /api/learning/content/{content_id}/audio/{language}

Streams audio content for the frontend player.

**Parameters:**
- `content_id` (path): Content item ID (MongoDB ObjectId string)
- `language` (path): Language code (`en` or `sv`)

**Response:**
- Content-Type: `audio/mpeg` (or actual MIME type)
- Binary audio data

**Errors:**
- `400`: Invalid language (must be 'en' or 'sv')
- `404`: Audio not found

---

## Content Types

- `text_article` - Text-based article content
- `audio_article` - Audio content (guided meditations, etc.)
- `audio_exercise` - Interactive audio exercise
- `video_link` - External video link

---

## Categories

- `featured` - Featured content
- `leadership` - Leadership skills
- `breath` - Breath techniques
- `meditation` - Meditation practices
- `burnout` - Burnout prevention
- `wellbeing` - General wellbeing
- `other` - Other content

---

## hasContent Field

The `hasContent` boolean field indicates whether the content item has actual content available:

- `text_article`: `true` if `textContentEn` is not empty
- `audio_article` / `audio_exercise`: `true` if `audioFileEn` exists
- `video_link`: `true` if `videoUrl` exists

Frontend uses this to grey out unavailable content cards.
