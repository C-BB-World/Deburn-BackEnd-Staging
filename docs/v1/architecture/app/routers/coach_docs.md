# Coach Router

AI coaching conversation endpoints with streaming support.

---

## Functions

### check_quota

- **Inputs:**
  - `user` (User): User model
- **Outputs:** (dict) {allowed: bool, limit: int, count: int}
- **Description:** Check if user has exceeded daily exchange limit. Resets count if new day.

### increment_exchange_count

- **Inputs:**
  - `user` (User): User model
- **Outputs:** (None)
- **Description:** Increment the user's daily exchange count and save.

---

## Constants

### QUOTA_MESSAGES

- **Type:** dict
- **Description:** Quota exceeded messages by language code ("en", "sv").

---

## Endpoints

### POST /api/coach/chat

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Body: `ChatRequest` (message, conversationId?, language?, context?)
- **Outputs:** (dict) {quotaExceeded: bool, response: ChatResponse, conversationId?: string}
- **Description:** Send a message to the AI coach and get a response. Returns quota exceeded message if limit reached. Increments exchange count.

---

### POST /api/coach/stream

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Body: `ChatRequest` (message, conversationId?, language?, context?)
- **Outputs:** (StreamingResponse) Server-Sent Events stream
- **Description:** Stream a conversation with the AI coach. Returns SSE stream with chunks: {type: "text"|"quotaExceeded"|"done"|"error", content: string}. Ends with "data: [DONE]".

---

### GET /api/coach/starters

- **Inputs:**
  - Header: Authorization (Bearer token)
  - Query:
    - `language` (string, "en"|"sv", default "en")
    - `includeWellbeing` (bool, default false)
    - `mood` (int, 1-5, optional)
    - `energy` (int, 1-10, optional)
    - `stress` (int, 1-10, optional)
- **Outputs:** (dict) {starters: List[ConversationStarter]}
- **Description:** Get conversation starters based on user context. Returns localized starters with categories (wellness, goals, leadership, work).
