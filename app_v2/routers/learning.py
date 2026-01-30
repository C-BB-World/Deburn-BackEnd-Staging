import logging
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response

from app_v2.dependencies import require_auth, get_hub_db
from common.utils import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["learning"])


def _compute_has_content(item: dict) -> bool:
    content_type = item.get("contentType", "")

    if content_type == "text_article":
        text = item.get("textContentEn", "")
        return bool(text and text.strip())
    elif content_type in ("audio_article", "audio_exercise"):
        return bool(item.get("audioFileEn"))
    elif content_type == "video_link":
        return bool(item.get("videoUrl"))

    return False


@router.get("/content")
async def get_learning_content(
    user: Annotated[dict, Depends(require_auth)],
):
    db = get_hub_db()
    collection = db["contentitems"]

    # Exclude binary data from query for performance
    projection = {
        "audioDataEn": 0,
        "audioDataSv": 0,
        "articleImageEn": 0,
        "articleImageSv": 0,
    }
    cursor = collection.find({"status": "published"}, projection)
    cursor = cursor.sort("sortOrder", 1)
    raw_items = await cursor.to_list(length=500)

    items = []
    for item in raw_items:
        # Check for article image by mime type presence (single field, same for En/Sv)
        has_image = bool(item.get("articleImageMimeType"))

        content_item = {
            "id": str(item.get("_id", "")),
            "contentType": item.get("contentType"),
            "category": item.get("category"),
            "titleEn": item.get("titleEn"),
            "titleSv": item.get("titleSv"),
            "lengthMinutes": item.get("lengthMinutes"),
            "audioFileEn": item.get("audioFileEn"),
            "audioFileSv": item.get("audioFileSv"),
            "textContentEn": item.get("textContentEn"),
            "textContentSv": item.get("textContentSv"),
            "videoUrl": item.get("videoUrl"),
            "videoEmbedCode": item.get("videoEmbedCode"),
            "videoAvailableInEn": item.get("videoAvailableInEn"),
            "videoAvailableInSv": item.get("videoAvailableInSv"),
            "purpose": item.get("purpose"),
            "sortOrder": item.get("sortOrder"),
            "hasContent": _compute_has_content(item),
            "hasImageEn": has_image,
            "hasImageSv": has_image,
            "hasImage": has_image,
        }
        items.append(content_item)

    return success_response({"items": items})


@router.get("/content/{content_id}")
async def get_content_item(
    content_id: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get a single content item by ID."""
    db = get_hub_db()
    collection = db["contentitems"]

    try:
        item = await collection.find_one(
            {"_id": ObjectId(content_id)},
            {"audioDataEn": 0, "audioDataSv": 0, "articleImageEn": 0, "articleImageSv": 0}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid content ID")

    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Check for article image by mime type presence (single field, same for En/Sv)
    has_image = bool(item.get("articleImageMimeType"))

    content_item = {
        "id": str(item.get("_id", "")),
        "contentType": item.get("contentType"),
        "category": item.get("category"),
        "titleEn": item.get("titleEn"),
        "titleSv": item.get("titleSv"),
        "lengthMinutes": item.get("lengthMinutes"),
        "audioFileEn": item.get("audioFileEn"),
        "audioFileSv": item.get("audioFileSv"),
        "textContentEn": item.get("textContentEn"),
        "textContentSv": item.get("textContentSv"),
        "videoUrl": item.get("videoUrl"),
        "videoEmbedCode": item.get("videoEmbedCode"),
        "videoAvailableInEn": item.get("videoAvailableInEn"),
        "videoAvailableInSv": item.get("videoAvailableInSv"),
        "purpose": item.get("purpose"),
        "sortOrder": item.get("sortOrder"),
        "hasContent": _compute_has_content(item),
        "hasImageEn": has_image,
        "hasImageSv": has_image,
        "hasImage": has_image,
    }

    return success_response({"item": content_item})


@router.get("/content/{content_id}/audio/{language}")
async def stream_audio(
    content_id: str,
    language: str,
    user: Annotated[dict, Depends(require_auth)],
):
    if language not in ("en", "sv"):
        raise HTTPException(status_code=400, detail="Language must be 'en' or 'sv'")

    db = get_hub_db()
    collection = db["contentitems"]

    lang_suffix = language.capitalize()
    data_field = f"audioData{lang_suffix}"
    mime_field = f"audioMimeType{lang_suffix}"

    item = await collection.find_one(
        {"_id": ObjectId(content_id)},
        {data_field: 1, mime_field: 1}
    )

    if not item or not item.get(data_field):
        raise HTTPException(status_code=404, detail="Audio not found")

    audio_data = item[data_field]
    mime_type = item.get(mime_field, "audio/mpeg")

    return Response(
        content=audio_data,
        media_type=mime_type,
        headers={
            "Content-Disposition": "inline; filename=audio.mp3",
            "Accept-Ranges": "bytes",
        }
    )


# Create a separate router for article images at /api/article-image
article_image_router = APIRouter(prefix="/article-image", tags=["learning"])


@article_image_router.get("/{content_id}/{language}")
async def get_article_image(
    content_id: str,
    language: str,
    user: Annotated[dict, Depends(require_auth)],
):
    """Get article image for a content item."""
    if language not in ("en", "sv"):
        raise HTTPException(status_code=400, detail="Language must be 'en' or 'sv'")

    db = get_hub_db()
    collection = db["contentitems"]

    # Fetch both language images and the single mime type field
    try:
        item = await collection.find_one(
            {"_id": ObjectId(content_id)},
            {"articleImageEn": 1, "articleImageSv": 1, "articleImageMimeType": 1}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid content ID")

    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Get image data for requested language, fallback to English
    if language == "sv":
        image_data = item.get("articleImageSv") or item.get("articleImageEn")
    else:
        image_data = item.get("articleImageEn")

    mime_type = item.get("articleImageMimeType", "image/jpeg")

    if not image_data:
        raise HTTPException(status_code=404, detail="Article image not found")

    return Response(
        content=image_data,
        media_type=mime_type,
        headers={
            "Cache-Control": "public, max-age=86400",
        }
    )
