# AIProvider (Base)

Abstract AI provider interface. Defines the contract that all AI/LLM providers must implement.

---

## Classes

### AIProvider (ABC)

Abstract AI provider interface. Implement this for different LLM services.

**Methods:**

#### chat

- **Inputs:**
  - `message` (str): The user's message
  - `system_prompt` (Optional[str]): Optional system instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages. Format: [{"role": "user"|"assistant", "content": "..."}]
  - `max_tokens` (int): Maximum tokens in response. Default: 1024
  - `temperature` (float): Sampling temperature (0-1). Default: 0.7
  - `**kwargs` (Any): Provider-specific options
- **Outputs:** (str) The AI's response text
- **Description:** Send a message and get a response.

#### stream_chat

- **Inputs:**
  - `message` (str): The user's message
  - `system_prompt` (Optional[str]): Optional system instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Maximum tokens in response. Default: 1024
  - `temperature` (float): Sampling temperature (0-1). Default: 0.7
  - `**kwargs` (Any): Provider-specific options
- **Outputs:** (AsyncGenerator[str, None]) Yields text chunks as they are generated
- **Description:** Stream a response in chunks.

#### generate_embedding

- **Inputs:**
  - `text` (str): The text to embed
- **Outputs:** (List[float]) Embedding vector
- **Description:** Generate an embedding vector for the given text. Raises NotImplementedError if provider doesn't support embeddings.

#### count_tokens

- **Inputs:**
  - `text` (str): The text to count tokens for
- **Outputs:** (int) Estimated or exact token count
- **Description:** Count the number of tokens in a text string. Default implementation estimates ~4 characters per token. Override for accurate counting.

#### health_check

- **Inputs:** None
- **Outputs:** (bool) True if service is healthy and responding
- **Description:** Check if the AI service is available.
