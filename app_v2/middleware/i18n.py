"""
i18n middleware for request-scoped language detection and translation.

Attaches language and translation helper to requests.
"""

import logging
from typing import Optional, Callable

from fastapi import Request

from app_v2.services.i18n.i18n_service import I18nService
from app_v2.services.i18n.language_config import LanguageConfig

logger = logging.getLogger(__name__)


class I18nMiddleware:
    """
    FastAPI middleware for request-scoped i18n.
    Attaches request.state.language and request.state.t to all requests.
    """

    def __init__(
        self,
        i18n_service: I18nService,
        language_config: LanguageConfig
    ):
        """
        Initialize I18nMiddleware.

        Args:
            i18n_service: Translation service instance
            language_config: For supported language lookup
        """
        self._i18n_service = i18n_service
        self._language_config = language_config

    async def __call__(self, request: Request, call_next: Callable):
        """
        Middleware function that attaches language to request.

        Attaches:
            - request.state.language: detected language code
            - request.state.t: translation function
        """
        language = self.get_language_from_request(request)
        request.state.language = language

        def translate(key: str, options: dict = None) -> str:
            return self._i18n_service.t(key, language, options)

        request.state.t = translate

        response = await call_next(request)
        return response

    def get_language_from_request(self, request: Request) -> str:
        """
        Detect user's preferred language from request.

        Args:
            request: HTTP request object

        Returns:
            Language code (e.g., 'en', 'sv')

        Priority:
            1. req.user.profile.preferredLanguage (if authenticated)
            2. Accept-Language header (primary language)
            3. Default language ('en')
        """
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            profile = user.get("profile", {})
            preferred = profile.get("preferredLanguage")
            if preferred and self._language_config.is_supported(preferred):
                return preferred

        accept_language = request.headers.get("Accept-Language")
        if accept_language:
            parsed = self._parse_accept_language(accept_language)
            if parsed and self._language_config.is_supported(parsed):
                return parsed

        return self._language_config.get_default_language()

    def _parse_accept_language(self, header: str) -> Optional[str]:
        """
        Parse Accept-Language header to extract primary language.

        Args:
            header: Accept-Language header value
                e.g., "sv-SE,sv;q=0.9,en;q=0.8"

        Returns:
            Primary language code (e.g., 'sv'), or None if invalid
        """
        if not header:
            return None

        primary = header.split(",")[0].strip()
        lang = primary.split(";")[0].strip()
        lang = lang.split("-")[0].strip()

        return lang.lower() if lang else None
