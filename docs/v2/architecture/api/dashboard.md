## API Description

Fetches dashboard overview data including today's check-in status, streak, insights count, today's focus, and next circle meeting.

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
      "title": "Module Title",
      "progress": 45
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
      title: string,          // Module title
      progress: number        // Progress percentage (0-100)
    } | null,
    nextCircle: {
      date: string            // Formatted date string
    } | null
  }
}
```
