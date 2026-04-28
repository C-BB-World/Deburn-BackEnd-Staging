## API Description

Fetches dashboard overview data including today's check-in status, streak, insights count, today's focus (learning module), and next circle meeting.

## Endpoint

`GET /api/dashboard`

## JSON Structure

**Request:** None (uses session authentication)

**Frontend Input** (src/pages/Dashboard.jsx):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "todaysCheckin": {
      "mood": 4,
      "physicalEnergy": 7,
      "mentalEnergy": 6,
      "sleep": 4,
      "stress": 3
    },
    "streak": 5,
    "insightsCount": 3,
    "todaysFocus": {
      "module": {
        "id": "694e2888323051422a93d572",
        "contentType": "text_article",
        "category": "leadership",
        "titleEn": "Team Dynamics & Conflict Resolution",
        "titleSv": "Teamdynamik & Konfliktlösning",
        "lengthMinutes": 9
      },
      "currentIndex": 0,
      "totalModules": 61,
      "progress": 0.0
    },
    "nextCircle": {
      "date": "Dec 1, 3:00 PM"
    }
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    todaysCheckin: {
      mood: number,           // 1-5 scale
      physicalEnergy: number, // 1-10 scale
      mentalEnergy: number,   // 1-10 scale
      sleep: number,          // 1-5 scale
      stress: number          // 1-10 scale
    } | null,                 // null if no check-in today
    streak: number,           // Current check-in streak
    insightsCount: number,    // Number of unread insights
    todaysFocus: {
      module: {
        id: string,           // Content item ID
        contentType: string,  // "text_article" | "audio_article" | "audio_exercise" | "video_link"
        category: string,     // "leadership" | "meditation" | "breath" | etc.
        titleEn: string,      // English title
        titleSv: string,      // Swedish title
        lengthMinutes: number // Duration in minutes
      },
      currentIndex: number,   // Current position in queue (0-based)
      totalModules: number,   // Total modules in user's queue
      progress: number        // Progress as decimal (0.0 to 1.0)
    } | null,                 // null if no content available
    nextCircle: {
      date: string            // Formatted date string
    } | null
  }
}
```

## Today's Focus Feature

The "Today's Focus" feature provides a shuffled learning playlist for each user:

### Behavior
1. **New users**: A shuffled queue is created from all published content items
2. **Daily rotation**: Each day, the current index advances to show a new module
3. **Cycle completion**: When all modules are viewed, the queue reshuffles
4. **Deleted content**: If current module was deleted, queue reshuffles automatically

### Database Collection
`userlearningqueues` in main database:
```json
{
  "_id": "ObjectId",
  "userId": "ObjectId",
  "queue": ["content_id_1", "content_id_2", ...],
  "currentIndex": 0,
  "lastAdvancedDate": "2026-01-28",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Frontend Integration
Clicking "Continue" on the Today's Focus card:
1. Fetches full module data via `GET /api/learning/content/{id}`
2. Opens appropriate modal based on `contentType`:
   - `text_article` → ArticleModal
   - `audio_article` / `audio_exercise` → AudioModal
   - `video_link` → Opens URL in new tab

### Related Files
**Backend:**
- `app_v2/routers/dashboard.py` - Dashboard endpoint
- `app_v2/pipelines/learning.py` - Today's Focus pipeline
- `app_v2/services/learning/learning_queue_service.py` - Queue operations

**Frontend:**
- `src/pages/Dashboard.jsx` - Dashboard page with Today's Focus card
