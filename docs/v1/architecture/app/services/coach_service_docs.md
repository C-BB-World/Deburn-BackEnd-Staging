# CoachService

BrainBank AI coaching service.

---

## Classes

### CoachService

BrainBank AI coaching service. Uses the generic AIProvider interface to support multiple AI backends.

**Properties:**

- `ai` (AIProvider): AI provider instance
- `max_tokens` (int): Maximum tokens in responses
- `temperature` (float): Sampling temperature
- `system_prompt` (str): System prompt for coaching

**Methods:**

#### __init__

- **Inputs:**
  - `ai_provider` (AIProvider): AI provider instance (Claude, OpenAI, etc.)
  - `system_prompt` (Optional[str]): Custom system prompt. Uses default if None.
  - `max_tokens` (int): Maximum tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
- **Outputs:** (CoachService) New CoachService instance
- **Description:** Initialize coach service with AI provider.

#### chat

- **Inputs:**
  - `message` (str): User's message
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `user_context` (Optional[Dict[str, Any]]): User context (name, recent check-ins, etc.)
- **Outputs:** (str) Coach's response
- **Description:** Send a message and get a response.

#### stream_chat

- **Inputs:**
  - `message` (str): User's message
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `user_context` (Optional[Dict[str, Any]]): User context
- **Outputs:** (AsyncGenerator[str, None]) Yields text chunks
- **Description:** Stream a response in chunks.

#### stream_chat_sse

- **Inputs:**
  - `message` (str): User's message
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `user_context` (Optional[Dict[str, Any]]): User context
- **Outputs:** (AsyncGenerator[str, None]) Yields SSE-formatted strings
- **Description:** Stream response formatted for Server-Sent Events (SSE). Yields metadata, text chunks, actions, quickReplies, and done marker.

#### get_conversation_starters

- **Inputs:**
  - `language` (str): Language code ("en" or "sv"). Default: "en"
- **Outputs:** (List[Dict[str, str]]) List of {text, category} starters
- **Description:** Get conversation starter suggestions.

---

### Private Methods

#### _default_system_prompt

- **Outputs:** (str) Default coaching system prompt
- **Description:** Get the default coaching system prompt for Eve, the AI wellness coach.

#### _build_system_prompt

- **Inputs:**
  - `user_context` (Optional[Dict[str, Any]]): User context
- **Outputs:** (str) System prompt with context appended
- **Description:** Build system prompt with optional user context (name, organization, mood, streak, language).

#### _generate_actions

- **Inputs:**
  - `response` (str): AI response text
  - `user_context` (Optional[Dict[str, Any]]): User context
- **Outputs:** (List[Dict[str, Any]]) List of action buttons
- **Description:** Generate suggested actions (setGoal, startCheckIn, openLearning) based on response content.

#### _generate_quick_replies

- **Inputs:**
  - `response` (str): AI response text
  - `original_message` (str): User's original message
- **Outputs:** (List[str]) List of quick reply suggestions (max 4)
- **Description:** Generate quick reply suggestions based on response content.
