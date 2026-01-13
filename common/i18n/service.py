"""
Generic internationalization (i18n) service.

Provides translation loading and lookup with support for:
- Multiple languages with fallback
- Nested translation keys (dot notation)
- Variable interpolation
- Pluralization

Translations are loaded at startup from JSON files.

Example:
    # Directory structure:
    # locales/
    #   en/
    #     common.json
    #     auth.json
    #   sv/
    #     common.json
    #     auth.json

    from common.i18n import I18nService

    i18n = I18nService(
        locales_dir="./locales",
        default_language="en",
    )

    # Simple translation
    message = i18n.t("auth.login.success", language="en")

    # With interpolation
    greeting = i18n.t("common.greeting", language="sv", name="John")

    # With pluralization
    items = i18n.t("cart.items", language="en", count=5)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class I18nService:
    """
    Generic internationalization service.

    Loads translations from JSON files at startup and provides
    fast lookup with fallback to default language.
    """

    def __init__(
        self,
        locales_dir: str,
        default_language: str = "en",
        supported_languages: Optional[List[str]] = None,
        fallback_to_key: bool = True,
    ):
        """
        Initialize i18n service.

        Args:
            locales_dir: Path to the locales directory
            default_language: Default language code for fallback
            supported_languages: List of supported language codes.
                If None, auto-detects from directory structure.
            fallback_to_key: If True, return the key when translation not found
        """
        self.locales_dir = Path(locales_dir)
        self.default_language = default_language
        self.fallback_to_key = fallback_to_key
        self.translations: Dict[str, Dict[str, Any]] = {}

        # Auto-detect or use provided languages
        if supported_languages:
            self.supported_languages = supported_languages
        else:
            self.supported_languages = self._detect_languages()

        # Load all translations at startup
        self._load_translations()

    def _detect_languages(self) -> List[str]:
        """Detect available languages from directory structure."""
        if not self.locales_dir.exists():
            return [self.default_language]

        languages = []
        for path in self.locales_dir.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                languages.append(path.name)

        return languages if languages else [self.default_language]

    def _load_translations(self) -> None:
        """Load all translation files at startup."""
        for lang in self.supported_languages:
            self.translations[lang] = {}
            lang_dir = self.locales_dir / lang

            if not lang_dir.exists():
                continue

            # Load all JSON files in the language directory
            for file_path in lang_dir.glob("*.json"):
                namespace = file_path.stem
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.translations[lang][namespace] = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse {file_path}: {e}")
                except IOError as e:
                    print(f"Warning: Failed to read {file_path}: {e}")

    def _get_nested(
        self,
        data: Dict[str, Any],
        path: List[str],
    ) -> Optional[Any]:
        """Navigate nested dictionary using path list."""
        current = data
        for key in path:
            if not isinstance(current, dict):
                return None
            if key not in current:
                return None
            current = current[key]
        return current

    def t(
        self,
        key: str,
        language: Optional[str] = None,
        **options: Any,
    ) -> str:
        """
        Get translation by dot-notation key.

        Args:
            key: Dot notation key (e.g., 'auth.login.success')
                First part is the namespace (filename without .json)
            language: Language code (falls back to default if not supported)
            **options: Interpolation values. Special keys:
                - count: For pluralization (uses 'one' or 'other' forms)
                - default: Default value if key not found

        Returns:
            Translated string, or the key if not found (configurable)

        Examples:
            i18n.t("auth.login.success")
            i18n.t("common.greeting", name="John")
            i18n.t("cart.items", count=5)
            i18n.t("missing.key", default="Fallback text")
        """
        # Validate language
        lang = language if language in self.supported_languages else self.default_language

        # Parse key into namespace and path
        parts = key.split(".")
        if len(parts) < 2:
            return options.get("default", key) if self.fallback_to_key else key

        namespace = parts[0]
        path = parts[1:]

        # Try to get value in requested language
        value = self._get_nested(
            self.translations.get(lang, {}).get(namespace, {}),
            path,
        )

        # Fallback to default language if not found
        if value is None and lang != self.default_language:
            value = self._get_nested(
                self.translations.get(self.default_language, {}).get(namespace, {}),
                path,
            )

        # Handle not found
        if value is None:
            return options.get("default", key if self.fallback_to_key else "")

        # Handle pluralization
        if isinstance(value, dict) and "count" in options:
            count = options["count"]
            # Support 'one', 'few', 'many', 'other' forms
            if count == 0 and "zero" in value:
                value = value["zero"]
            elif count == 1 and "one" in value:
                value = value["one"]
            elif "other" in value:
                value = value["other"]
            else:
                # Use first available form
                value = next(iter(value.values()), key)

        # Ensure value is a string
        if not isinstance(value, str):
            return str(value)

        # Handle interpolation
        result = value
        for var_name, var_value in options.items():
            if var_name in ("default", "count"):
                continue
            # Support both {{var}} and {var} formats
            result = result.replace(f"{{{{{var_name}}}}}", str(var_value))
            result = result.replace(f"{{{var_name}}}", str(var_value))

        return result

    def has(self, key: str, language: Optional[str] = None) -> bool:
        """
        Check if a translation key exists.

        Args:
            key: Dot notation key
            language: Language to check (defaults to default_language)

        Returns:
            True if the key exists
        """
        lang = language if language in self.supported_languages else self.default_language

        parts = key.split(".")
        if len(parts) < 2:
            return False

        namespace = parts[0]
        path = parts[1:]

        value = self._get_nested(
            self.translations.get(lang, {}).get(namespace, {}),
            path,
        )
        return value is not None

    def is_supported(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in self.supported_languages

    def get_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self.supported_languages.copy()

    def get_namespace(
        self,
        namespace: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all translations for a namespace.

        Useful for sending translations to frontend.

        Args:
            namespace: Namespace name (e.g., 'common', 'auth')
            language: Language code

        Returns:
            Dictionary of all translations in the namespace
        """
        lang = language if language in self.supported_languages else self.default_language
        return self.translations.get(lang, {}).get(namespace, {}).copy()

    def get_all(self, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all translations for a language.

        Args:
            language: Language code

        Returns:
            Dictionary of all namespaces and their translations
        """
        lang = language if language in self.supported_languages else self.default_language
        return self.translations.get(lang, {}).copy()

    def reload(self) -> None:
        """Reload all translations from disk."""
        self.translations.clear()
        self.supported_languages = self._detect_languages()
        self._load_translations()
