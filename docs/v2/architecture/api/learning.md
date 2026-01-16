## API Description

Endpoints for learning content and audio streaming.

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
        "hasContent": true
      }
    ]
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    items: Array<{
      id: string,                    // Content item ID
      contentType: string,           // "text_article" | "audio_article" | "audio_exercise" | "video_link"
      category: string,              // "featured" | "leadership" | "breath" | "meditation" | "burnout" | "wellbeing" | "other"
      titleEn: string,               // English title
      titleSv: string,               // Swedish title
      lengthMinutes: number,         // Duration in minutes
      audioFileEn: string | null,    // Audio streaming URL (English)
      audioFileSv: string | null,    // Audio streaming URL (Swedish)
      textContentEn: string | null,  // Article text (English)
      textContentSv: string | null,  // Article text (Swedish)
      videoUrl: string | null,       // Video URL
      videoEmbedCode: string | null, // Video embed code
      videoAvailableInEn: boolean,   // Video available in English
      videoAvailableInSv: boolean,   // Video available in Swedish
      purpose: string | null,        // Content purpose/description
      sortOrder: number,             // Sort order
      hasContent: boolean            // Whether content is available (false = grey out)
    }>
  }
}
```

---

## GET /api/learning/content/{content_id}/audio/{language}

Streams audio content for the frontend player.

**Path Parameters:**
- `content_id` - Content item ID
- `language` - `en` or `sv`

**Response:**
Binary audio data with appropriate `Content-Type` header (e.g., `audio/mpeg`).

**Error Responses:**
- `400` - Invalid language (must be 'en' or 'sv')
- `404` - Audio not found

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

## hasContent Logic

The `hasContent` field is computed based on content type:

- `text_article`: `true` if `textContentEn` is not empty
- `audio_article` / `audio_exercise`: `true` if `audioFileEn` exists
- `video_link`: `true` if `videoUrl` exists

Use this to grey out content cards that don't have actual content yet.
