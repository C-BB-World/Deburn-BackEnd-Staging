# Media Services System

## Description

The Media Services System provides AI-powered media generation including text-to-speech audio (ElevenLabs) and image generation (FAL.ai). Both services include optional caching to prevent duplicate API calls.

**Responsibilities:**
- Generate audio from text (TTS)
- Generate images from prompts
- Cache lookups to avoid duplicate API costs
- Support multiple voices and image modes
- Provide configurable generation settings

**Tech Stack:**
- **ElevenLabs API** - Text-to-speech generation
- **FAL.ai FLUX** - Image generation
- **MongoDB** - Cache lookup storage
- **Express** - RESTful API endpoints (images only)

---

## Pipelines

### Pipeline 1: Generate Speech

Generates audio from text using ElevenLabs. Used internally by Coach for voice mode.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GENERATE SPEECH PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Coach System                     Media System
────────────                     ────────────
    │                                │
    │  1. Generate speech            │
    │     {text, voice, speed, ...}  │
    │───────────────────────────────>│
    │                                │
    │                                │  2. If caching enabled:
    │                                │     - Hash parameters → cacheKey
    │                                │     - Check TTSCache collection
    │                                │
    │                                │  3. If cache hit:
    │                                │     - Return cached reference
    │                                │
    │                                │  4. If cache miss:
    │                                │     - Call ElevenLabs API
    │                                │     - Get audio buffer
    │                                │
    │                                │  5. If caching enabled:
    │                                │     - Store reference in cache
    │                                │
    │  6. Return audio buffer        │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Coach system requests speech generation with text and options
2. If caching enabled, hash all parameters to create cache key
3. Check TTSCache for existing entry
4. If cache hit, return the cached audio reference/data
5. If cache miss, call ElevenLabs API to generate audio
6. If caching enabled, store reference in cache with TTL
7. Return audio buffer to caller

**Voice Options:**
- Custom: Leoni Vergara, Aria, Ana-Rita, Andromeda, LavenderLessons
- Standard: Sarah, Laura, Alice, Matilda, Jessica, Lily, Roger, Charlie, George, etc.

**Error Cases:**
- Missing API key → 500 API_KEY_MISSING
- ElevenLabs error → 500 GENERATION_FAILED

---

### Pipeline 2: Generate Image

Generates an image from a text prompt using FAL.ai FLUX model.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GENERATE IMAGE PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /api/image/generate   │
    │     {prompt, imageSize, ...}   │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. If caching enabled:
    │                                │     - Hash parameters → cacheKey
    │                                │     - Check ImageCache collection
    │                                │
    │                                │  3. If cache hit:
    │                                │     - Return cached imageUrl
    │                                │
    │                                │  4. If cache miss:
    │                                │     - Call FAL.ai API
    │                                │     - Get image URL
    │                                │
    │                                │  5. If caching enabled:
    │                                │     - Store URL in cache
    │                                │
    │  6. Return image result        │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests image generation with prompt and options
2. If caching enabled, hash all parameters to create cache key
3. Check ImageCache for existing entry
4. If cache hit, return the cached image URL
5. If cache miss, call FAL.ai FLUX dev model
6. If caching enabled, store URL in cache with TTL
7. Return image result with URL, dimensions, seed

**Error Cases:**
- Missing prompt → 400 VALIDATION_ERROR
- FAL.ai error → 500 GENERATION_FAILED

---

### Pipeline 3: Generate Image Fast

Generates an image quickly using FAL.ai FLUX Schnell model (fewer inference steps).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GENERATE IMAGE FAST PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /api/image/           │
    │     generate-fast              │
    │     {prompt, imageSize}        │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Cache check (if enabled)
    │                                │
    │                                │  3. Call FAL.ai FLUX Schnell
    │                                │     (1-12 inference steps)
    │                                │
    │                                │  4. Cache store (if enabled)
    │                                │
    │  5. Return image result        │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests fast image generation
2. Check cache if enabled
3. Call FAL.ai FLUX Schnell model (optimized for speed)
4. Store in cache if enabled
5. Return image result

**Difference from standard:**
- Uses FLUX Schnell model (faster)
- Limited to 1-12 inference steps
- Lower quality but much faster

---

### Pipeline 4: Generate Image-to-Image

Transforms an existing image based on a text prompt.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GENERATE IMAGE-TO-IMAGE PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. POST /api/image/           │
    │     generate/transform         │
    │     {prompt, imageUrl,         │
    │      strength}                 │
    │     Authorization: Bearer <token>
    │───────────────────────────────>│
    │                                │
    │                                │  2. Cache check (if enabled)
    │                                │
    │                                │  3. Call FAL.ai FLUX dev
    │                                │     image-to-image endpoint
    │                                │
    │                                │  4. Cache store (if enabled)
    │                                │
    │  5. Return transformed image   │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Frontend requests image transformation with source image URL
2. Check cache if enabled
3. Call FAL.ai FLUX dev image-to-image model
4. Store in cache if enabled
5. Return transformed image result

**Parameters:**
- `strength` (0-1): How much to transform (0 = no change, 1 = complete transformation)

---

### Pipeline 5: Get Image Sizes

Returns available image size presets.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GET IMAGE SIZES PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         Backend
────────                         ───────
    │                                │
    │  1. GET /api/image/sizes       │
    │───────────────────────────────>│
    │                                │
    │                                │  2. Return size presets
    │                                │
    │  3. Return sizes               │
    │<───────────────────────────────│
    │                                │
```

**Available Sizes:**

| Preset | Dimensions | Description |
|--------|------------|-------------|
| `square_hd` | 1024x1024 | Square HD |
| `square` | 512x512 | Square |
| `portrait_4_3` | 768x1024 | Portrait 4:3 |
| `portrait_16_9` | 576x1024 | Portrait 16:9 |
| `landscape_4_3` | 1024x768 | Landscape 4:3 |
| `landscape_16_9` | 1024x576 | Landscape 16:9 |

---

## Components

### TTSService

Text-to-speech generation using ElevenLabs API with optional caching.

```python
class TTSService:
    """
    Generates speech audio from text using ElevenLabs API.
    Used internally by Coach system for voice mode.
    """

    def __init__(self, db: Database = None, config: dict = None):
        """
        Args:
            db: MongoDB connection for caching (optional)
            config: Configuration dict with:
                - caching_enabled: bool (default: False)
                - cache_ttl_seconds: int (default: 86400 = 24 hours)
        """

    def generate_speech(
        self,
        text: str,
        voice: str = "Aria",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        speed: float = 1.0,
        style: float = 0,
        model_id: str = "eleven_multilingual_v2",
        use_cache: bool = True
    ) -> dict:
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

    def get_voice_id(self, voice: str) -> str:
        """
        Get voice ID from name or return as-is if already an ID.

        Args:
            voice: Voice name or ID

        Returns:
            Voice ID string
        """

    def get_available_voices(self) -> dict:
        """
        Get available voice name to ID mappings.

        Returns:
            Dict of voice names to IDs
        """

    def list_account_voices(self) -> list[dict]:
        """
        List voices from ElevenLabs account.

        Returns:
            List of voice objects from API
        """

    def _generate_cache_key(self, params: dict) -> str:
        """
        Generate cache key from parameters.

        Args:
            params: All generation parameters

        Returns:
            SHA-256 hash string
        """

    def _check_cache(self, cache_key: str) -> dict | None:
        """
        Check cache for existing entry.

        Args:
            cache_key: Hash key

        Returns:
            Cached data or None
        """

    def _store_in_cache(self, cache_key: str, data: dict) -> None:
        """
        Store result in cache with TTL.

        Args:
            cache_key: Hash key
            data: Data to cache (audio buffer reference)
        """
```

---

### ImageService

Image generation using FAL.ai FLUX models with optional caching.

```python
class ImageService:
    """
    Generates images using FAL.ai FLUX models.
    Supports standard, fast, and image-to-image generation.
    """

    def __init__(self, db: Database = None, config: dict = None):
        """
        Args:
            db: MongoDB connection for caching (optional)
            config: Configuration dict with:
                - caching_enabled: bool (default: False)
                - cache_ttl_seconds: int (default: 86400 = 24 hours)
                - store_binary: bool (default: False, store URL only)
        """

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        image_size: str = "landscape_4_3",
        num_inference_steps: int = 28,
        seed: int = None,
        guidance_scale: float = 3.5,
        enable_safety_checker: bool = True,
        use_cache: bool = True
    ) -> dict:
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

    def generate_image_fast(
        self,
        prompt: str,
        image_size: str = "landscape_4_3",
        num_inference_steps: int = 4,
        use_cache: bool = True
    ) -> dict:
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

    def generate_image_to_image(
        self,
        prompt: str,
        image_url: str,
        strength: float = 0.75,
        image_size: str = "landscape_4_3",
        use_cache: bool = True
    ) -> dict:
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

    def get_image_sizes(self) -> dict:
        """
        Get available image size presets.

        Returns:
            Dict of preset names to dimensions
        """

    def _generate_cache_key(self, params: dict) -> str:
        """
        Generate cache key from parameters.

        Args:
            params: All generation parameters

        Returns:
            SHA-256 hash string
        """

    def _check_cache(self, cache_key: str) -> dict | None:
        """
        Check cache for existing entry.

        Args:
            cache_key: Hash key

        Returns:
            Cached data or None
        """

    def _store_in_cache(self, cache_key: str, data: dict) -> None:
        """
        Store result in cache with TTL.

        Args:
            cache_key: Hash key
            data: Data to cache (URL or binary reference)
        """
```

---

## Data Models

### TTSCache Document

```python
{
    "_id": ObjectId,
    "cacheKey": str,              # SHA-256 hash of parameters (indexed, unique)
    "audioData": bytes | None,    # Audio buffer (if storing binary)
    "audioUrl": str | None,       # Audio URL (if storing reference)
    "contentType": str,           # "audio/mpeg"
    "voiceId": str,
    "voiceName": str,
    "textLength": int,            # Original text length
    "parameters": {               # Original parameters for debugging
        "voice": str,
        "speed": float,
        "stability": float,
        ...
    },
    "createdAt": datetime,
    "expiresAt": datetime         # TTL index for auto-deletion
}
```

**Indexes:**
- `cacheKey` - Unique index for lookups
- `expiresAt` - TTL index for automatic expiration

---

### ImageCache Document

```python
{
    "_id": ObjectId,
    "cacheKey": str,              # SHA-256 hash of parameters (indexed, unique)
    "imageUrl": str,              # Generated image URL
    "imageData": bytes | None,    # Binary data (if store_binary enabled)
    "width": int,
    "height": int,
    "seed": int,
    "model": str,                 # "flux-dev", "flux-schnell", "flux-dev-i2i"
    "parameters": {               # Original parameters for debugging
        "prompt": str,
        "imageSize": str,
        "guidanceScale": float,
        ...
    },
    "createdAt": datetime,
    "expiresAt": datetime         # TTL index for auto-deletion
}
```

**Indexes:**
- `cacheKey` - Unique index for lookups
- `expiresAt` - TTL index for automatic expiration

---

## Integration Points

### With Coach System

TTS used for voice mode:

```python
# Coach generates AI response, then converts to speech
response_text = ai_service.generate_response(message)

# Convert to audio for voice mode
audio_result = tts_service.generate_speech(
    text=response_text,
    voice=user_preferred_voice,
    speed=1.0
)

# Stream audio to client
return audio_result["audioBuffer"]
```

### With Content System

TTS used for content audio generation:

```python
# Generate audio for content item
audio_result = tts_service.generate_speech(
    text=content_item["voiceoverScriptEn"],
    voice=content_item["ttsVoice"],
    speed=content_item["ttsSpeed"]
)

# Store on content item
content_item["audioDataEn"] = audio_result["audioBuffer"]
```

### With Auth System

Image endpoints require authentication:

```python
@require_auth
def generate_image_handler(request):
    ...
```

---

## Configuration

### Environment Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | TTSService | ElevenLabs API key |
| `FAL_KEY` | ImageService | FAL.ai API key |

### Service Configuration

```python
# TTSService config
{
    "caching_enabled": True,       # Enable/disable caching
    "cache_ttl_seconds": 86400,    # 24 hours default
}

# ImageService config
{
    "caching_enabled": True,       # Enable/disable caching
    "cache_ttl_seconds": 86400,    # 24 hours default
    "store_binary": False,         # Store URL only (True = download and store binary)
}
```

### Voice Mappings

| Voice Name | Voice ID | Type |
|------------|----------|------|
| Aria | fO844Om1VZLpw8IpZj3T | Custom |
| Leoni Vergara | pBZVCk298iJlHAcHQwLr | Custom |
| Ana-Rita | wJqPPQ618aTW29mptyoc | Custom |
| Andromeda | HoU1B9WLbSprzhhX34v0 | Custom |
| Sarah | EXAVITQu4vr4xnSDxMaL | Standard |
| Laura | FGY2WhTYpPnrIDTdsKH5 | Standard |
| Alice | Xb7hH8MSUJpSbSDYk0k2 | Standard |
| Roger | CwhRBWXzGAHq8TQ4Fs17 | Standard |
| ... | ... | ... |
