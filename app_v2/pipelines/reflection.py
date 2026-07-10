"""
Reflection pipeline functions.

Lightweight orchestration for reflection operations.
"""

import logging
from typing import Any, Dict

from app_v2.services.reflection import ReflectionService

logger = logging.getLogger(__name__)


async def get_reflections_pipeline(
    reflection_service: ReflectionService,
    user_id: str,
    page: int,
    limit: int,
) -> Dict[str, Any]:
    """Fetch a paginated page of reflections for a user."""
    skip = (page - 1) * limit
    return await reflection_service.get_reflections(user_id, skip, limit)


async def update_reflection_pipeline(
    reflection_service: ReflectionService,
    reflection_id: str,
    user_id: str,
    new_text: str,
) -> Dict[str, Any]:
    """Update a reflection's text and return the updated document."""
    return await reflection_service.update_reflection(reflection_id, user_id, new_text)
