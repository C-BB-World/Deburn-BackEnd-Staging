# OpenAIProvider

OpenAI GPT provider implementation.

---

## Classes

### OpenAIProvider

OpenAI GPT provider. Uses the OpenAI async client for API calls.

**Properties:**

- `client` (AsyncOpenAI): OpenAI async client
- `model` (str): Chat model to use
- `embedding_model` (str): Embedding model to use

**Methods:**

#### __init__

- **Inputs:**
  - `api_key` (str): OpenAI API key
  - `model` (str): Chat model. Default: "gpt-4o"
  - `embedding_model` (str): Embedding model. Default: "text-embedding-3-small"
  - `max_retries` (int): Retries for failed requests. Default: 3
  - `timeout` (float): Request timeout in seconds. Default: 60.0
  - `organization` (Optional[str]): OpenAI organization ID
- **Outputs:** (OpenAIProvider) New OpenAIProvider instance
- **Description:** Initialize OpenAI provider. Raises ImportError if openai package not installed.

#### chat

- **Inputs:**
  - `message` (str): User's message
  - `system_prompt` (Optional[str]): System instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Max response tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
  - `**kwargs` (Any): Optional: model, stop, presence_penalty, frequency_penalty, top_p, seed
- **Outputs:** (str) Response text
- **Description:** Send message and get response from OpenAI.

#### stream_chat

- **Inputs:**
  - `message` (str): User's message
  - `system_prompt` (Optional[str]): System instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Max response tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
  - `**kwargs` (Any): Optional parameters
- **Outputs:** (AsyncGenerator[str, None]) Yields text chunks
- **Description:** Stream response from OpenAI in chunks.

#### generate_embedding

- **Inputs:**
  - `text` (str): Text to embed
- **Outputs:** (List[float]) Embedding vector (1536 dims for text-embedding-3-small)
- **Description:** Generate embedding vector using OpenAI's embedding API.

#### generate_embeddings_batch

- **Inputs:**
  - `texts` (List[str]): List of texts to embed
- **Outputs:** (List[List[float]]) List of embedding vectors
- **Description:** Generate embeddings for multiple texts in a single request.

#### count_tokens

- **Inputs:**
  - `text` (str): Text to count
- **Outputs:** (int) Token count
- **Description:** Count tokens using tiktoken if available, otherwise estimates.

#### chat_with_tools

- **Inputs:**
  - `message` (str): User's message
  - `tools` (List[Dict[str, Any]]): Tool definitions (OpenAI function format)
  - `system_prompt` (Optional[str]): System instructions
  - `conversation_history` (Optional[List[Dict[str, str]]]): Previous messages
  - `max_tokens` (int): Max response tokens. Default: 1024
  - `temperature` (float): Sampling temperature. Default: 0.7
  - `**kwargs` (Any): Optional parameters
- **Outputs:** (Dict[str, Any]) Dict with 'content' (text), 'tool_calls' (list of {id, name, arguments}), 'finish_reason'
- **Description:** Chat with function/tool calling capability.

#### create_image

- **Inputs:**
  - `prompt` (str): Image description
  - `model` (str): DALL-E model. Default: "dall-e-3"
  - `size` (str): Image size. Default: "1024x1024"
  - `quality` (str): Image quality ("standard" or "hd"). Default: "standard"
  - `n` (int): Number of images. Default: 1
- **Outputs:** (List[str]) List of image URLs
- **Description:** Generate images using DALL-E.
