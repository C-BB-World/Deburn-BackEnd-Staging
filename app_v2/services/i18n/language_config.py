"""
Language configuration service.

Manages the list of supported languages with metadata.
"""

import logging
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class LanguageConfig:
    """
    Configuration for supported languages.
    Supports file-based config with option for database storage.
    """

    LANGUAGES = [
        {"code": "en", "name": "English", "nativeName": "English", "isDefault": True},
        {"code": "sv", "name": "Swedish", "nativeName": "Svenska", "isDefault": False},
    ]

    def __init__(
        self,
        db: Optional[AsyncIOMotorDatabase] = None,
        source_mode: str = "file"
    ):
        """
        Initialize LanguageConfig.

        Args:
            db: MongoDB database connection (for database mode)
            source_mode: "file" or "database"
        """
        self._db = db
        self._source_mode = source_mode
        self._languages = self.LANGUAGES.copy()

        if source_mode == "database" and db:
            self._languages_collection = db["languages"]

    def get_supported_languages(self) -> List[dict]:
        """
        Get list of supported languages with metadata.

        Returns:
            List of language dicts:
                [
                    { "code": "en", "name": "English", "isDefault": True },
                    { "code": "sv", "name": "Svenska", "isDefault": False }
                ]
        """
        return [
            {
                "code": lang["code"],
                "name": lang["name"],
                "isDefault": lang["isDefault"]
            }
            for lang in self._languages
        ]

    def get_language_codes(self) -> List[str]:
        """
        Get list of supported language codes only.

        Returns:
            List of codes (e.g., ['en', 'sv'])
        """
        return [lang["code"] for lang in self._languages]

    def get_default_language(self) -> str:
        """
        Get the default language code.

        Returns:
            Default language code (e.g., 'en')
        """
        for lang in self._languages:
            if lang["isDefault"]:
                return lang["code"]
        return "en"

    def is_supported(self, lang: str) -> bool:
        """
        Check if a language code is supported.

        Args:
            lang: Language code to check

        Returns:
            True if supported, False otherwise
        """
        return lang in self.get_language_codes()

    async def add_language(
        self,
        code: str,
        name: str,
        native_name: str = None,
        is_default: bool = False
    ) -> dict:
        """
        Add a new supported language.
        Only available in database mode.

        Args:
            code: Language code (e.g., 'de')
            name: Display name (e.g., 'German')
            native_name: Name in native language (e.g., 'Deutsch')
            is_default: Whether this is the default language

        Returns:
            Created language dict

        Raises:
            NotImplementedError: If in file mode
            ValueError: If language code already exists
        """
        if self._source_mode != "database":
            raise NotImplementedError("Adding languages only supported in database mode")

        if self.is_supported(code):
            raise ValueError(f"Language '{code}' already exists")

        language = {
            "code": code,
            "name": name,
            "nativeName": native_name or name,
            "isDefault": is_default,
            "enabled": True
        }

        await self._languages_collection.insert_one(language)
        self._languages.append(language)

        logger.info(f"Added language: {code}")
        return language

    async def remove_language(self, code: str) -> bool:
        """
        Remove a supported language.
        Only available in database mode.
        Cannot remove default language.

        Args:
            code: Language code to remove

        Returns:
            True if removed

        Raises:
            NotImplementedError: If in file mode
            ValueError: If trying to remove default language
        """
        if self._source_mode != "database":
            raise NotImplementedError("Removing languages only supported in database mode")

        for lang in self._languages:
            if lang["code"] == code:
                if lang["isDefault"]:
                    raise ValueError("Cannot remove default language")

                await self._languages_collection.delete_one({"code": code})
                self._languages.remove(lang)
                logger.info(f"Removed language: {code}")
                return True

        return False

    async def reload(self) -> None:
        """
        Reload language configuration from source.
        Used when config file or database is updated.
        """
        if self._source_mode == "database" and self._db:
            cursor = self._languages_collection.find({"enabled": True})
            self._languages = await cursor.to_list(length=None)
            logger.info(f"Reloaded {len(self._languages)} languages from database")
        else:
            self._languages = self.LANGUAGES.copy()
            logger.info("Reloaded languages from config")
