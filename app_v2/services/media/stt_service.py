"""
Speech-to-Text service using OpenAI Whisper API.

Provides audio transcription for voice input in coaching conversations.
Wraps the WhisperProvider from common/speech_processing.
"""

import logging
import os
from typing import Optional

from common.speech_processing.whisper import WhisperProvider
from common.utils.exceptions import ServerException, BadRequestException

logger = logging.getLogger(__name__)

# Max file size: 25MB (Whisper API limit)
MAX_FILE_SIZE = 25 * 1024 * 1024


class STTService:
    """
    Transcribes audio to text using OpenAI Whisper.
    Used by the Coach system for voice input.
    """

    def __init__(self):
        """Initialize STTService with WhisperProvider."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set; STT will be unavailable")
            self._provider = None
        else:
            self._provider = WhisperProvider(api_key=api_key)

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio data
            filename: Original filename (for format detection)
            language: Optional ISO 639-1 language code ("en", "sv")

        Returns:
            Transcribed text string

        Raises:
            ServerException: If Whisper API is not configured
            BadRequestException: If audio is invalid or empty
        """
        if self._provider is None:
            raise ServerException(
                message="Speech-to-text service not configured",
                code="STT_NOT_CONFIGURED",
            )

        if not audio_bytes or len(audio_bytes) == 0:
            raise BadRequestException(
                message="No audio data provided",
                code="EMPTY_AUDIO",
            )

        if len(audio_bytes) > MAX_FILE_SIZE:
            raise BadRequestException(
                message="Audio file too large (max 25MB)",
                code="FILE_TOO_LARGE",
            )

        try:
            transcript = await self._provider.transcribe(
                audio_bytes=audio_bytes,
                filename=filename,
                language=language,
            )

            if not transcript:
                raise BadRequestException(
                    message="Could not transcribe audio. Please try again.",
                    code="EMPTY_TRANSCRIPT",
                )

            logger.info(
                f"Transcribed {len(audio_bytes)} bytes -> {len(transcript)} chars"
            )
            return transcript

        except ValueError as e:
            raise BadRequestException(
                message=str(e),
                code="UNSUPPORTED_FORMAT",
            )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise ServerException(
                message="Transcription failed. Please try again.",
                code="TRANSCRIPTION_FAILED",
            )
