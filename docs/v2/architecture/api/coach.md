## API Description

AI coaching chat endpoints for streaming responses and conversation management.

**Key Features:**
- SSE streaming responses with actions
- Encrypted conversation persistence (AES-256-CBC)
- Pipeline architecture for storage (SOLID principles)

---

## POST /api/coach/chat

Streams AI coach response using Server-Sent Events. Messages are automatically encrypted and stored.

**Request:**
```json
{
  "message": "I want to work on my leadership skills",
  "conversationId": "conv_123abc",
  "language": "en"
}
```

**Frontend Input** (src/features/coach/coachApi.js):
```typescript
{
  message: string,              // User's message to the coach
  conversationId: string | null, // Existing conversation ID or null for new
  language: string              // Language code: "en" | "sv" (default: "en")
}
```

**Response (SSE Stream):**
```
data: {"type":"text","content":"That's a great goal! "}

data: {"type":"text","content":"Leadership development..."}

data: {"type":"actions","content":[
  {"type":"exercise","id":"breathing-1","label":"Try a Calming Exercise","metadata":{"duration":"3 min","contentType":"audio_exercise","category":"breathing"}},
  {"type":"learning","id":"stress-mgmt-1","label":"Learn: Stress Management","metadata":{"duration":"5 min","contentType":"audio_article","category":"wellbeing"}}
]}

data: {"type":"quickReplies","content":["Tell me more","Show me exercises"]}

data: {"type":"metadata","content":{"conversationId":"conv_123abc","topics":["stress"],"safetyLevel":0}}

data: {"type":"done","content":null}
```

**Stream Chunk Types:**
| Type | Content | Description |
|------|---------|-------------|
| `text` | string | Incremental response text |
| `actions` | Action[] | Recommended learning/exercises |
| `quickReplies` | string[] | Suggested follow-up messages |
| `metadata` | object | conversationId, topics, safetyLevel |
| `done` | null | Stream complete |

**Action Object:**
```typescript
{
  type: string,      // "learning" | "exercise"
  id: string,        // Content identifier
  label: string,     // User-facing label
  metadata: {
    duration?: string,     // e.g., "3 min"
    contentType?: string,  // e.g., "audio_exercise", "audio_article"
    category?: string      // e.g., "breathing", "wellbeing"
  }
}
```

**Internal Flow:**
1. Pipeline: Get/create conversation (decrypt history)
2. Pipeline: Save user message (encrypted)
3. CoachService: Generate AI response (pure logic)
4. Pipeline: Save assistant message (encrypted with actions)
5. Pipeline: Update topics

---

## GET /api/coach/starters

Fetches conversation starter suggestions based on user wellbeing data.

**Query Parameters:**
- `language` (string): Language code ('en' or 'sv')
- `includeWellbeing` (boolean): Include wellbeing-based suggestions

**Response:**
```json
{
  "success": true,
  "data": {
    "starters": [
      {"label": "I want to work on my leadership skills", "context": "leadership"},
      {"label": "My stress has been building up", "context": "stress"}
    ]
  }
}
```

---

## GET /api/coach/conversations

Fetches user's recent conversations (decrypted).

**Query Parameters:**
- `limit` (number): Max conversations to return (default: 10, max: 50)

**Response:**
```json
{
  "success": true,
  "data": {
    "conversations": [
      {
        "id": "abc123",
        "conversationId": "conv_20260119_abc123",
        "userId": "user123",
        "messages": [...],
        "topics": ["stress", "leadership"],
        "status": "active",
        "lastMessageAt": "2026-01-19T12:00:00Z",
        "createdAt": "2026-01-19T10:00:00Z"
      }
    ]
  }
}
```

---

## GET /api/coach/conversations/{conversation_id}

Fetches a specific conversation by ID.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "abc123",
    "conversationId": "conv_20260119_abc123",
    "messages": [
      {"role": "user", "content": "Hello", "timestamp": "..."},
      {"role": "assistant", "content": "Hi there!", "timestamp": "..."}
    ],
    "topics": ["greeting"],
    "status": "active"
  }
}
```

---

## POST /api/coach/voice

Converts text to speech using ElevenLabs.

**Request:**
```json
{
  "text": "Hello, how can I help you today?",
  "voice": "Aria"
}
```

**Response:** `audio/mpeg` (MP3 binary)

**Available Voices:**
- `Aria` (default coach voice)
- `Sarah` (standard female)
- `Roger` (standard male)

---

## GET /api/coach/commitments

Fetches active commitments.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "commit123",
      "commitment": "Take a 5-minute walk after lunch",
      "topic": "stress",
      "status": "active",
      "followUpDate": "2026-01-20T12:00:00Z"
    }
  ]
}
```

---

## POST /api/coach/commitments/{commitment_id}/complete

Marks a commitment as completed.

**Request:**
```json
{
  "reflectionNotes": "I felt much better after the walk",
  "helpfulnessRating": 4
}
```

---

## POST /api/coach/commitments/{commitment_id}/dismiss

Dismisses a commitment.

---

## GET /api/coach/patterns

Fetches detected patterns from check-in data.

**Query Parameters:**
- `days` (number): Analysis period (default: 30, min: 7, max: 90)

**Response:**
```json
{
  "success": true,
  "data": {
    "streak": 7,
    "morningCheckins": 5,
    "stressDayPattern": "Monday",
    "moodChange": 0.5,
    "stressChange": -0.3
  }
}
