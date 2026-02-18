"""
Whisper speech-to-text provider implementation.

Provides speech-to-text transcription using OpenAI's Whisper API.
Supports various audio formats including webm, mp4, wav, and mp3.

Example:
    from common.speech_processing import WhisperProvider

    whisper = WhisperProvider(api_key="your-api-key")
    transcript = await whisper.transcribe(audio_bytes, "recording.webm")
    print(transcript)
"""

from typing import Optional


class WhisperProvider:
    """
    OpenAI Whisper speech-to-text provider.

    Uses the OpenAI async client for API calls.
    Supports multiple audio formats and languages.
    """

    # Supported audio formats by Whisper API
    SUPPORTED_FORMATS = {"webm", "mp4", "mp3", "wav", "m4a", "ogg", "flac", "mpeg", "mpga", "oga"}

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        timeout: float = 60.0,
    ):
        """
        Initialize Whisper provider.

        Args:
            api_key: OpenAI API key
            model: Whisper model to use (default: whisper-1)
            timeout: Request timeout in seconds
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for Whisper. "
                "Install with: pip install openai"
            )

        self._api_key = api_key
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
        )
        self.model = model

    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        return bool(self._api_key)

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio to text using Whisper API.

        Args:
            audio_bytes: Raw audio data as bytes
            filename: Original filename (used to determine format)
            language: Optional language code (e.g., "en", "es")
            prompt: Optional prompt to guide transcription style

        Returns:
            Transcribed text string

        Raises:
            ValueError: If audio format is not supported
            Exception: If transcription fails
        """
        # Extract and validate file extension
        extension = self._get_extension(filename)
        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Prepare the file tuple for the API
        # Format: (filename, file_bytes, content_type)
        content_type = self._get_content_type(extension)
        file_tuple = (filename, audio_bytes, content_type)

        # Build transcription parameters
        params = {
            "model": self.model,
            "file": file_tuple,
            "response_format": "text",
        }

        if language:
            params["language"] = language

        if prompt:
            params["prompt"] = prompt

        # Call Whisper API
        transcript = await self.client.audio.transcriptions.create(**params)

        # Response format is "text", so transcript is a string
        return transcript.strip() if isinstance(transcript, str) else str(transcript).strip()

    def _get_extension(self, filename: str) -> str:
        """Extract lowercase file extension from filename."""
        if "." not in filename:
            return ""
        return filename.rsplit(".", 1)[-1].lower()

    def _get_content_type(self, extension: str) -> str:
        """Get MIME content type for audio extension."""
        content_types = {
            "webm": "audio/webm",
            "mp4": "audio/mp4",
            "mp3": "audio/mpeg",
            "mpeg": "audio/mpeg",
            "mpga": "audio/mpeg",
            "wav": "audio/wav",
            "m4a": "audio/m4a",
            "ogg": "audio/ogg",
            "oga": "audio/ogg",
            "flac": "audio/flac",
        }
        return content_types.get(extension, "audio/mpeg")
