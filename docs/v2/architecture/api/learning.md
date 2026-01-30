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
        "hasContent": true,
        "hasImage": true,
        "hasImageEn": true,
        "hasImageSv": true
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
      hasContent: boolean,           // Whether content is available (false = grey out)
      hasImage: boolean,             // Whether article has an image
      hasImageEn: boolean,           // Whether English image exists
      hasImageSv: boolean            // Whether Swedish image exists
    }>
  }
}
```

---

## GET /api/learning/content/{content_id}

Fetches a single content item by ID.

**Path Parameters:**
- `content_id` - Content item ID

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

## GET /api/article-image/{content_id}/{language}

Fetches article image for a content item.

**Path Parameters:**
- `content_id` - Content item ID
- `language` - `en` or `sv`

**Response:**
Binary image data with appropriate `Content-Type` header (e.g., `image/jpeg`, `image/png`).

**Headers:**
- `Content-Type` - Image MIME type
- `Cache-Control: public, max-age=86400` - 24 hour cache

**Fallback Behavior:**
- If Swedish (`sv`) is requested but no Swedish image exists, returns English image
- If no image exists for the requested language, returns `404`

**Error Responses:**
- `400` - Invalid content ID or language
- `404` - Content not found or no image available

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

---

## hasImage Logic

The `hasImage`, `hasImageEn`, and `hasImageSv` fields indicate whether an article image is available:

- All three flags are `true` if `articleImageMimeType` field exists in the database
- Currently uses a single image for both languages (Swedish falls back to English)
- Use these flags to conditionally fetch and display article images
