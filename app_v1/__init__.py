"""
BrainBank application-specific code.

This package contains all BrainBank-specific implementations:
- models: Database document schemas (User, CheckIn, Organization, etc.)
- services: Business logic (coach service, etc.)
- locales: Translation files (en, sv)
- config: Application settings

Uses generic infrastructure from the common/ package.
"""

from app_v1.config import settings

__all__ = ["settings"]
