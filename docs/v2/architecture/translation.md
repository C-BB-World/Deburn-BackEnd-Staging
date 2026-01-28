# Translation System Architecture

## Overview

The translation system provides on-demand translation of coach conversation history when users switch languages. It uses Claude API for translation and caches results for efficiency.

## Components

### Service Layer

**TranslationService** (`app_v2/services/translation/translation_service.py`)
- Uses Claude API for batch translation
- Handles JSON response parsing with fallbacks
- Maintains conversation tone and formatting

```python
class TranslationService:
    async def translate_messages(
        messages: List[Dict],      # [{index, content}, ...]
        target_language: str,      # 'en' or 'sv'
        source_language: str = None
    ) -> List[Dict]               # [{index, content}, ...]

    async def translate_single(
        text: str,
        target_language: str
    ) -> str
```

### Pipeline Layer

**Translation Pipeline** (`app_v2/pipelines/translation.py`)
- Orchestrates translation with caching
- Handles encryption/decryption
- Manages windowed translation for large histories

```python
async def translate_conversation_messages(
    db: AsyncIOMotorDatabase,
    translation_service: TranslationService,
    encryption_service: MemoryEncryptionService,
    conversation_id: str,
    user_id: str,
    target_language: str,
    start_index: Optional[int] = None,
    count: int = 20
) -> Dict[str, Any]
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │ Language    │───▶│ Translation  │───▶│ Update Messages     │ │
│  │ Switch      │    │ Request      │    │ with Translations   │ │
│  └─────────────┘    └──────────────┘    └─────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     POST /api/coach/conversations/translate     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Translation Pipeline                          │
│  ┌──────────────┐   ┌───────────────┐   ┌────────────────────┐  │
│  │ Fetch        │──▶│ Check Cache   │──▶│ Decrypt Messages   │  │
│  │ Conversation │   │ & Language    │   │ that need transl.  │  │
│  └──────────────┘   └───────────────┘   └────────────────────┘  │
│                                                   │              │
│                                                   ▼              │
│  ┌──────────────┐   ┌───────────────┐   ┌────────────────────┐  │
│  │ Cache        │◀──│ Encrypt       │◀──│ TranslationService │  │
│  │ in MongoDB   │   │ Translations  │   │ (Claude API)       │  │
│  └──────────────┘   └───────────────┘   └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Message Schema

Messages in the `conversations` collection include translation support:

```json
{
  "role": "user",
  "content": "base64_encrypted_content",
  "encrypted": true,
  "language": "en",
  "timestamp": "2026-01-28T10:00:00Z",
  "metadata": {},
  "translations": {
    "sv": "base64_encrypted_swedish"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `language` | string | Original language of message ('en' or 'sv') |
| `translations` | object | Cached translations keyed by language code |

## Caching Strategy

### When Translating

1. **Already in target language**: Return original content, skip translation
2. **Cached translation exists**: Return cached (decrypt from `translations.{lang}`)
3. **Needs translation**: Translate via Claude, encrypt, store in `translations.{lang}`

### Cache Storage

Translations are stored encrypted in the message document:

```javascript
// MongoDB update for caching translation
await collection.update_one(
  {"conversationId": conversation_id},
  {"$set": {`messages.${idx}.translations.${target_language}`: encrypted_translation}}
)
```

## Windowed Translation

For large conversation histories, translation is windowed:

- **Default**: Last 20 messages
- **Maximum per request**: 50 messages
- **Configurable**: `startIndex` and `count` parameters

Frontend can request additional windows if needed:
```javascript
// First request - latest 20
translateConversation(convId, 'sv', { count: 20 })

// Load more - next 20
translateConversation(convId, 'sv', { startIndex: 20, count: 20 })
```

## Claude Prompt

The translation service uses this prompt structure:

```
Translate the following messages from {source} to {target}.
These are messages from a coaching conversation. Maintain the tone, warmth, and context.

Important:
- Keep the same meaning and emotional tone
- Preserve any formatting (bullet points, numbered lists)
- Return ONLY valid JSON array, no other text

Messages to translate:
1. "First message content"
2. "Second message content"

Return as JSON array with objects containing "index" (0-based) and "content" (translated text):
[{"index": 0, "content": "translated text"}, ...]
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| Claude API failure | Return original messages unchanged |
| JSON parse failure | Return original messages unchanged |
| Decryption failure | Return "[Decryption failed]" |
| Conversation not found | Return empty with error message |

## Dependencies

```python
# app_v2/dependencies.py

def init_translation_services(claude_provider: ClaudeProvider) -> None:
    global _translation_service
    _translation_service = TranslationService(claude_provider=claude_provider)

def get_translation_service() -> TranslationService:
    if _translation_service is None:
        raise RuntimeError("Translation services not initialized.")
    return _translation_service
```

## Files

| File | Purpose |
|------|---------|
| `app_v2/services/translation/__init__.py` | Module exports |
| `app_v2/services/translation/translation_service.py` | Claude translation service |
| `app_v2/pipelines/translation.py` | Translation orchestration with caching |
| `app_v2/routers/coach.py` | `/conversations/translate` endpoint |
| `app_v2/schemas/coach.py` | Request/response schemas |
| `app_v2/dependencies.py` | Service initialization |
