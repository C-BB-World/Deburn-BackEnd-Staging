# Agent System Architecture

## Overview

The Agent system provides the AI backbone for Eve (the coaching AI). It consists of two core components:

1. **Memory System** - Encrypted conversation storage with RAG-ready architecture
2. **Agent** - Claude-based AI interface with dynamic prompt loading

All code will reside in `app_v2/agent/` following SOLID principles.

---

## Component 1: Memory System

### Purpose

Store and retrieve conversation history with AES-256-CBC encryption. Designed to be extended to a RAG (Retrieval-Augmented Generation) system later.

> **Note on Encryption:** While SHA256 is a hash function (one-way), conversations require reversible encryption for retrieval. We use AES-256-CBC (the existing pattern in TokenEncryptionService) with SHA256-derived keys for actual content encryption.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEMORY SYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │  MemoryProvider  │◄────────│      EncryptedMemory         │  │
│  │   (Abstract)     │         │   (MongoDB Implementation)   │  │
│  └──────────────────┘         └──────────────────────────────┘  │
│           ▲                              │                       │
│           │                              ▼                       │
│           │                   ┌──────────────────────────────┐  │
│  (Future: RAGMemory)          │   MemoryEncryptionService    │  │
│                               │   (AES-256-CBC + SHA256)     │  │
│                               └──────────────────────────────┘  │
│                                          │                       │
│                                          ▼                       │
│                               ┌──────────────────────────────┐  │
│                               │   MongoDB: conversations     │  │
│                               │   (deburn-hub database)      │  │
│                               └──────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
app_v2/agent/
├── __init__.py
├── memory/
│   ├── __init__.py
│   ├── provider.py          # Abstract MemoryProvider
│   ├── encrypted_memory.py  # MongoDB implementation with encryption
│   └── encryption.py        # MemoryEncryptionService
└── ...
```

### Classes

#### MemoryProvider (Abstract)

```python
class MemoryProvider(ABC):
    """
    Abstract interface for conversation memory.
    Allows swapping implementations (encrypted, RAG, etc.)
    """

    @abstractmethod
    async def store_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,  # "user" | "assistant"
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a single message."""
        pass

    @abstractmethod
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Conversation]:
        """Retrieve full conversation."""
        pass

    @abstractmethod
    async def get_recent_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for context window."""
        pass

    @abstractmethod
    async def create_conversation(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new conversation, return ID."""
        pass

    @abstractmethod
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[ConversationSummary]:
        """
        Search past conversations (for future RAG).
        Default implementation can return empty list.
        """
        pass
```

#### MemoryEncryptionService

```python
class MemoryEncryptionService:
    """
    Encrypts/decrypts conversation content using AES-256-CBC.
    Key derived from SHA256 hash of encryption key.
    """

    def __init__(self, encryption_key: str):
        """
        Args:
            encryption_key: Key from environment (MEMORY_ENCRYPTION_KEY)
        """

    def encrypt(self, plaintext: str) -> str:
        """Encrypt message content. Returns base64(IV + ciphertext)."""

    def decrypt(self, encrypted: str) -> Optional[str]:
        """Decrypt message content. Returns None on failure."""

    def hash_for_search(self, text: str) -> str:
        """
        Generate searchable hash tokens (for future RAG indexing).
        Uses SHA256 for consistent hashing.
        """
```

#### EncryptedMemory

```python
class EncryptedMemory(MemoryProvider):
    """
    MongoDB-backed memory with AES-256-CBC encryption.
    Stores in 'conversations' collection under deburn-hub.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        encryption_service: MemoryEncryptionService
    ):
        """
        Args:
            db: MongoDB database connection (deburn-hub)
            encryption_service: For content encryption
        """
        self._db = db
        self._collection = db["conversations"]
        self._encryption = encryption_service
```

### Data Model (MongoDB)

```python
# Collection: conversations (deburn-hub database)
{
    "_id": ObjectId,
    "conversationId": str,              # Unique ID (conv_timestamp_random)
    "userId": ObjectId,                 # Reference to User
    "messages": [{
        "role": str,                    # "user" | "assistant"
        "content": str,                 # ENCRYPTED (AES-256-CBC, base64)
        "contentHash": str,             # SHA256 hash (for future RAG dedup)
        "timestamp": datetime,
        "metadata": dict                # Unencrypted (topics, etc.)
    }],
    "topics": [str],                    # Accumulated topics (unencrypted)
    "status": str,                      # "active" | "archived"
    "messageCount": int,                # For quick stats
    "lastMessageAt": datetime,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

### RAG Extension Points

The design allows future RAG implementation:

1. **`search_conversations()`** - Currently returns empty, can be implemented with vector search
2. **`contentHash`** - SHA256 hash allows deduplication and indexing
3. **Separate `RAGMemory`** class can extend `MemoryProvider` with:
   - Embedding generation (via OpenAI/other)
   - Vector storage (MongoDB Atlas Vector Search or Pinecone)
   - Semantic search retrieval

---

## Component 2: Agent System

### Purpose

Provide AI coaching responses using Claude, with dynamic prompts loaded from MongoDB.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT SYSTEM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │      Agent       │◄────────│        ClaudeAgent           │  │
│  │   (Abstract)     │         │   (Claude Implementation)    │  │
│  └──────────────────┘         └──────────────────────────────┘  │
│           ▲                              │                       │
│           │                              ▼                       │
│           │                   ┌──────────────────────────────┐  │
│  ┌────────────────┐           │      PromptService           │  │
│  │  OpenAIAgent   │           │   (MongoDB: aiprompt)        │  │
│  │  (Future)      │           └──────────────────────────────┘  │
│  └────────────────┘                      │                       │
│           │                              ▼                       │
│           ▼                   ┌──────────────────────────────┐  │
│  ┌────────────────┐           │   ClaudeProvider             │  │
│  │ OpenAIProvider │           │   (common/ai/claude.py)      │  │
│  │ (common/ai/)   │           └──────────────────────────────┘  │
│  └────────────────┘                      │                       │
│                                          ▼                       │
│                               ┌──────────────────────────────┐  │
│                               │   Anthropic SDK              │  │
│                               └──────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Reusing Common AI Providers

The `common/ai/` module provides low-level AI provider abstractions:

| Provider | File | Features |
|----------|------|----------|
| `AIProvider` | `common/ai/base.py` | Abstract interface |
| `ClaudeProvider` | `common/ai/claude.py` | Claude API (chat, stream, tools) |
| `OpenAIProvider` | `common/ai/openai.py` | OpenAI API (chat, stream, embeddings) |

**ClaudeAgent uses ClaudeProvider** - it doesn't call the Anthropic SDK directly. This keeps the agent layer focused on coaching logic while delegating raw API calls to the common layer.

### File Structure

```
app_v2/agent/
├── __init__.py
├── memory/
│   └── ... (see above)
├── agent.py              # Abstract Agent interface
├── claude_agent.py       # Claude implementation (uses common/ai/claude.py)
├── openai_agent.py       # OpenAI implementation (uses common/ai/openai.py)
├── prompt_service.py     # Dynamic prompt loading from MongoDB
├── types.py              # Dataclasses (CoachingContext, etc.)
└── topics.py             # Topic extraction logic
```

### Classes

#### Agent (Abstract)

```python
class Agent(ABC):
    """
    Abstract AI agent interface.
    All AI operations go through this abstraction.
    """

    @abstractmethod
    async def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> AsyncIterator[str] | str:
        """Generate coaching response (streaming or complete)."""
        pass

    @abstractmethod
    async def generate_checkin_insight(
        self,
        context: CheckinInsightContext
    ) -> CheckinInsight:
        """Generate insight after check-in."""
        pass

    @abstractmethod
    async def enhance_recommendation(
        self,
        base_description: str,
        patterns: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """Enhance recommendation with personalized advice."""
        pass

    @abstractmethod
    def extract_topics(self, message: str) -> List[str]:
        """Extract coaching topics from message."""
        pass
```

#### PromptService

```python
class PromptService:
    """
    Loads and caches prompts from MongoDB 'aiprompt' collection.
    Supports English and Swedish.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Args:
            db: MongoDB database connection (deburn-hub)
        """
        self._db = db
        self._collection = db["aiprompt"]
        self._cache: Dict[str, CachedPrompt] = {}  # In-memory cache
        self._cache_ttl = 300  # 5 minutes

    async def get_system_prompt(
        self,
        prompt_type: str,  # "coaching" | "checkin_insight" | "recommendation"
        language: str = "en"
    ) -> str:
        """
        Get prompt from MongoDB or cache.

        Args:
            prompt_type: Type of prompt to retrieve
            language: 'en' or 'sv'

        Returns:
            System prompt string
        """

    async def refresh_cache(self) -> None:
        """Force refresh all cached prompts."""

    async def get_all_prompts(self) -> Dict[str, Dict[str, str]]:
        """Get all prompts (for admin UI)."""
```

#### ClaudeAgent

```python
from common.ai.claude import ClaudeProvider

class ClaudeAgent(Agent):
    """
    Claude-based AI agent with dynamic prompt loading.
    Uses ClaudeProvider from common/ai/ for API calls.
    """

    def __init__(
        self,
        provider: ClaudeProvider,
        prompt_service: PromptService,
        max_tokens: int = 1024
    ):
        """
        Args:
            provider: ClaudeProvider instance (from common/ai/)
            prompt_service: For dynamic prompt loading
            max_tokens: Maximum response tokens
        """
        self._provider = provider
        self._prompt_service = prompt_service
        self._max_tokens = max_tokens

    async def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> AsyncIterator[str] | str:
        """
        Generate coaching response.

        1. Load system prompt from PromptService
        2. Inject user context (profile, wellbeing, commitments)
        3. Build message history
        4. Delegate to ClaudeProvider (stream_chat or chat)
        """
        system_prompt = await self._build_system_prompt(context)
        history = self._build_history(context)

        if stream:
            return self._provider.stream_chat(
                message=message,
                system_prompt=system_prompt,
                conversation_history=history,
                max_tokens=self._max_tokens
            )
        else:
            return await self._provider.chat(
                message=message,
                system_prompt=system_prompt,
                conversation_history=history,
                max_tokens=self._max_tokens
            )

    async def _build_system_prompt(self, context: CoachingContext) -> str:
        """
        Build complete system prompt:
        1. Base prompt from MongoDB (via PromptService)
        2. + User context section
        3. + Wellbeing data
        4. + Due commitments (if any)
        5. + Safety level note (if level 1)
        """

    def _build_history(self, context: CoachingContext) -> List[Dict[str, str]]:
        """Convert conversation history to provider format."""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in context.conversation_history[-10:]
        ]
```

#### Switching to Another Provider

To use OpenAI instead of Claude:

```python
from common.ai.openai import OpenAIProvider

class OpenAIAgent(Agent):
    """OpenAI-based agent - same pattern as ClaudeAgent."""

    def __init__(
        self,
        provider: OpenAIProvider,
        prompt_service: PromptService,
        max_tokens: int = 1024
    ):
        self._provider = provider
        self._prompt_service = prompt_service
        self._max_tokens = max_tokens

    # ... same methods, delegates to OpenAIProvider
```

### Data Model (MongoDB)

```python
# Collection: aiprompt (deburn-hub database)
{
    "_id": ObjectId,
    "promptType": str,          # "coaching" | "checkin_insight" | "recommendation"
    "language": str,            # "en" | "sv"
    "content": str,             # The actual prompt text
    "version": int,             # For versioning/rollback
    "isActive": bool,           # Only active prompts are used
    "metadata": {
        "author": str,          # Who last edited
        "description": str,     # What this prompt does
    },
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Index:**
- `{ promptType: 1, language: 1, isActive: 1 }` - Unique for active prompts

### Initial Prompts (English)

```markdown
# promptType: "coaching", language: "en"

You are Eve, an AI leadership coach focused on helping leaders grow, prevent burnout, and build psychologically safe teams.

Your coaching style:
- Warm, empathetic, and supportive
- Ask thoughtful questions to help users reflect
- Offer practical, actionable micro-commitments
- Reference patterns you notice in their wellbeing data
- Keep responses concise but meaningful

When the user seems stressed or overwhelmed, acknowledge their feelings first.

When suggesting a micro-commitment, format it as:
**Micro-Commitment:** "The specific action"
**Reflection Question:** "A question to ponder"
**Why This Matters:** "Brief psychological insight"

Keep your responses focused and around 150-250 words.
```

### Initial Prompts (Swedish)

```markdown
# promptType: "coaching", language: "sv"

Du är Eve, en AI-ledarskapscoach som fokuserar på att hjälpa ledare att växa, förebygga utbrändhet och bygga psykologiskt trygga team.

Din coachstil:
- Varm, empatisk och stödjande
- Ställ eftertänksamma frågor för reflektion
- Erbjud praktiska, handlingsbara mikro-åtaganden
- Referera till mönster du ser i deras välmåendedata
- Håll svaren koncisa men meningsfulla

När användaren verkar stressad eller överväldigad, bekräfta deras känslor först.

När du föreslår ett mikro-åtagande, formatera det som:
**Mikro-Åtagande:** "Den specifika handlingen"
**Reflektionsfråga:** "En fråga att fundera på"
**Varför det Spelar Roll:** "Kort psykologisk insikt"

Håll dina svar fokuserade och omkring 150-250 ord.
```

---

## SOLID Principles Applied

| Principle | Application |
|-----------|-------------|
| **S** - Single Responsibility | `MemoryProvider` handles storage only; `Agent` handles AI only; `PromptService` handles prompts only |
| **O** - Open/Closed | Add `RAGMemory` without modifying `EncryptedMemory`; add new LLM agents without modifying `ClaudeAgent` |
| **L** - Liskov Substitution | Any `MemoryProvider` implementation works anywhere memory is used |
| **I** - Interface Segregation | Small focused interfaces: `MemoryProvider`, `Agent`, `PromptService` |
| **D** - Dependency Inversion | `ClaudeAgent` depends on `PromptService` abstraction, not concrete MongoDB calls |

---

## Configuration

```python
# Environment variables

# Agent selection
AGENT_TYPE = "claude"                  # "claude" or "openai"

# Provider API keys
ANTHROPIC_API_KEY = "..."              # Claude API key
OPENAI_API_KEY = "..."                 # OpenAI API key (if using openai)

# Agent settings
AGENT_MODEL = "claude-sonnet-4-5-20250514"  # Model name (provider-specific)
AGENT_MAX_TOKENS = 1024

# Memory encryption
MEMORY_ENCRYPTION_KEY = "..."          # 32-byte hex or any string (SHA256 hashed)

# Prompt caching
PROMPT_CACHE_TTL = 300                 # 5 minutes
```

---

## Integration with Existing Services

The agent folder components integrate with `CoachService` in `app_v2/services/coach/`:

```python
# In dependencies.py (updated)

from common.ai.claude import ClaudeProvider
from common.ai.openai import OpenAIProvider
from app_v2.agent import ClaudeAgent, OpenAIAgent, PromptService, EncryptedMemory, MemoryEncryptionService

def init_agent_services(db: AsyncIOMotorDatabase) -> None:
    """Initialize agent components."""

    # Memory
    encryption_key = os.getenv("MEMORY_ENCRYPTION_KEY", "default-dev-key")
    encryption_service = MemoryEncryptionService(encryption_key)
    memory = EncryptedMemory(db=db, encryption_service=encryption_service)

    # Prompt Service (shared)
    prompt_service = PromptService(db=db)

    # Agent (provider-based)
    agent_type = os.getenv("AGENT_TYPE", "claude")
    max_tokens = int(os.getenv("AGENT_MAX_TOKENS", "1024"))

    if agent_type == "claude":
        provider = ClaudeProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("AGENT_MODEL", "claude-sonnet-4-5-20250514")
        )
        agent = ClaudeAgent(
            provider=provider,
            prompt_service=prompt_service,
            max_tokens=max_tokens
        )
    elif agent_type == "openai":
        provider = OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("AGENT_MODEL", "gpt-4o")
        )
        agent = OpenAIAgent(
            provider=provider,
            prompt_service=prompt_service,
            max_tokens=max_tokens
        )
    else:
        raise ValueError(f"Unknown AGENT_TYPE: {agent_type}")

    # Memory replaces ConversationService for storage
    # Agent is injected into CoachService
```

---

## Implementation Order

1. **Memory System**
   - `memory/encryption.py` - MemoryEncryptionService
   - `memory/provider.py` - Abstract MemoryProvider
   - `memory/encrypted_memory.py` - MongoDB implementation

2. **Agent System**
   - `types.py` - Dataclasses (move from services/coach/agent.py)
   - `topics.py` - Topic extraction (move from services/coach/claude_agent.py)
   - `prompt_service.py` - Dynamic prompt loading
   - `agent.py` - Abstract Agent
   - `claude_agent.py` - Claude implementation (uses `ClaudeProvider` from common/ai/)
   - `openai_agent.py` - (Optional) OpenAI implementation

3. **Integration**
   - Update `dependencies.py` to use new components
   - Update `CoachService` to use `MemoryProvider` instead of `ConversationService`
   - Add `AGENT_TYPE` environment variable support

---

## Quick Reference

| Component | File | Purpose |
|-----------|------|---------|
| `MemoryProvider` | `memory/provider.py` | Abstract memory interface |
| `MemoryEncryptionService` | `memory/encryption.py` | AES-256-CBC encryption |
| `EncryptedMemory` | `memory/encrypted_memory.py` | MongoDB + encryption |
| `Agent` | `agent.py` | Abstract AI interface |
| `ClaudeAgent` | `claude_agent.py` | Claude implementation (uses `ClaudeProvider`) |
| `OpenAIAgent` | `openai_agent.py` | OpenAI implementation (uses `OpenAIProvider`) |
| `PromptService` | `prompt_service.py` | Dynamic prompts from MongoDB |
| `CoachingContext` | `types.py` | Context dataclass |
| `TOPIC_KEYWORDS` | `topics.py` | Topic extraction logic |
| `ClaudeProvider` | `common/ai/claude.py` | Low-level Claude API (reused) |
| `OpenAIProvider` | `common/ai/openai.py` | Low-level OpenAI API (reused) |

---

## Future Works

### 1. Secure Key Generation Script

Add a CLI command or script to generate cryptographically secure encryption keys:

```bash
# Generate 32-byte hex key for MEMORY_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

Consider adding a management command:
```bash
python manage.py generate-encryption-key
```

### 2. Key Rotation

Implement key rotation for MEMORY_ENCRYPTION_KEY:
- Re-encrypt existing conversations with new key
- Support dual-key decryption during transition period

### 3. RAG Memory Implementation

Extend `MemoryProvider` with `RAGMemory`:
- Vector embeddings for semantic search
- MongoDB Atlas Vector Search or Pinecone integration
- `search_conversations()` implementation

### 4. OpenAI Agent

Add `openai_agent.py` for OpenAI as alternative provider.
