"""
Learning Router.

Handles learning modules and content.
"""

from fastapi import APIRouter, Depends, Query

from common.utils import success_response

from app_v1.models import User
from app_v1.dependencies import get_current_user

router = APIRouter()


# =============================================================================
# GET /api/learning/modules
# =============================================================================
@router.get("/modules")
async def get_modules(
    user: User = Depends(get_current_user),
    language: str = Query("en", pattern=r"^(en|sv)$"),
    category: str = Query(None),
):
    """
    Get available learning modules.
    """
    # Use user's preferred language if not specified
    lang = language or (user.profile.preferred_language if user.profile else "en")

    # TODO: Implement when ContentItem model is added to app/
    # For now, return placeholder modules

    modules = [
        {
            "id": "mod_stress_101",
            "title": "Understanding Stress" if lang == "en" else "Förstå stress",
            "description": (
                "Learn about the science of stress and its effects"
                if lang == "en"
                else "Lär dig om stressens vetenskap och dess effekter"
            ),
            "category": "wellness",
            "contentType": "audio",
            "lengthMinutes": 15,
            "status": "active",
        },
        {
            "id": "mod_leadership_101",
            "title": "Leadership Foundations" if lang == "en" else "Ledarskapets grunder",
            "description": (
                "Core principles of effective leadership"
                if lang == "en"
                else "Grundprinciper för effektivt ledarskap"
            ),
            "category": "leadership",
            "contentType": "audio",
            "lengthMinutes": 20,
            "status": "active",
        },
        {
            "id": "mod_delegation_101",
            "title": "The Art of Delegation" if lang == "en" else "Konsten att delegera",
            "description": (
                "Master the skill of effective delegation"
                if lang == "en"
                else "Bemästra färdigheten att delegera effektivt"
            ),
            "category": "leadership",
            "contentType": "audio",
            "lengthMinutes": 12,
            "status": "active",
        },
    ]

    # Filter by category if provided
    if category:
        modules = [m for m in modules if m["category"] == category]

    return success_response({
        "modules": modules,
    })
