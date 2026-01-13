"""
Abstract AI provider interface.

Defines the contract that all AI/LLM providers must implement.
This allows swapping between different AI services (Claude, OpenAI, etc.)
without changing application code.

Example:
    from common.ai import AIProvider, ClaudeProvider, OpenAIProvider

    def get_ai_provider(settings) -> AIProvider:
        if settings.AI_PROVIDER == "openai":
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY)
        return ClaudeProvider(api_key=settings.CLAUDE_API_KEY)
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict, Any


class AIProvider(ABC):
    """
    Abstract AI provider interface.

    Implement this for different LLM services.
    Supports both streaming and non-streaming chat completions.
    """

    @abstractmethod
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Send a message and get a response.

        Args:
            message: The user's message
            system_prompt: Optional system instructions
            conversation_history: Previous messages in the conversation
                Format: [{"role": "user"|"assistant", "content": "..."}]
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0-1)
            **kwargs: Provider-specific options

        Returns:
            The AI's response text
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response in chunks.

        Args:
            message: The user's message
            system_prompt: Optional system instructions
            conversation_history: Previous messages in the conversation
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0-1)
            **kwargs: Provider-specific options

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector

        Raises:
            NotImplementedError: If the provider doesn't support embeddings
        """
        pass

    async def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Default implementation estimates based on word count.
        Override for accurate token counting.

        Args:
            text: The text to count tokens for

        Returns:
            Estimated or exact token count
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4

    async def health_check(self) -> bool:
        """
        Check if the AI service is available.

        Returns:
            True if the service is healthy and responding
        """
        try:
            await self.chat("test", max_tokens=5)
            return True
        except Exception:
            return False
