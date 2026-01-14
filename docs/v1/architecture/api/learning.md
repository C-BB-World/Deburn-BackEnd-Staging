## API Description

Endpoints for learning modules and content management.

---

## GET /api/learning/modules

Fetches list of available learning modules with progress.

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

---

## Module Types

- `video` - Video content
- `audio` - Audio/podcast content
- `article` - Text-based content
- `exercise` - Interactive exercise
