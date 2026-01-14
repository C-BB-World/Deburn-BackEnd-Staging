"""
Extended i18n service for Deburn application.

Wraps the common I18nService and adds email translations and hot reload.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from common.i18n.service import I18nService as BaseI18nService
from app_v2.i18n.services.language_config import LanguageConfig

logger = logging.getLogger(__name__)


class I18nService:
    """
    Handles translation loading and lookup.
    Supports file-based storage with optional database source.
    """

    def __init__(
        self,
        language_config: LanguageConfig,
        locales_path: str = "public/locales",
        emails_path: str = "locales/emails",
        source_mode: str = "file"
    ):
        """
        Initialize i18n service.

        Args:
            language_config: Configuration for supported languages
            locales_path: Path to UI locales directory
            emails_path: Path to email translations directory
            source_mode: "file" or "database"
        """
        self._language_config = language_config
        self._locales_path = Path(locales_path)
        self._emails_path = Path(emails_path)
        self._source_mode = source_mode

        self._translations: Dict[str, Dict[str, Any]] = {}
        self._email_translations: Dict[str, Dict[str, Any]] = {}

        self.load_translations()

    def load_translations(self) -> None:
        """
        Load all translations from configured source.
        Called at startup and on reload.

        Side Effects:
            - Clears existing translations cache
            - Loads UI translations from public/locales/{lang}/*.json
            - Loads email translations from locales/emails/{lang}.json
            - Logs loaded languages and namespace count
        """
        self._translations.clear()
        self._email_translations.clear()

        languages = self._language_config.get_language_codes()
        total_namespaces = 0

        for lang in languages:
            self._translations[lang] = self._load_from_files(lang)
            total_namespaces += len(self._translations[lang])

            email_trans = self._load_email_translations(lang)
            if email_trans:
                self._email_translations[lang] = email_trans

        logger.info(
            f"Loaded translations for {len(languages)} languages, "
            f"{total_namespaces} namespaces"
        )

    def _load_from_files(self, lang: str) -> Dict[str, Any]:
        """
        Load translations for a language from JSON files.

        Args:
            lang: Language code (e.g., 'en', 'sv')

        Returns:
            dict mapping namespace → translations dict
        """
        translations = {}
        lang_dir = self._locales_path / lang

        if not lang_dir.exists():
            logger.debug(f"Locales directory not found: {lang_dir}")
            return translations

        for file_path in lang_dir.glob("*.json"):
            namespace = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    translations[namespace] = json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
            except IOError as e:
                logger.warning(f"Failed to read {file_path}: {e}")

        return translations

    def _load_email_translations(self, lang: str) -> Optional[Dict[str, Any]]:
        """
        Load email-specific translations (backend only).

        Args:
            lang: Language code

        Returns:
            dict with email template translations
        """
        file_path = self._emails_path / f"{lang}.json"

        if not file_path.exists():
            logger.debug(f"Email translations not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None
        except IOError as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    def t(
        self,
        key: str,
        lang: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate a key to the specified language.

        Args:
            key: Dot notation key (e.g., 'validation.email.required')
            lang: Target language code
            options: Interpolation values and count for pluralization
                - count: int for pluralization selection
                - **kwargs: Values for {{varName}} interpolation

        Returns:
            Translated string, or key if not found

        Examples:
            t('common.greeting', 'en', {'name': 'Alice'})
            → "Hello, Alice!"

            t('progress.days', 'en', {'count': 5})
            → "5 days" (pluralized)
        """
        options = options or {}

        if not self.is_supported(lang):
            lang = self._language_config.get_default_language()

        parts = key.split(".")
        if len(parts) < 2:
            return key

        namespace = parts[0]
        path = parts[1:]

        value = self._get_nested_value(
            self._translations.get(lang, {}).get(namespace, {}),
            path
        )

        if value is None and lang != self._language_config.get_default_language():
            default_lang = self._language_config.get_default_language()
            value = self._get_nested_value(
                self._translations.get(default_lang, {}).get(namespace, {}),
                path
            )

        if value is None:
            logger.debug(f"Translation not found: {key} ({lang})")
            return key

        if isinstance(value, dict) and "count" in options:
            value = self._pluralize(value, options["count"])

        if isinstance(value, str):
            value = self._interpolate(value, options)

        return str(value) if value else key

    def t_email(
        self,
        key: str,
        lang: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate an email template key.

        Args:
            key: Dot notation key within email namespace
            lang: Target language code
            options: Interpolation values

        Returns:
            Translated string, or key if not found
        """
        options = options or {}

        if not self.is_supported(lang):
            lang = self._language_config.get_default_language()

        parts = key.split(".")
        value = self._get_nested_value(
            self._email_translations.get(lang, {}),
            parts
        )

        if value is None and lang != self._language_config.get_default_language():
            default_lang = self._language_config.get_default_language()
            value = self._get_nested_value(
                self._email_translations.get(default_lang, {}),
                parts
            )

        if value is None:
            logger.debug(f"Email translation not found: {key} ({lang})")
            return key

        if isinstance(value, str):
            value = self._interpolate(value, options)

        return str(value) if value else key

    def _get_nested_value(
        self,
        obj: Dict[str, Any],
        path_parts: List[str]
    ) -> Optional[Any]:
        """
        Traverse nested dict using path parts.

        Args:
            obj: Dictionary to traverse
            path_parts: List of keys to follow

        Returns:
            Value at path, or None if not found
        """
        current = obj
        for part in path_parts:
            if not isinstance(current, dict):
                return None
            if part not in current:
                return None
            current = current[part]
        return current

    def _interpolate(self, text: str, options: Dict[str, Any]) -> str:
        """
        Replace {{varName}} placeholders with values.

        Args:
            text: String with placeholders
            options: Values to interpolate

        Returns:
            String with placeholders replaced
        """
        result = text
        for var_name, var_value in options.items():
            if var_name == "count":
                result = result.replace("{{count}}", str(var_value))
            else:
                result = result.replace(f"{{{{{var_name}}}}}", str(var_value))
        return result

    def _pluralize(self, value: Dict[str, str], count: int) -> str:
        """
        Select plural form based on count.

        Args:
            value: Dict with 'one' and 'other' keys
            count: Number to determine plural form

        Returns:
            Selected plural form string
        """
        if count == 0 and "zero" in value:
            return value["zero"]
        elif count == 1 and "one" in value:
            return value["one"]
        elif "other" in value:
            return value["other"]
        else:
            return next(iter(value.values()), "")

    def reload(self) -> Dict[str, Any]:
        """
        Hot reload translations from source.

        Returns:
            dict with reload statistics:
                - success: bool
                - languages: list of loaded language codes
                - namespaces: count of loaded namespaces
        """
        self.load_translations()

        languages = list(self._translations.keys())
        namespaces = sum(len(ns) for ns in self._translations.values())

        return {
            "success": True,
            "languages": languages,
            "namespaces": namespaces
        }

    def is_supported(self, lang: str) -> bool:
        """
        Check if a language is supported.

        Args:
            lang: Language code to check

        Returns:
            True if language is in supported list
        """
        return self._language_config.is_supported(lang)

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.

        Returns:
            List of language codes (e.g., ['en', 'sv'])
        """
        return self._language_config.get_language_codes()
