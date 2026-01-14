# Coach Schemas

Coach request/response schemas.

---

## Classes

### WellbeingContext

User's recent wellbeing data for context.

**Properties:**

- `mood` (Optional[int]): Recent mood
- `energy` (Optional[int]): Recent energy level
- `stress` (Optional[int]): Recent stress level
- `streak` (Optional[int]): Check-in streak

---

### CoachContext

Additional context for coaching conversation.

**Properties:**

- `recentCheckin` (Optional[WellbeingContext]): Recent check-in data

---

### ChatRequest

Coach chat request.

**Properties:**

- `message` (str): User message (1-5000 chars)
- `conversationId` (Optional[str]): Existing conversation ID
- `language` (Optional[str]): "en" or "sv"
- `context` (Optional[CoachContext]): Additional context

---

### SuggestedAction

Suggested action in coach response.

**Properties:**

- `type` (str): Action type: "setGoal", "startCheckIn", "openLearning"
- `label` (str): Display label

---

### ChatResponse

Coach chat response.

**Properties:**

- `text` (str): Coach's response text
- `conversationId` (str): Conversation ID
- `topics` (List[str]): Detected topics. Default: []
- `suggestedActions` (Optional[List[SuggestedAction]]): Suggested next actions
- `isSystemMessage` (bool): Whether this is a system message. Default: False

---

### ConversationStarter

Conversation starter option.

**Properties:**

- `id` (str): Starter ID
- `text` (str): Starter text
- `category` (str): Category: "wellness", "goals", "leadership", "work"
