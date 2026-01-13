"""
OpenAI GPT provider implementation.

Provides chat completions, streaming, and embeddings using the OpenAI API.
Supports GPT-4, GPT-4o, and other OpenAI models.

Example:
    from common.ai import OpenAIProvider

    openai = OpenAIProvider(api_key="your-api-key")
    response = await openai.chat(
        message="Hello, how are you?",
        system_prompt="You are a helpful assistant."
    )
    print(response)

    # Embeddings
    embedding = await openai.generate_embedding("Hello world")
    print(len(embedding))  # 1536 for text-embedding-3-small
"""

from typing import AsyncGenerator, Optional, List, Dict, Any

from common.ai.base import AIProvider


class OpenAIProvider(AIProvider):
    """
    OpenAI GPT provider.

    Uses the OpenAI async client for API calls.
    Supports chat completions, streaming, and embeddings.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        max_retries: int = 3,
        timeout: float = 60.0,
        organization: Optional[str] = None,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Chat model to use (default: gpt-4o)
            embedding_model: Embedding model (default: text-embedding-3-small)
            max_retries: Number of retries for failed requests
            timeout: Request timeout in seconds
            organization: Optional OpenAI organization ID
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAI. "
                "Install with: pip install openai"
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
            organization=organization,
        )
        self.model = model
        self.embedding_model = embedding_model

    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Send message and get response from OpenAI."""
        messages: List[Dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        params: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add optional parameters
        for key in ["stop", "presence_penalty", "frequency_penalty", "top_p", "seed"]:
            if key in kwargs:
                params[key] = kwargs[key]

        response = await self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI in chunks."""
        messages: List[Dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        params: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        # Add optional parameters
        for key in ["stop", "presence_penalty", "frequency_penalty", "top_p", "seed"]:
            if key in kwargs:
                params[key] = kwargs[key]

        stream = await self.client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector using OpenAI's embedding API."""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single request.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Requires tiktoken package for accurate counting.
        """
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except ImportError:
            # Fall back to estimation
            return await super().count_tokens(text)
        except KeyError:
            # Model not found in tiktoken
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
        Chat with function/tool calling capability.

        Args:
            message: The user's message
            tools: List of tool definitions (OpenAI function format)
            system_prompt: Optional system instructions
            conversation_history: Previous messages
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Dict with 'content' (text) and 'tool_calls' (if any)
        """
        messages: List[Dict[str, Any]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        params: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": tools,
        }

        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]

        result: Dict[str, Any] = {
            "content": choice.message.content or "",
            "tool_calls": [],
            "finish_reason": choice.finish_reason,
        }

        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                result["tool_calls"].append({
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                })

        return result

    async def create_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
    ) -> List[str]:
        """
        Generate images using DALL-E.

        Args:
            prompt: Image description
            model: DALL-E model (dall-e-2 or dall-e-3)
            size: Image size
            quality: Image quality (standard or hd)
            n: Number of images to generate

        Returns:
            List of image URLs
        """
        response = await self.client.images.generate(
            model=model,
            prompt=prompt,
            size=size,  # type: ignore
            quality=quality,  # type: ignore
            n=n,
        )
        return [image.url for image in response.data if image.url]
