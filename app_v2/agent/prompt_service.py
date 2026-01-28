"""
Prompt service for dynamic prompt loading.

Supports two sources:
- "aiprompt": Loads from MongoDB 'aiprompt' collection (default)
- "file": Loads from local markdown files

Supports component-based prompts with multiple languages.
"""

import logging
import os
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
    Loads and caches prompts from MongoDB or local files.

    Prompts are stored as components that are combined at retrieval time.
    Each component has content in multiple languages (en, sv).
    """

    SEPARATOR = "\n\n---\n\n"
    COMPONENTS = ["base-coach", "safety-rules", "tone-guidelines"]

    def __init__(
        self,
        db: Optional[AsyncIOMotorDatabase] = None,
        cache_ttl: int = 300,
        source: str = "aiprompt",
        prompts_dir: Optional[str] = None
    ):
        """
        Initialize PromptService.

        Args:
            db: MongoDB database connection (required for "aiprompt" source)
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
            source: "aiprompt" for MongoDB or "file" for local files
            prompts_dir: Directory containing prompt files (for "file" source)
        """
        self._db = db
        self._collection = db["aiprompt"] if db is not None else None
        self._cache: Dict[str, CachedPrompt] = {}
        self._cache_ttl = cache_ttl
        self._source = source
        self._prompts_dir = prompts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "system"
        )

        if source == "aiprompt" and db is None:
            raise ValueError("Database connection required for 'aiprompt' source")

        if source == "file" and not os.path.exists(self._prompts_dir):
            raise ValueError(f"Prompts directory not found: {self._prompts_dir}")

        logger.info(f"PromptService initialized with source='{source}'")

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
        Get combined prompt from configured source or cache.

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

        # Load from source
        if self._source == "file":
            combined = self._load_from_files(language)
        else:
            combined = await self._load_and_combine_components(prompt_type, language)

        if combined:
            # Update cache
            self._cache[cache_key] = CachedPrompt(
                content=combined,
                cached_at=time.time(),
                version=1
            )
            logger.debug(f"Loaded and cached prompt {cache_key} from {self._source}")
            return combined

        # No prompts found
        logger.error(f"No prompts found for {cache_key}")
        raise ValueError(f"No prompts found for type '{prompt_type}' and language '{language}'")

    def _load_from_files(self, language: str) -> Optional[str]:
        """
        Load prompts from local markdown files.

        Args:
            language: Language code ('en' or 'sv')

        Returns:
            Combined prompt string or None if files not found
        """
        lang_dir = os.path.join(self._prompts_dir, language)

        # Fallback to English if language directory doesn't exist
        if not os.path.exists(lang_dir):
            logger.warning(f"Language directory '{language}' not found, falling back to 'en'")
            lang_dir = os.path.join(self._prompts_dir, "en")

        if not os.path.exists(lang_dir):
            logger.error(f"Prompts directory not found: {lang_dir}")
            return None

        components = []
        for component in self.COMPONENTS:
            file_path = os.path.join(lang_dir, f"{component}.md")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content:
                            components.append(content)
                            logger.debug(f"Loaded {file_path} ({len(content)} chars)")
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
            else:
                logger.warning(f"Component file not found: {file_path}")

        if not components:
            return None

        return self.SEPARATOR.join(components)

    async def _load_and_combine_components(
        self,
        prompt_type: str,
        language: str
    ) -> Optional[str]:
        """
        Load all components for a prompt type from MongoDB and combine them.

        Args:
            prompt_type: The prompt type (e.g., 'coaching')
            language: Language code ('en' or 'sv')

        Returns:
            Combined prompt string or None if no components found
        """
        if self._collection is None:
            logger.error("MongoDB collection not available")
            return None

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
        if self._source == "file":
            file_path = os.path.join(self._prompts_dir, language, f"{component}.md")
            if not os.path.exists(file_path):
                file_path = os.path.join(self._prompts_dir, "en", f"{component}.md")

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            return None

        if self._collection is None:
            return None

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
        if self._source == "file":
            # Return file-based components
            components = []
            for idx, component in enumerate(self.COMPONENTS):
                content = {}
                for lang in ["en", "sv"]:
                    file_path = os.path.join(self._prompts_dir, lang, f"{component}.md")
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            content[lang] = f.read()

                components.append({
                    "id": component,
                    "component": component,
                    "content": content,
                    "order": idx + 1,
                    "version": 1,
                    "metadata": {"source": "file"},
                    "updatedAt": None
                })
            return components

        if self._collection is None:
            return []

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
        if self._source == "file":
            # Update file
            file_path = os.path.join(self._prompts_dir, language, f"{component}.md")
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Invalidate cache
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{prompt_type}:")]
                for key in keys_to_remove:
                    self._cache.pop(key, None)

                logger.info(f"Updated file {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error writing {file_path}: {e}")
                return False

        if self._collection is None:
            return False

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
