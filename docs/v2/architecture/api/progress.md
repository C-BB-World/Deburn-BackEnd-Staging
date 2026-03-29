## API Description

Endpoints for user progress statistics and AI-generated insights.

---

## GET /api/progress/stats

Fetches user's overall statistics.

**Frontend Input** (src/pages/Progress.jsx):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "streak": 12,
    "checkins": 45,
    "lessons": 8,
    "sessions": 23
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    streak: number,    // Current check-in streak (days)
    checkins: number,  // Total check-ins completed
    lessons: number,   // Learning modules completed
    sessions: number   // Coaching sessions completed
  }
}
```

---

## GET /api/progress/insights

Fetches AI-generated insights based on user's check-in history.

**Frontend Input** (src/pages/Progress.jsx):
No request body.

**Response:**
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "title": "Thursday Stress Pattern",
        "description": "Your stress tends to spike on Thursdays. Consider blocking 30 minutes before your afternoon meetings for preparation."
      },
      {
        "title": "Morning Energy Peak",
        "description": "You report highest energy levels between 9-11am. Schedule your most demanding tasks during this window."
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
    insights: Array<{
      title: string,       // Insight headline
      description: string  // Detailed insight with recommendation
    }>
  }
}
```
