"""
Image generation service using FAL.ai FLUX models.

Provides standard, fast, and image-to-image generation with optional caching.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ServerException, ValidationException

logger = logging.getLogger(__name__)


IMAGE_SIZES = {
    "square_hd": {"width": 1024, "height": 1024},
    "square": {"width": 512, "height": 512},
    "portrait_4_3": {"width": 768, "height": 1024},
    "portrait_16_9": {"width": 576, "height": 1024},
    "landscape_4_3": {"width": 1024, "height": 768},
    "landscape_16_9": {"width": 1024, "height": 576},
}


class ImageService:
    """
    Generates images using FAL.ai FLUX models.
    Supports standard, fast, and image-to-image generation.
    """

    def __init__(
        self,
        db: Optional[AsyncIOMotorDatabase] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize ImageService.

        Args:
            db: MongoDB connection for caching (optional)
            config: Configuration dict with:
                - caching_enabled: bool (default: False)
                - cache_ttl_seconds: int (default: 86400 = 24 hours)
                - store_binary: bool (default: False, store URL only)
        """
        self._db = db
        self._cache_collection = db["imageCache"] if db is not None else None

        config = config or {}
        self._caching_enabled = config.get("caching_enabled", False)
        self._cache_ttl_seconds = config.get("cache_ttl_seconds", 86400)
        self._store_binary = config.get("store_binary", False)

        self._api_key = os.getenv("FAL_KEY")
        self._base_url = "https://fal.run"

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        image_size: str = "landscape_4_3",
        num_inference_steps: int = 28,
        seed: Optional[int] = None,
        guidance_scale: float = 3.5,
        enable_safety_checker: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate image using FLUX dev model.

        Args:
            prompt: Text description of image
            negative_prompt: What to avoid
            image_size: Size preset
            num_inference_steps: Quality steps (more = better)
            seed: Random seed for reproducibility
            guidance_scale: How closely to follow prompt
            enable_safety_checker: Enable content filtering
            use_cache: Whether to use cache (if caching enabled)

        Returns:
            dict with keys:
                - success: bool
                - imageUrl: str
                - width: int
                - height: int
                - seed: int
                - prompt: str
                - requestId: str
                - fromCache: bool
        """
        if not prompt:
            raise ValidationException(
                message="Prompt is required",
                code="VALIDATION_ERROR"
            )

        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": image_size,
            "num_inference_steps": num_inference_steps,
            "seed": seed,
            "guidance_scale": guidance_scale,
            "model": "flux-dev",
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            cache_key = self._generate_cache_key(params)
            cached = await self._check_cache(cache_key)

            if cached:
                logger.debug(f"Image cache hit for prompt: {prompt[:50]}...")
                return {
                    "success": True,
                    "imageUrl": cached["imageUrl"],
                    "width": cached["width"],
                    "height": cached["height"],
                    "seed": cached["seed"],
                    "prompt": prompt,
                    "requestId": str(cached["_id"]),
                    "model": "flux-dev",
                    "fromCache": True,
                }

        result = await self._call_fal_api(
            endpoint="fal-ai/flux/dev",
            payload={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "image_size": image_size,
                "num_inference_steps": num_inference_steps,
                "seed": seed,
                "guidance_scale": guidance_scale,
                "enable_safety_checker": enable_safety_checker,
            }
        )

        size = IMAGE_SIZES.get(image_size, IMAGE_SIZES["landscape_4_3"])
        image_data = result.get("images", [{}])[0]

        response = {
            "success": True,
            "imageUrl": image_data.get("url", ""),
            "width": image_data.get("width", size["width"]),
            "height": image_data.get("height", size["height"]),
            "seed": result.get("seed", seed),
            "prompt": prompt,
            "requestId": result.get("request_id", ""),
            "model": "flux-dev",
            "fromCache": False,
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            await self._store_in_cache(cache_key, {
                "imageUrl": response["imageUrl"],
                "width": response["width"],
                "height": response["height"],
                "seed": response["seed"],
                "model": "flux-dev",
                "parameters": params,
            })

        return response

    async def generate_image_fast(
        self,
        prompt: str,
        image_size: str = "landscape_4_3",
        num_inference_steps: int = 4,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate image quickly using FLUX Schnell model.

        Args:
            prompt: Text description of image
            image_size: Size preset
            num_inference_steps: Steps (1-12 for schnell)
            use_cache: Whether to use cache

        Returns:
            dict with image result + model: "flux-schnell"
        """
        if not prompt:
            raise ValidationException(
                message="Prompt is required",
                code="VALIDATION_ERROR"
            )

        num_inference_steps = min(max(num_inference_steps, 1), 12)

        params = {
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": num_inference_steps,
            "model": "flux-schnell",
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            cache_key = self._generate_cache_key(params)
            cached = await self._check_cache(cache_key)

            if cached:
                logger.debug(f"Image (fast) cache hit for prompt: {prompt[:50]}...")
                return {
                    "success": True,
                    "imageUrl": cached["imageUrl"],
                    "width": cached["width"],
                    "height": cached["height"],
                    "seed": cached.get("seed"),
                    "prompt": prompt,
                    "requestId": str(cached["_id"]),
                    "model": "flux-schnell",
                    "fromCache": True,
                }

        result = await self._call_fal_api(
            endpoint="fal-ai/flux/schnell",
            payload={
                "prompt": prompt,
                "image_size": image_size,
                "num_inference_steps": num_inference_steps,
            }
        )

        size = IMAGE_SIZES.get(image_size, IMAGE_SIZES["landscape_4_3"])
        image_data = result.get("images", [{}])[0]

        response = {
            "success": True,
            "imageUrl": image_data.get("url", ""),
            "width": image_data.get("width", size["width"]),
            "height": image_data.get("height", size["height"]),
            "seed": result.get("seed"),
            "prompt": prompt,
            "requestId": result.get("request_id", ""),
            "model": "flux-schnell",
            "fromCache": False,
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            await self._store_in_cache(cache_key, {
                "imageUrl": response["imageUrl"],
                "width": response["width"],
                "height": response["height"],
                "seed": response["seed"],
                "model": "flux-schnell",
                "parameters": params,
            })

        return response

    async def generate_image_to_image(
        self,
        prompt: str,
        image_url: str,
        strength: float = 0.75,
        image_size: str = "landscape_4_3",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Transform existing image based on prompt.

        Args:
            prompt: Text description of transformation
            image_url: Source image URL
            strength: Transformation strength (0-1)
            image_size: Output size preset
            use_cache: Whether to use cache

        Returns:
            dict with image result + model: "flux-dev-i2i"
        """
        if not prompt:
            raise ValidationException(
                message="Prompt is required",
                code="VALIDATION_ERROR"
            )

        if not image_url:
            raise ValidationException(
                message="Image URL is required",
                code="VALIDATION_ERROR"
            )

        strength = min(max(strength, 0), 1)

        params = {
            "prompt": prompt,
            "image_url": image_url,
            "strength": strength,
            "image_size": image_size,
            "model": "flux-dev-i2i",
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            cache_key = self._generate_cache_key(params)
            cached = await self._check_cache(cache_key)

            if cached:
                logger.debug(f"Image (i2i) cache hit for prompt: {prompt[:50]}...")
                return {
                    "success": True,
                    "imageUrl": cached["imageUrl"],
                    "width": cached["width"],
                    "height": cached["height"],
                    "seed": cached.get("seed"),
                    "prompt": prompt,
                    "requestId": str(cached["_id"]),
                    "model": "flux-dev-i2i",
                    "fromCache": True,
                }

        result = await self._call_fal_api(
            endpoint="fal-ai/flux/dev/image-to-image",
            payload={
                "prompt": prompt,
                "image_url": image_url,
                "strength": strength,
                "image_size": image_size,
            }
        )

        size = IMAGE_SIZES.get(image_size, IMAGE_SIZES["landscape_4_3"])
        image_data = result.get("images", [{}])[0]

        response = {
            "success": True,
            "imageUrl": image_data.get("url", ""),
            "width": image_data.get("width", size["width"]),
            "height": image_data.get("height", size["height"]),
            "seed": result.get("seed"),
            "prompt": prompt,
            "requestId": result.get("request_id", ""),
            "model": "flux-dev-i2i",
            "fromCache": False,
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            await self._store_in_cache(cache_key, {
                "imageUrl": response["imageUrl"],
                "width": response["width"],
                "height": response["height"],
                "seed": response["seed"],
                "model": "flux-dev-i2i",
                "parameters": params,
            })

        return response

    def get_image_sizes(self) -> Dict[str, Dict[str, int]]:
        """
        Get available image size presets.

        Returns:
            Dict of preset names to dimensions
        """
        return IMAGE_SIZES.copy()

    async def _call_fal_api(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call FAL.ai API endpoint.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            API response dict
        """
        if not self._api_key:
            raise ServerException(
                message="FAL.ai API key not configured",
                code="API_KEY_MISSING"
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/{endpoint}",
                    headers={
                        "Authorization": f"Key {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=120.0
                )

                if response.status_code != 200:
                    logger.error(
                        f"FAL.ai API error: {response.status_code} - {response.text}"
                    )
                    raise ServerException(
                        message="Failed to generate image",
                        code="GENERATION_FAILED"
                    )

                return response.json()

        except httpx.RequestError as e:
            logger.error(f"FAL.ai request error: {e}")
            raise ServerException(
                message="Failed to connect to FAL.ai API",
                code="GENERATION_FAILED"
            )

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """
        Generate cache key from parameters.

        Args:
            params: All generation parameters

        Returns:
            SHA-256 hash string
        """
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()

    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Check cache for existing entry.

        Args:
            cache_key: Hash key

        Returns:
            Cached data or None
        """
        if self._cache_collection is None:
            return None

        entry = await self._cache_collection.find_one({
            "cacheKey": cache_key,
            "expiresAt": {"$gt": datetime.now(timezone.utc)}
        })

        return entry

    async def _store_in_cache(
        self,
        cache_key: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Store result in cache with TTL.

        Args:
            cache_key: Hash key
            data: Data to cache (URL or binary reference)
        """
        if self._cache_collection is None:
            return

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._cache_ttl_seconds)

        doc = {
            "cacheKey": cache_key,
            "imageUrl": data["imageUrl"],
            "width": data["width"],
            "height": data["height"],
            "seed": data.get("seed"),
            "model": data["model"],
            "parameters": data["parameters"],
            "createdAt": now,
            "expiresAt": expires_at,
        }

        await self._cache_collection.update_one(
            {"cacheKey": cache_key},
            {"$set": doc},
            upsert=True
        )

        logger.debug(f"Stored image in cache: {cache_key[:16]}...")
