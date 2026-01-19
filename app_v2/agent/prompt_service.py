"""
Prompt service for dynamic prompt loading.

Loads and caches prompts from MongoDB 'aiprompt' collection.
Supports component-based prompts with multiple languages.
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class CachedPrompt:
    """Cached prompt with expiration."""
    content: str
    cached_at: float
    version: int


class PromptService:
    """
    Loads and caches prompts from MongoDB 'aiprompt' collection.

    Prompts are stored as components that are combined at retrieval time.
    Each component has content in multiple languages (en, sv).
    """

    SEPARATOR = "\n\n---\n\n"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        cache_ttl: int = 300
    ):
        """
        Initialize PromptService.

        Args:
            db: MongoDB database connection (deburn-hub)
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
        """
        self._db = db
        self._collection = db["aiprompt"]
        self._cache: Dict[str, CachedPrompt] = {}
        self._cache_ttl = cache_ttl

    def _cache_key(self, prompt_type: str, language: str) -> str:
        """Generate cache key."""
        return f"{prompt_type}:{language}"

    def _is_cache_valid(self, cached: CachedPrompt) -> bool:
        """Check if cached prompt is still valid."""
        return (time.time() - cached.cached_at) < self._cache_ttl

    async def get_system_prompt(
        self,
        prompt_type: str,
        language: str = "en"
    ) -> str:
        """
        Get combined prompt from MongoDB or cache.

        For 'coaching' type, combines all components (base-coach, safety-rules,
        tone-guidelines) in order.

        Args:
            prompt_type: "coaching" (others raise NotImplementedError)
            language: 'en' or 'sv'

        Returns:
            Combined system prompt string

        Raises:
            NotImplementedError: For prompt types other than 'coaching'
        """
        if prompt_type != "coaching":
            raise NotImplementedError(
                f"Prompt type '{prompt_type}' is not yet implemented. "
                "Only 'coaching' is currently supported."
            )

        cache_key = self._cache_key(prompt_type, language)

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if self._is_cache_valid(cached):
                logger.debug(f"Cache hit for prompt {cache_key}")
                return cached.content

        # Load from MongoDB
        combined = await self._load_and_combine_components(prompt_type, language)

        if combined:
            # Update cache
            self._cache[cache_key] = CachedPrompt(
                content=combined,
                cached_at=time.time(),
                version=1
            )
            logger.debug(f"Loaded and cached prompt {cache_key}")
            return combined

        # No prompts found
        logger.error(f"No prompts found for {cache_key}")
        raise ValueError(f"No prompts found for type '{prompt_type}' and language '{language}'")

    async def _load_and_combine_components(
        self,
        prompt_type: str,
        language: str
    ) -> Optional[str]:
        """
        Load all components for a prompt type and combine them.

        Args:
            prompt_type: The prompt type (e.g., 'coaching')
            language: Language code ('en' or 'sv')

        Returns:
            Combined prompt string or None if no components found
        """
        cursor = self._collection.find({
            "promptType": prompt_type,
            "isActive": True
        }).sort("order", 1)

        components = []
        async for doc in cursor:
            content = doc.get("content", {})
            lang_content = content.get(language)

            if lang_content:
                components.append(lang_content)
            else:
                # Fallback to English if language not found
                en_content = content.get("en")
                if en_content:
                    logger.warning(
                        f"Language '{language}' not found for component "
                        f"'{doc.get('component')}', falling back to English"
                    )
                    components.append(en_content)

        if not components:
            return None

        return self.SEPARATOR.join(components)

    async def get_component(
        self,
        prompt_type: str,
        component: str,
        language: str = "en"
    ) -> Optional[str]:
        """
        Get a single component's content.

        Args:
            prompt_type: The prompt type (e.g., 'coaching')
            component: Component name (e.g., 'base-coach')
            language: Language code

        Returns:
            Component content or None if not found
        """
        doc = await self._collection.find_one({
            "promptType": prompt_type,
            "component": component,
            "isActive": True
        })

        if not doc:
            return None

        content = doc.get("content", {})
        return content.get(language) or content.get("en")

    async def refresh_cache(self) -> None:
        """Force refresh all cached prompts."""
        self._cache.clear()
        logger.info("Prompt cache cleared")

    async def get_all_components(
        self,
        prompt_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all components for a prompt type (for admin UI).

        Args:
            prompt_type: The prompt type

        Returns:
            List of component documents
        """
        cursor = self._collection.find({
            "promptType": prompt_type,
            "isActive": True
        }).sort("order", 1)

        components = []
        async for doc in cursor:
            components.append({
                "id": str(doc["_id"]),
                "component": doc["component"],
                "content": doc["content"],
                "order": doc["order"],
                "version": doc.get("version", 1),
                "metadata": doc.get("metadata", {}),
                "updatedAt": doc.get("updatedAt")
            })

        return components

    async def update_component(
        self,
        prompt_type: str,
        component: str,
        language: str,
        content: str,
        author: str = "system"
    ) -> bool:
        """
        Update a component's content for a specific language.

        Args:
            prompt_type: Prompt type
            component: Component name
            language: Language code
            content: New content
            author: Who made the change

        Returns:
            True if updated, False if not found
        """
        from datetime import datetime, timezone

        result = await self._collection.update_one(
            {
                "promptType": prompt_type,
                "component": component,
                "isActive": True
            },
            {
                "$set": {
                    f"content.{language}": content,
                    "updatedAt": datetime.now(timezone.utc),
                    "metadata.lastEditedBy": author
                },
                "$inc": {"version": 1}
            }
        )

        if result.modified_count > 0:
            # Invalidate cache for all languages of this prompt type
            keys_to_remove = [
                k for k in self._cache.keys()
                if k.startswith(f"{prompt_type}:")
            ]
            for key in keys_to_remove:
                self._cache.pop(key, None)

            logger.info(f"Updated component {prompt_type}/{component}/{language}")
            return True

        return False
