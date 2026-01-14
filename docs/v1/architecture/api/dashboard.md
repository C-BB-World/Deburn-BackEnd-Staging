## API Description

Fetches dashboard overview data including today's check-in status, streak, insights count, today's focus, and next circle meeting.

## Endpoint

`GET /api/dashboard`

## JSON Structure

**Request:** None (uses session authentication)

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
