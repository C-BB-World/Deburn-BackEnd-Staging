"""
Translation service using Claude API.

Handles batch translation of chat messages with caching.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from common.ai.claude import ClaudeProvider

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translates chat messages using Claude API.
    Optimized for batch translation to reduce API calls.
    """

    # Language display names for prompts
    LANGUAGE_NAMES = {
        "en": "English",
        "sv": "Swedish",
    }

    def __init__(self, claude_provider: ClaudeProvider):
        """
        Initialize TranslationService.

        Args:
            claude_provider: Claude API provider for translation
        """
        self._claude = claude_provider

    async def translate_messages(
        self,
        messages: List[Dict[str, Any]],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Translate a batch of messages to target language.

        Args:
            messages: List of messages with 'index' and 'content' keys
            target_language: Target language code ('en' or 'sv')
            source_language: Source language code (auto-detect if None)

        Returns:
            List of translated messages with 'index' and 'content' keys
        """
        if not messages:
            return []

        target_name = self.LANGUAGE_NAMES.get(target_language, target_language)
        source_name = self.LANGUAGE_NAMES.get(source_language, "the original language") if source_language else "the original language"

        # Build the translation prompt
        messages_text = "\n".join([
            f'{i+1}. "{msg["content"]}"'
            for i, msg in enumerate(messages)
        ])

        prompt = f"""Translate the following messages from {source_name} to {target_name}.
These are messages from a coaching conversation. Maintain the tone, warmth, and context.

Important:
- Keep the same meaning and emotional tone
- Preserve any formatting (bullet points, numbered lists)
- Return ONLY valid JSON array, no other text

Messages to translate:
{messages_text}

Return as JSON array with objects containing "index" (0-based) and "content" (translated text):
[{{"index": 0, "content": "translated text"}}, ...]"""

        try:
            response = await self._claude.chat(
                message=prompt,
                system_prompt="You are a professional translator. Return only valid JSON.",
                max_tokens=4096,
            )

            # Parse JSON response
            translated = self._parse_translation_response(response, messages)
            return translated

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return original messages on failure
            return [{"index": msg.get("index", i), "content": msg["content"]} for i, msg in enumerate(messages)]

    def _parse_translation_response(
        self,
        response: str,
        original_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse Claude's translation response.

        Args:
            response: Raw response from Claude
            original_messages: Original messages for fallback

        Returns:
            List of translated messages
        """
        try:
            # Try to extract JSON from response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            # Find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end > start:
                response = response[start:end]

            translated = json.loads(response)

            # Validate structure
            if not isinstance(translated, list):
                raise ValueError("Response is not a list")

            # Map back to original indices
            result = []
            for item in translated:
                if isinstance(item, dict) and "content" in item:
                    idx = item.get("index", len(result))
                    result.append({
                        "index": original_messages[idx].get("index", idx) if idx < len(original_messages) else idx,
                        "content": item["content"]
                    })

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse translation response: {e}")
            # Return original on parse failure
            return [{"index": msg.get("index", i), "content": msg["content"]} for i, msg in enumerate(original_messages)]

    async def translate_single(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> str:
        """
        Translate a single text string.

        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)

        Returns:
            Translated text
        """
        result = await self.translate_messages(
            messages=[{"index": 0, "content": text}],
            target_language=target_language,
            source_language=source_language,
        )
        return result[0]["content"] if result else text
