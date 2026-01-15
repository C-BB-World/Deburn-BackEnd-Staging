## API Description

AI coaching chat endpoints for streaming responses and conversation management.

---

## POST /api/coach/stream

Streams AI coach response using Server-Sent Events.

**Request:**
```json
{
  "message": "I want to work on my leadership skills",
  "conversationId": "conv_123abc",
  "language": "en",
  "context": {}
}
```

**Frontend Input** (src/features/coach/coachApi.js):
```typescript
{
  message: string,              // User's message to the coach
  conversationId: string | null, // Existing conversation ID or null for new
  context: object,              // Additional context (default: {})
  language: string              // Language code: "en" | "sv" (default: "en")
}
```

**Response (SSE Stream):**
```
data: {"type":"metadata","content":{"conversationId":"conv_123abc"}}

data: {"type":"text","content":"That's a great goal! "}

data: {"type":"text","content":"Leadership development..."}

data: {"type":"quickReplies","content":["Tell me more","Show me exercises"]}

data: [DONE]
```

---

## POST /api/coach/chat

Non-streaming message endpoint (alternative to stream).

**Request:**
```json
{
  "message": "Hello",
  "conversationId": null,
  "context": {},
  "language": "en"
}
```

**Frontend Input** (src/features/coach/coachApi.js):
```typescript
{
  message: string,              // User's message to the coach
  conversationId: string | null, // Existing conversation ID or null for new
  context: object,              // Additional context (default: {})
  language: string              // Language code: "en" | "sv" (default: "en")
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Hello! I'm your AI Leadership Coach...",
    "conversationId": "conv_123abc",
    "quickReplies": ["Tell me more", "I have a question"]
  }
}
```

---

## GET /api/coach/starters

Fetches conversation starter suggestions.

**Query Parameters:**
- `language` (string): Language code ('en' or 'sv')
- `includeWellbeing` (boolean): Include wellbeing-based suggestions
- `mood` (number): Current mood (if includeWellbeing)
- `energy` (number): Current energy (if includeWellbeing)
- `stress` (number): Current stress (if includeWellbeing)

**Frontend Input** (src/features/coach/coachApi.js):
```typescript
// Query parameters
{
  language: string,           // "en" | "sv" (default: "en")
  includeWellbeing?: "true",  // String "true" if wellbeing provided
  mood?: number,              // 1-5 scale (default: 3)
  energy?: number,            // 1-10 scale (default: 5)
  stress?: number             // 1-10 scale (default: 5)
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "starters": [
      {
        "key": "leadership",
        "text": "I want to work on my leadership skills"
      },
      {
        "key": "stress",
        "text": "My stress has been building up"
      }
    ]
  }
}
```

---

## GET /api/coach/history

Fetches conversation history.

**Frontend Input** (src/features/coach/coachApi.js):
```typescript
// Query parameters
{
  conversationId: string,  // The conversation ID
  limit: number            // Max messages to return (default: 50)
}
```

---

## POST /api/coach/feedback

Submits feedback for a message.

**Frontend Input** (src/features/coach/coachApi.js):
```typescript
{
  messageId: string,   // ID of the message being rated
  rating: number,      // Rating value (e.g., 1-5)
  feedback: string,    // Optional feedback text (default: "")
  category: string     // Feedback category (default: "coaching_quality")
}
```

---

## GET /api/coach/exercises

Fetches available exercises.

**Frontend Input** (src/features/coach/coachApi.js):
No request body.
