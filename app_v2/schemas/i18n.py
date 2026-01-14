"""
Pydantic models for i18n system request/response validation.

Defines schemas for language operations.
"""

from typing import List
from pydantic import BaseModel, Field


class LanguageResponse(BaseModel):
    """Individual language in API responses."""
    code: str = Field(..., description="ISO 639-1 language code")
    name: str = Field(..., description="Display name")
    isDefault: bool = Field(default=False)


class LanguagesListResponse(BaseModel):
    """Response for listing supported languages."""
    languages: List[LanguageResponse]


class ReloadResponse(BaseModel):
    """Response for reloading translations."""
    success: bool
    languages: List[str]
    namespaces: int
