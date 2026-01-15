## API Description

Endpoints for learning modules and content management.

---

## GET /api/learning/modules

Fetches list of available learning modules with progress.

**Frontend Input** (src/pages/Learning.jsx):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "modules": [
      {
        "id": "mod_123",
        "title": "Time Ninja: Mastering Your Schedule",
        "description": "Learn effective time management techniques",
        "type": "audio",
        "duration": 15,
        "thumbnail": "/images/modules/time-ninja.jpg",
        "progress": 45
      },
      {
        "id": "mod_456",
        "title": "Stress Management Basics",
        "description": "Techniques for managing daily stress",
        "type": "video",
        "duration": 20,
        "thumbnail": null,
        "progress": 0
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
    modules: Array<{
      id: string,              // Module ID
      title: string,           // Module title
      description: string,     // Module description
      type: string,            // "video" | "audio" | "article" | "exercise"
      duration: number,        // Duration in minutes
      thumbnail: string | null, // Thumbnail URL or null
      progress: number         // Progress percentage (0-100)
    }>
  }
}
```

---

## Module Types

- `video` - Video content
- `audio` - Audio/podcast content
- `article` - Text-based content
- `exercise` - Interactive exercise
