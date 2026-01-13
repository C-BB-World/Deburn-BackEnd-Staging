# ClaudeProvider

Anthropic Claude AI provider implementation.

---

## Classes

### ClaudeProvider

Anthropic Claude AI provider. Uses the Anthropic SDK for API calls.

**Properties:**

- `client` (AsyncAnthropic): Anthropic async client
- `model` (str): Model to use

**Methods:**

#### __init__

- **Inputs:**
  - `api_key` (str): Anthropic API key
  - `model` (str): Model to use. Default: "claude-sonnet-4-5-20250929"
  - `max_retries` (int): Number of retries for failed requests. Default: 3
  - `timeout` (float): Request timeout in seconds. Default: 60.0
- **Outputs:** (ClaudeProvider) New ClaudeProvider instance
- **Description:** Initialize Claude provider. Raises ImportError if anthropic package not installed.

#### chat

- **Inputs:**
  - `message` (str): User's message
  - `system_prompt` (Optional[str]): System instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Max response tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
  - `**kwargs` (Any): Optional: model, stop_sequences, top_p, top_k, metadata
- **Outputs:** (str) Response text
- **Description:** Send message and get response from Claude.

#### stream_chat

- **Inputs:**
  - `message` (str): User's message
  - `system_prompt` (Optional[str]): System instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Max response tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
  - `**kwargs` (Any): Optional: model, stop_sequences, top_p, top_k, metadata
- **Outputs:** (AsyncGenerator[str, None]) Yields text chunks
- **Description:** Stream response from Claude in chunks.

#### generate_embedding

- **Inputs:**
  - `text` (str): Text to embed
- **Outputs:** (List[float]) N/A
- **Description:** Not supported by Claude API. Raises NotImplementedError. Consider using Voyage AI or OpenAI embeddings.

#### count_tokens

- **Inputs:**
  - `text` (str): Text to count
- **Outputs:** (int) Token count
- **Description:** Count tokens using Claude's tokenizer if available, otherwise estimates.

#### chat_with_tools

- **Inputs:**
  - `message` (str): User's message
  - `tools` (List[Dict[str, Any]]): Tool definitions (Claude tool format)
  - `system_prompt` (Optional[str]): System instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Max response tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
  - `**kwargs` (Any): Optional parameters
- **Outputs:** (Dict[str, Any]) Dict with 'content' (text), 'tool_calls' (list of {id, name, input}), 'stop_reason'
- **Description:** Chat with tool use capability.
