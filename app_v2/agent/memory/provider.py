"""
Abstract memory provider interface.

Defines the contract for conversation memory implementations.
Allows swapping between encrypted, RAG, or other memory backends.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from app_v2.agent.types import Conversation, Message, ConversationSummary


class MemoryProvider(ABC):
    """
    Abstract interface for conversation memory.

    Implementations may use encrypted storage, RAG systems, or other backends.
    """

    @abstractmethod
    async def store_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a single message.

        Args:
            conversation_id: Conversation ID
            user_id: User's ID
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (topics, etc.)
        """
        pass

    @abstractmethod
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Conversation]:
        """
        Retrieve full conversation.

        Args:
            conversation_id: Conversation ID
            user_id: User's ID (for validation)

        Returns:
            Conversation object or None if not found
        """
        pass

    @abstractmethod
    async def get_recent_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Get recent messages for context window.

        Args:
            conversation_id: Conversation ID
            user_id: User's ID
            limit: Maximum messages to return

        Returns:
            List of recent messages (oldest first)
        """
        pass

    @abstractmethod
    async def create_conversation(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new conversation.

        Args:
            user_id: User's ID
            metadata: Optional initial metadata

        Returns:
            New conversation ID
        """
        pass

    @abstractmethod
    async def get_or_create_conversation(
        self,
        conversation_id: Optional[str],
        user_id: str
    ) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            conversation_id: Existing ID or None for new
            user_id: User's ID

        Returns:
            Conversation object
        """
        pass

    @abstractmethod
    async def update_topics(
        self,
        conversation_id: str,
        topics: List[str]
    ) -> None:
        """
        Update detected topics for conversation.

        Args:
            conversation_id: Conversation ID
            topics: List of topic strings to add
        """
        pass

    @abstractmethod
    async def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Get user's recent conversations.

        Args:
            user_id: User's ID
            limit: Maximum conversations to return

        Returns:
            List of recent conversations
        """
        pass

    @abstractmethod
    async def archive_conversation(
        self,
        conversation_id: str
    ) -> None:
        """
        Archive a conversation.

        Args:
            conversation_id: Conversation ID
        """
        pass

    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[ConversationSummary]:
        """
        Search past conversations.

        Default implementation returns empty list.
        Override for RAG-enabled implementations.

        Args:
            user_id: User's ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching conversation summaries
        """
        return []

    @abstractmethod
    async def clear_all_memory(
        self,
        user_id: str
    ) -> int:
        """
        Permanently delete all conversations for a user.

        This operation is irreversible. Use with caution.

        Args:
            user_id: User's ID

        Returns:
            Number of conversations deleted
        """
        pass
