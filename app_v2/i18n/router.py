"""
FastAPI router for i18n system endpoints.

Provides endpoints for language listing and translation reload.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.i18n.dependencies import get_language_config, get_i18n_service
from app_v2.i18n.services.language_config import LanguageConfig
from app_v2.i18n.services.i18n_service import I18nService
from app_v2.i18n.models import (
    LanguageResponse,
    LanguagesListResponse,
    ReloadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/i18n", tags=["i18n"])


@router.get("/languages", response_model=LanguagesListResponse)
async def get_languages(
    language_config: Annotated[LanguageConfig, Depends(get_language_config)],
):
    """
    Get list of supported languages.

    Returns all available languages with their codes and display names.
    """
    languages = language_config.get_supported_languages()

    return LanguagesListResponse(
        languages=[LanguageResponse(**lang) for lang in languages]
    )


@router.post("/reload", response_model=ReloadResponse)
async def reload_translations(
    i18n_service: Annotated[I18nService, Depends(get_i18n_service)],
):
    """
    Reload translations from source.

    Hot reload translations without server restart.
    Requires admin privileges in production.
    """
    result = i18n_service.reload()

    logger.info(
        f"Translations reloaded: {len(result['languages'])} languages, "
        f"{result['namespaces']} namespaces"
    )

    return ReloadResponse(**result)
