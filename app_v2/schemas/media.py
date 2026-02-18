"""
Pydantic models for Media system request/response validation.

Defines schemas for TTS and image generation.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class GenerateSpeechRequest(BaseModel):
    """Request to generate speech from text."""
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(default="Aria")
    stability: float = Field(default=0.5, ge=0, le=1)
    similarityBoost: float = Field(default=0.75, ge=0, le=1)
    speed: float = Field(default=1.0, ge=0.7, le=1.2)
    style: float = Field(default=0, ge=0, le=1)
    modelId: str = Field(default="eleven_multilingual_v2")
    useCache: bool = Field(default=True)


class SpeechResponse(BaseModel):
    """TTS generation response."""
    success: bool
    contentType: str
    voiceId: str
    voiceName: str
    fromCache: bool


class GenerateImageRequest(BaseModel):
    """Request to generate an image."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    negativePrompt: str = Field(default="")
    imageSize: str = Field(default="landscape_4_3")
    numInferenceSteps: int = Field(default=28, ge=1, le=50)
    seed: Optional[int] = None
    guidanceScale: float = Field(default=3.5, ge=1, le=20)
    enableSafetyChecker: bool = Field(default=True)
    useCache: bool = Field(default=True)


class GenerateImageFastRequest(BaseModel):
    """Request for fast image generation."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    imageSize: str = Field(default="landscape_4_3")
    numInferenceSteps: int = Field(default=4, ge=1, le=12)
    useCache: bool = Field(default=True)


class GenerateImageToImageRequest(BaseModel):
    """Request for image-to-image transformation."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    imageUrl: str = Field(..., min_length=1)
    strength: float = Field(default=0.75, ge=0, le=1)
    imageSize: str = Field(default="landscape_4_3")
    useCache: bool = Field(default=True)


class ImageResponse(BaseModel):
    """Image generation response."""
    success: bool
    imageUrl: str
    width: int
    height: int
    seed: Optional[int] = None
    prompt: str
    requestId: str
    model: str
    fromCache: bool


class ImageSizeInfo(BaseModel):
    """Image size preset information."""
    width: int
    height: int


class ImageSizesResponse(BaseModel):
    """Available image sizes response."""
    sizes: Dict[str, ImageSizeInfo]


class VoiceInfo(BaseModel):
    """Voice information."""
    id: str
    name: str
    voiceType: str = Field(default="standard")


class VoicesResponse(BaseModel):
    """Available voices response."""
    voices: Dict[str, str]
