"""
Anthropic Claude AI provider implementation.

Provides chat completions and streaming using the Anthropic API.
Supports all Claude models.

Example:
    from common.ai import ClaudeProvider

    claude = ClaudeProvider(api_key="your-api-key")
    response = await claude.chat(
        message="Hello, how are you?",
        system_prompt="You are a helpful assistant."
    )
    print(response)

    # Streaming
    async for chunk in claude.stream_chat("Tell me a story"):
        print(chunk, end="", flush=True)
"""

from typing import AsyncGenerator, Optional, List, Dict, Any

from common.ai.base import AIProvider


class ClaudeProvider(AIProvider):
    """
    Anthropic Claude AI provider.

    Uses the Anthropic SDK for API calls.
    Supports both sync and async operations through the async client.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-sonnet-4-5-20250929)
            max_retries: Number of retries for failed requests
            timeout: Request timeout in seconds
        """
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required for Claude. "
                "Install with: pip install anthropic"
            )

        self.client = AsyncAnthropic(
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.model = model

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Send message and get response from Claude."""
        messages = list(conversation_history) if conversation_history else []
        messages.append({"role": "user", "content": message})

        params: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            params["system"] = system_prompt

        # Add any extra parameters
        for key in ["stop_sequences", "top_p", "top_k", "metadata"]:
            if key in kwargs:
                params[key] = kwargs[key]

        response = await self.client.messages.create(**params)
        return response.content[0].text

    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream response from Claude in chunks."""
        messages = list(conversation_history) if conversation_history else []
        messages.append({"role": "user", "content": message})

        params: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            params["system"] = system_prompt

        # Add any extra parameters
        for key in ["stop_sequences", "top_p", "top_k", "metadata"]:
            if key in kwargs:
                params[key] = kwargs[key]

        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding - not supported by Claude API.

        Claude doesn't have a native embeddings API.
        Consider using Voyage AI or another embedding service.

        Raises:
            NotImplementedError: Always, as Claude doesn't support embeddings
        """
        raise NotImplementedError(
            "Claude API doesn't support embeddings directly. "
            "Consider using Voyage AI (voyageai.com) for embeddings with Claude, "
            "or use OpenAI's embedding API."
        )

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens using Claude's tokenizer.

        Uses the Anthropic client's token counting if available.
        """
        try:
            # Use the anthropic client's count_tokens if available
            count = await self.client.count_tokens(text)
            return count
        except (AttributeError, NotImplementedError):
            # Fall back to estimation
            return await super().count_tokens(text)

    async def chat_with_tools(
        self,
        message: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Chat with tool use capability.

        Args:
            message: The user's message
            tools: List of tool definitions (Claude tool format)
            system_prompt: Optional system instructions
            conversation_history: Previous messages
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Dict with 'content' (text) and 'tool_calls' (if any)
        """
        messages = list(conversation_history) if conversation_history else []
        messages.append({"role": "user", "content": message})

        params: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "tools": tools,
        }

        if system_prompt:
            params["system"] = system_prompt

        response = await self.client.messages.create(**params)

        result: Dict[str, Any] = {
            "content": "",
            "tool_calls": [],
            "stop_reason": response.stop_reason,
        }

        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return result
