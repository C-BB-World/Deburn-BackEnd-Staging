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
