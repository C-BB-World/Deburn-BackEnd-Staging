"""
Coach configuration service.

Manages AI coach configuration including prompts, settings, and safety config.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class CoachConfigService:
    """
    Manages AI coach configuration.
    Prompts stored in filesystem, settings in database.
    """

    def __init__(
        self,
        hub_db: AsyncIOMotorDatabase,
        prompts_dir: Optional[str] = None,
        knowledge_base_dir: Optional[str] = None
    ):
        """
        Initialize CoachConfigService.

        Args:
            hub_db: Hub MongoDB database connection
            prompts_dir: Directory for system prompts
            knowledge_base_dir: Directory for knowledge base files
        """
        self._db = hub_db
        self._settings_collection = hub_db["hubSettings"]

        base_dir = Path(__file__).parent.parent.parent.parent
        self._prompts_dir = Path(prompts_dir) if prompts_dir else base_dir / "prompts" / "system"
        self._knowledge_dir = Path(knowledge_base_dir) if knowledge_base_dir else base_dir / "knowledge-base"

    async def get_prompts(self) -> Dict[str, Dict[str, str]]:
        """
        Get all system prompts by language.

        Returns:
            {'en': {'prompt_name': 'content'}, 'sv': {...}}
        """
        result = {"en": {}, "sv": {}}

        for lang in ["en", "sv"]:
            lang_dir = self._prompts_dir / lang

            if not lang_dir.exists():
                continue

            for prompt_file in lang_dir.glob("*.md"):
                prompt_name = prompt_file.stem
                try:
                    content = prompt_file.read_text(encoding="utf-8")
                    result[lang][prompt_name] = content
                except Exception as e:
                    logger.warning(f"Failed to read prompt {prompt_file}: {e}")

        return result

    async def update_prompt(
        self,
        language: str,
        prompt_name: str,
        content: str
    ) -> None:
        """
        Update a system prompt file.

        Args:
            language: 'en' or 'sv'
            prompt_name: Name of the prompt file (without .md)
            content: New prompt content
        """
        if language not in ("en", "sv"):
            raise ValidationException(
                message="Language must be 'en' or 'sv'",
                code="INVALID_LANGUAGE"
            )

        prompt_path = self._prompts_dir / language / f"{prompt_name}.md"

        if not prompt_path.exists():
            raise NotFoundException(
                message=f"Prompt '{prompt_name}' not found for language '{language}'",
                code="PROMPT_NOT_FOUND"
            )

        try:
            prompt_path.write_text(content, encoding="utf-8")
            logger.info(f"Updated prompt: {language}/{prompt_name}")
        except Exception as e:
            logger.error(f"Failed to write prompt: {e}")
            raise ValidationException(
                message="Failed to save prompt",
                code="SAVE_FAILED"
            )

    async def get_exercises(self) -> Dict[str, Any]:
        """
        Get exercises and modules from JSON file.

        Returns:
            Dict with exercises and modules
        """
        exercises_file = self._knowledge_dir / "exercises" / "exercises.json"

        if not exercises_file.exists():
            return {"exercises": [], "modules": []}

        try:
            content = exercises_file.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to read exercises file: {e}")
            return {"exercises": [], "modules": []}

    async def update_exercises(
        self,
        exercises: List[Dict[str, Any]],
        modules: List[Dict[str, Any]]
    ) -> None:
        """
        Update exercises and modules JSON file.

        Args:
            exercises: List of exercise objects
            modules: List of module objects
        """
        exercises_dir = self._knowledge_dir / "exercises"
        exercises_dir.mkdir(parents=True, exist_ok=True)

        exercises_file = exercises_dir / "exercises.json"

        data = {
            "exercises": exercises,
            "modules": modules,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        try:
            content = json.dumps(data, indent=2, default=str)
            exercises_file.write_text(content, encoding="utf-8")
            logger.info("Updated exercises file")
        except Exception as e:
            logger.error(f"Failed to write exercises file: {e}")
            raise ValidationException(
                message="Failed to save exercises",
                code="SAVE_FAILED"
            )

    async def get_coach_settings(self) -> Dict[str, Any]:
        """
        Get coach settings (creates default if none).

        Returns:
            Coach settings dict
        """
        settings = await self._settings_collection.find_one({
            "key": "coachSettings"
        })

        if not settings:
            now = datetime.now(timezone.utc)
            settings = {
                "key": "coachSettings",
                "dailyExchangeLimit": 15,
                "deletionGracePeriodDays": 30,
                "createdAt": now,
                "updatedAt": now,
            }
            await self._settings_collection.insert_one(settings)

        return self._format_settings(settings)

    async def update_coach_settings(
        self,
        daily_exchange_limit: Optional[int] = None,
        deletion_grace_period_days: Optional[int] = None,
        admin_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update coach settings.

        Args:
            daily_exchange_limit: 1-100 exchanges per user per day
            deletion_grace_period_days: Grace period for account deletion
            admin_email: Who made the change

        Returns:
            Updated settings dict
        """
        updates = {"updatedAt": datetime.now(timezone.utc)}

        if admin_email:
            updates["updatedBy"] = admin_email

        if daily_exchange_limit is not None:
            if daily_exchange_limit < 1 or daily_exchange_limit > 100:
                raise ValidationException(
                    message="Daily exchange limit must be between 1 and 100",
                    code="VALIDATION_ERROR"
                )
            updates["dailyExchangeLimit"] = daily_exchange_limit

        if deletion_grace_period_days is not None:
            if deletion_grace_period_days < 1 or deletion_grace_period_days > 365:
                raise ValidationException(
                    message="Deletion grace period must be between 1 and 365 days",
                    code="VALIDATION_ERROR"
                )
            updates["deletionGracePeriodDays"] = deletion_grace_period_days

        result = await self._settings_collection.find_one_and_update(
            {"key": "coachSettings"},
            {"$set": updates},
            upsert=True,
            return_document=True
        )

        logger.info(f"Updated coach settings by {admin_email}")
        return self._format_settings(result)

    def get_safety_config(self) -> Dict[str, Any]:
        """
        Get safety keyword configuration (read-only).

        Returns:
            Dict with escalation levels and keywords
        """
        return {
            "levels": [
                {
                    "level": 0,
                    "name": "Normal",
                    "action": "Continue coaching",
                    "description": "Default state, no escalation needed",
                },
                {
                    "level": 1,
                    "name": "Soft Escalation",
                    "action": "Continue with caution",
                    "keywords": ["exhausted", "overwhelmed", "can't sleep", "burnout", "frustrated"],
                },
                {
                    "level": 2,
                    "name": "Professional Referral",
                    "action": "Redirect to expert",
                    "keywords": ["legal rights", "medical symptoms", "financial stress", "lawsuit", "fired"],
                },
                {
                    "level": 3,
                    "name": "Crisis",
                    "action": "Stop coaching immediately",
                    "keywords": ["suicide", "self-harm", "panic attack", "abuse", "kill", "hurt myself"],
                },
            ],
            "hard_boundaries": [
                "Medical advice",
                "Legal advice",
                "Financial advice",
                "Mental health diagnosis",
            ],
        }

    def _format_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Format settings for response."""
        return {
            "id": str(settings.get("_id", "")),
            "key": settings.get("key"),
            "dailyExchangeLimit": settings.get("dailyExchangeLimit", 15),
            "deletionGracePeriodDays": settings.get("deletionGracePeriodDays", 30),
            "updatedAt": settings.get("updatedAt"),
            "updatedBy": settings.get("updatedBy"),
            "createdAt": settings.get("createdAt"),
        }
