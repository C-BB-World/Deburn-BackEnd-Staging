"""
FastAPI router for Media system endpoints.

Provides endpoints for image generation. TTS is used internally.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app_v2.auth.dependencies import require_auth
from app_v2.media.dependencies import get_image_service
from app_v2.media.services.image_service import ImageService
from app_v2.media.models import (
    GenerateImageRequest,
    GenerateImageFastRequest,
    GenerateImageToImageRequest,
    ImageResponse,
    ImageSizesResponse,
    ImageSizeInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image", tags=["media"])


@router.post("/generate", response_model=ImageResponse)
async def generate_image(
    request: GenerateImageRequest,
    user: Annotated[dict, Depends(require_auth)],
    image_service: Annotated[ImageService, Depends(get_image_service)],
):
    """Generate an image using FLUX dev model."""
    result = await image_service.generate_image(
        prompt=request.prompt,
        negative_prompt=request.negativePrompt,
        image_size=request.imageSize,
        num_inference_steps=request.numInferenceSteps,
        seed=request.seed,
        guidance_scale=request.guidanceScale,
        enable_safety_checker=request.enableSafetyChecker,
        use_cache=request.useCache,
    )

    return ImageResponse(**result)


@router.post("/generate-fast", response_model=ImageResponse)
async def generate_image_fast(
    request: GenerateImageFastRequest,
    user: Annotated[dict, Depends(require_auth)],
    image_service: Annotated[ImageService, Depends(get_image_service)],
):
    """Generate an image quickly using FLUX Schnell model."""
    result = await image_service.generate_image_fast(
        prompt=request.prompt,
        image_size=request.imageSize,
        num_inference_steps=request.numInferenceSteps,
        use_cache=request.useCache,
    )

    return ImageResponse(**result)


@router.post("/generate/transform", response_model=ImageResponse)
async def generate_image_to_image(
    request: GenerateImageToImageRequest,
    user: Annotated[dict, Depends(require_auth)],
    image_service: Annotated[ImageService, Depends(get_image_service)],
):
    """Transform an existing image based on a prompt."""
    result = await image_service.generate_image_to_image(
        prompt=request.prompt,
        image_url=request.imageUrl,
        strength=request.strength,
        image_size=request.imageSize,
        use_cache=request.useCache,
    )

    return ImageResponse(**result)


@router.get("/sizes", response_model=ImageSizesResponse)
async def get_image_sizes(
    image_service: Annotated[ImageService, Depends(get_image_service)],
):
    """Get available image size presets."""
    sizes = image_service.get_image_sizes()

    return ImageSizesResponse(
        sizes={name: ImageSizeInfo(**dims) for name, dims in sizes.items()}
    )
