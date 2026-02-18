## API Description

Endpoints for daily check-in submission and trend data retrieval.

---

## POST /api/checkin

Submits a daily check-in with mood, energy, sleep, and stress data.

**Request:**
```json
{
  "mood": 4,
  "physicalEnergy": 7,
  "mentalEnergy": 6,
  "sleep": 4,
  "stress": 3
}
```

**Frontend Input** (src/pages/Checkin.jsx):
```typescript
{
  mood: number,           // 1-5 scale (1=very low, 5=very high)
  physicalEnergy: number, // 1-10 scale
  mentalEnergy: number,   // 1-10 scale
  sleep: number,          // 1-5 scale (sleep quality)
  stress: number          // 1-10 scale (1=low stress, 10=high stress)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "streak": 5,
    "insight": "Your stress tends to spike on Thursdays...",
    "tip": "Try the 2-minute breathing exercise before your 10am call"
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    streak: number,     // Current check-in streak (days)
    insight: string,    // AI-generated insight
    tip: string         // Actionable tip
  }
}
```

---

## GET /api/checkin/trends

Fetches wellbeing trend data for a specified time period.

**Query Parameters:**
- `period` (number): Number of days (7, 30, or 90)

**Frontend Input** (src/pages/Dashboard.jsx, src/pages/Progress.jsx):
```typescript
// Query parameter
{
  period: number  // 7 | 30 | 90
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dataPoints": 7,
    "moodValues": [4, 5, 4, 3, 4, 5, 4],
    "moodChange": 12,
    "energyValues": [6, 7, 5, 6, 7, 6, 7],
    "energyChange": 5,
    "stressValues": [4, 3, 5, 4, 3, 3, 2],
    "stressChange": -15
  }
}
```

**Response Types:**
```typescript
{
  success: boolean,
  data: {
    dataPoints: number,        // Number of data points
    moodValues: number[],      // Array of mood values
    moodChange: number,        // Percentage change
    energyValues: number[],    // Array of energy values
    energyChange: number,      // Percentage change
    stressValues: number[],    // Array of stress values
    stressChange: number       // Percentage change (negative = improvement)
  }
}
```
