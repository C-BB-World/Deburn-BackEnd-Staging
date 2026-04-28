"""
Hub content retriever.

Queries real published content from the hub database
instead of returning hardcoded fallback actions.
"""

import logging
from typing import List

from ..base import Action
from .base import ActionRetriever
from app_v2.services.hub.hub_content_service import HubContentService

logger = logging.getLogger(__name__)

# Content types that map to "exercise" actions; everything else is "learning"
_EXERCISE_CONTENT_TYPES = frozenset({"audio_exercise"})


class HubContentRetriever(ActionRetriever):
    """
    Retrieves actions from real hub content items.

    Queries HubContentService.get_for_coach() for published,
    coach-enabled content tagged with the detected topics.
    Results are sorted by coachPriority (descending) by the service.
    """

    def __init__(self, content_service: HubContentService):
        self._content_service = content_service

    async def retrieve(
        self,
        topics: List[str],
        language: str,
        limit: int = 2
    ) -> List[Action]:
        if not topics:
            return []

        try:
            items = await self._content_service.get_for_coach(topics)
        except Exception:
            logger.exception("Failed to retrieve hub content for topics %s", topics)
            return []

        actions: List[Action] = []
        for item in items:
            if len(actions) >= limit:
                break

            content_type = item.get("contentType", "")
            action_type = "exercise" if content_type in _EXERCISE_CONTENT_TYPES else "learning"

            title = item.get(f"title{'Sv' if language == 'sv' else 'En'}") or item.get("titleEn") or ""
            if not title:
                continue

            actions.append(Action(
                type=action_type,
                id=item["id"],
                label=title,
                metadata={
                    "contentType": content_type,
                    "category": item.get("category", ""),
                    "duration": f"{item.get('lengthMinutes', 0)} min" if item.get("lengthMinutes") else None,
                    "contentId": item["id"],
                    "purpose": item.get("purpose"),
                },
            ))

        return actions
