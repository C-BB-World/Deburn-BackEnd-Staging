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

---

## GET /api/checkin/trends

Fetches wellbeing trend data for a specified time period.

**Query Parameters:**
- `period` (number): Number of days (7, 30, or 90)

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
