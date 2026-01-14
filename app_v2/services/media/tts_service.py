"""
Text-to-Speech service using ElevenLabs API.

Provides speech generation with optional caching to avoid duplicate API costs.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.utils.exceptions import ServerException

logger = logging.getLogger(__name__)


VOICE_MAPPINGS = {
    # Custom voices
    "Aria": "fO844Om1VZLpw8IpZj3T",
    "Leoni Vergara": "pBZVCk298iJlHAcHQwLr",
    "Ana-Rita": "wJqPPQ618aTW29mptyoc",
    "Andromeda": "HoU1B9WLbSprzhhX34v0",
    "LavenderLessons": "cL2JBnZF7ILVaQ86EQMQ",
    # Standard voices
    "Sarah": "EXAVITQu4vr4xnSDxMaL",
    "Laura": "FGY2WhTYpPnrIDTdsKH5",
    "Alice": "Xb7hH8MSUJpSbSDYk0k2",
    "Matilda": "XrExE9yKIg1WjnnlVkGX",
    "Jessica": "cgSgspJ2msm6clMCkdW9",
    "Lily": "pFZP5JQG7iQjIQuC4Bku",
    "Roger": "CwhRBWXzGAHq8TQ4Fs17",
    "Charlie": "IKne3meq5aSn9XLyUdCD",
    "George": "JBFqnCBsd6RMkjVDRZzb",
}


class TTSService:
    """
    Generates speech audio from text using ElevenLabs API.
    Used internally by Coach system for voice mode.
    """

    def __init__(
        self,
        db: Optional[AsyncIOMotorDatabase] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize TTSService.

        Args:
            db: MongoDB connection for caching (optional)
            config: Configuration dict with:
                - caching_enabled: bool (default: False)
                - cache_ttl_seconds: int (default: 86400 = 24 hours)
        """
        self._db = db
        self._cache_collection = db["ttsCache"] if db is not None else None

        config = config or {}
        self._caching_enabled = config.get("caching_enabled", False)
        self._cache_ttl_seconds = config.get("cache_ttl_seconds", 86400)

        self._api_key = os.getenv("ELEVENLABS_API_KEY")
        self._base_url = "https://api.elevenlabs.io/v1"

    async def generate_speech(
        self,
        text: str,
        voice: str = "Aria",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        speed: float = 1.0,
        style: float = 0,
        model_id: str = "eleven_multilingual_v2",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate speech audio from text.

        Args:
            text: Text to convert to speech
            voice: Voice name or ID
            stability: Voice stability (0-1)
            similarity_boost: Similarity boost (0-1)
            speed: Speech speed (0.7-1.2)
            style: Style exaggeration (0-1)
            model_id: ElevenLabs model to use
            use_cache: Whether to use cache (if caching enabled)

        Returns:
            dict with keys:
                - success: bool
                - audioBuffer: bytes (MP3)
                - contentType: str ("audio/mpeg")
                - voiceId: str
                - voiceName: str
                - fromCache: bool
        """
        if not self._api_key:
            raise ServerException(
                message="ElevenLabs API key not configured",
                code="API_KEY_MISSING"
            )

        voice_id = self.get_voice_id(voice)
        voice_name = voice if voice in VOICE_MAPPINGS else "Custom"

        params = {
            "text": text,
            "voice": voice_id,
            "stability": stability,
            "similarity_boost": similarity_boost,
            "speed": speed,
            "style": style,
            "model_id": model_id,
        }

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            cache_key = self._generate_cache_key(params)
            cached = await self._check_cache(cache_key)

            if cached:
                logger.debug(f"TTS cache hit for text: {text[:50]}...")
                return {
                    "success": True,
                    "audioBuffer": cached["audioData"],
                    "contentType": cached["contentType"],
                    "voiceId": voice_id,
                    "voiceName": voice_name,
                    "fromCache": True,
                }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self._api_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json={
                        "text": text,
                        "model_id": model_id,
                        "voice_settings": {
                            "stability": stability,
                            "similarity_boost": similarity_boost,
                            "style": style,
                            "use_speaker_boost": True,
                        },
                    },
                    params={"output_format": "mp3_44100_128"},
                    timeout=60.0
                )

                if response.status_code != 200:
                    logger.error(f"ElevenLabs API error: {response.status_code}")
                    raise ServerException(
                        message="Failed to generate speech",
                        code="GENERATION_FAILED"
                    )

                audio_buffer = response.content

        except httpx.RequestError as e:
            logger.error(f"ElevenLabs request error: {e}")
            raise ServerException(
                message="Failed to connect to ElevenLabs API",
                code="GENERATION_FAILED"
            )

        if self._caching_enabled and use_cache and self._cache_collection is not None:
            await self._store_in_cache(
                cache_key,
                {
                    "audioData": audio_buffer,
                    "contentType": "audio/mpeg",
                    "voiceId": voice_id,
                    "voiceName": voice_name,
                    "textLength": len(text),
                    "parameters": params,
                }
            )

        return {
            "success": True,
            "audioBuffer": audio_buffer,
            "contentType": "audio/mpeg",
            "voiceId": voice_id,
            "voiceName": voice_name,
            "fromCache": False,
        }

    def get_voice_id(self, voice: str) -> str:
        """
        Get voice ID from name or return as-is if already an ID.

        Args:
            voice: Voice name or ID

        Returns:
            Voice ID string
        """
        return VOICE_MAPPINGS.get(voice, voice)

    def get_available_voices(self) -> Dict[str, str]:
        """
        Get available voice name to ID mappings.

        Returns:
            Dict of voice names to IDs
        """
        return VOICE_MAPPINGS.copy()

    async def list_account_voices(self) -> list:
        """
        List voices from ElevenLabs account.

        Returns:
            List of voice objects from API
        """
        if not self._api_key:
            raise ServerException(
                message="ElevenLabs API key not configured",
                code="API_KEY_MISSING"
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/voices",
                    headers={"xi-api-key": self._api_key},
                    timeout=30.0
                )

                if response.status_code != 200:
                    raise ServerException(
                        message="Failed to fetch voices",
                        code="API_ERROR"
                    )

                data = response.json()
                return data.get("voices", [])

        except httpx.RequestError as e:
            logger.error(f"ElevenLabs request error: {e}")
            raise ServerException(
                message="Failed to connect to ElevenLabs API",
                code="API_ERROR"
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
            data: Data to cache (audio buffer reference)
        """
        if self._cache_collection is None:
            return

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._cache_ttl_seconds)

        doc = {
            "cacheKey": cache_key,
            "audioData": data["audioData"],
            "contentType": data["contentType"],
            "voiceId": data["voiceId"],
            "voiceName": data["voiceName"],
            "textLength": data["textLength"],
            "parameters": data["parameters"],
            "createdAt": now,
            "expiresAt": expires_at,
        }

        await self._cache_collection.update_one(
            {"cacheKey": cache_key},
            {"$set": doc},
            upsert=True
        )

        logger.debug(f"Stored TTS in cache: {cache_key[:16]}...")
