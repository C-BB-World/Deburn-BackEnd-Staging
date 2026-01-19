# Agent System Architecture

## Overview

The Agent system provides the AI backbone for Eve (the coaching AI). It consists of two core components:

1. **Memory System** - Encrypted conversation storage with RAG-ready architecture
2. **Agent** - Claude-based AI interface with dynamic prompt loading
3. **Actions System** - Modular, pluggable action recommendations (learnings, exercises, etc.)
4. **Voice** - Text-to-speech integration via ElevenLabs

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
│   ├── encryption.py        # MemoryEncryptionService
│   └── knowledge.py         # Static knowledge (topics, fallback actions)
├── actions/
│   ├── __init__.py          # Exports registry, generator, Action
│   ├── base.py              # Action schema, ActionHandler base
│   ├── registry.py          # ActionRegistry
│   ├── generator.py         # ActionGenerator (orchestrator)
│   ├── topic_detector.py    # TopicDetector (keyword matching)
│   ├── retrieval/           # Retrieval subsystem
│   │   ├── __init__.py     # Exports retrievers
│   │   ├── base.py         # ActionRetriever abstract interface
│   │   ├── static.py       # StaticRetriever (uses memory/knowledge)
│   │   └── rag.py          # RAGRetriever (future - vector search)
│   └── types/               # Action type handlers
│       ├── __init__.py     # Exports all handlers
│       ├── learning.py     # LearningHandler
│       └── exercise.py     # ExerciseHandler
├── voice/
│   └── __init__.py          # Re-exports TTSService
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

## Component 3: Actions System

### Purpose

Provide modular, pluggable action recommendations during coaching conversations. Actions include learning modules, exercises, journaling prompts, and future action types. Designed with RAG extensibility in mind.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       ACTIONS SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │  ActionGenerator │◄────────│       ActionRegistry          │  │
│  │  (Orchestrator)  │         │   (Pluggable Handlers)       │  │
│  └──────────────────┘         └──────────────────────────────┘  │
│           │                              │                       │
│           │                   ┌──────────┼──────────┐           │
│           │                   ▼          ▼          ▼           │
│           │           ┌──────────┐┌──────────┐┌──────────┐      │
│           │           │ Learning ││ Exercise ││  Future  │      │
│           │           │ Handler  ││ Handler  ││ Handlers │      │
│           │           └──────────┘└──────────┘└──────────┘      │
│           │                   │                                  │
│           ▼                   ▼                                  │
│  ┌──────────────────┐  ┌──────────────────────────────┐         │
│  │  TopicDetector   │  │      ActionRetriever          │         │
│  │  (Keyword Match) │  │   (Abstract Interface)        │         │
│  └──────────────────┘  └──────────────────────────────┘         │
│           │                   │                                  │
│           ▼                   ├────────────────┐                 │
│  ┌──────────────────┐         ▼                ▼                 │
│  │ memory/knowledge │  ┌──────────────┐ ┌──────────────┐        │
│  │ (Topic Keywords) │  │StaticRetriever│ │ RAGRetriever │        │
│  └──────────────────┘  │  (Current)    │ │  (Future)    │        │
│                        └──────────────┘ └──────────────┘        │
│                               │                                  │
│                               ▼                                  │
│                        ┌──────────────────────────────┐         │
│                        │  memory/knowledge            │         │
│                        │  (Fallback Actions)          │         │
│                        └──────────────────────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
app_v2/agent/actions/
├── __init__.py               # Exports registry, generator, Action
├── base.py                   # Action schema, ActionHandler base
├── registry.py               # ActionRegistry
├── generator.py              # ActionGenerator (orchestrator)
├── topic_detector.py         # TopicDetector (keyword matching)
│
├── retrieval/                # Retrieval subsystem
│   ├── __init__.py          # Exports retrievers
│   ├── base.py              # ActionRetriever abstract interface
│   ├── static.py            # StaticRetriever (uses memory/knowledge)
│   └── rag.py               # RAGRetriever (future - vector search)
│
└── types/                    # Action type handlers
    ├── __init__.py          # Exports all handlers
    ├── learning.py          # LearningHandler
    └── exercise.py          # ExerciseHandler
```

**Separation of Concerns:**
- **`retrieval/`** - How to find relevant content (static, RAG, hybrid)
- **`types/`** - What kind of actions to generate (learning, exercise, journal)

### Classes

#### Action (Schema)

```python
from pydantic import BaseModel
from typing import Optional

class Action(BaseModel):
    """Universal action schema - flexible for all action types."""
    type: str                      # 'learning', 'exercise', 'journal', etc.
    id: str                        # Unique identifier
    label: str                     # User-facing label
    metadata: Optional[dict] = {}  # Flexible per-type data
                                   # e.g., duration, contentType, category
```

#### ActionHandler (Abstract Base)

```python
from abc import ABC, abstractmethod
from typing import List

class ActionHandler(ABC):
    """Base class for pluggable action type handlers."""

    @property
    @abstractmethod
    def action_type(self) -> str:
        """Unique identifier for this action type."""
        pass

    @abstractmethod
    async def generate(
        self,
        topics: List[str],
        language: str,
        context: dict
    ) -> List[Action]:
        """Generate actions of this type based on topics."""
        pass
```

#### ActionRegistry

```python
class ActionRegistry:
    """Registry for pluggable action handlers."""

    def __init__(self):
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, handler: ActionHandler) -> None:
        """Register an action handler."""
        self._handlers[handler.action_type] = handler

    def unregister(self, action_type: str) -> None:
        """Remove an action handler."""
        self._handlers.pop(action_type, None)

    def get(self, action_type: str) -> Optional[ActionHandler]:
        """Get handler by type."""
        return self._handlers.get(action_type)

    def all_handlers(self) -> List[ActionHandler]:
        """Get all registered handlers."""
        return list(self._handlers.values())
```

#### ActionGenerator

```python
class ActionGenerator:
    """Orchestrates action generation across all registered types."""

    def __init__(self, registry: ActionRegistry, topic_detector: TopicDetector):
        self._registry = registry
        self._topic_detector = topic_detector

    async def generate(
        self,
        message: str,
        language: str,
        context: dict = {},
        action_types: List[str] = None  # Filter to specific types
    ) -> List[Action]:
        """
        Generate actions for a user message.

        1. Detect topics from message
        2. Get all (or filtered) handlers
        3. Collect actions from each handler
        """
        topics = self._topic_detector.detect(message)

        handlers = self._registry.all_handlers()
        if action_types:
            handlers = [h for h in handlers if h.action_type in action_types]

        actions = []
        for handler in handlers:
            handler_actions = await handler.generate(topics, language, context)
            actions.extend(handler_actions)

        return actions
```

#### Retrieval Subsystem (`actions/retrieval/`)

The retrieval folder contains all content retrieval logic, designed for easy RAG integration.

**`retrieval/base.py` - Abstract Interface:**

```python
from abc import ABC, abstractmethod
from typing import List
from ..base import Action

class ActionRetriever(ABC):
    """Abstract interface for action retrieval - designed for RAG."""

    @abstractmethod
    async def retrieve(
        self,
        topics: List[str],
        language: str,
        limit: int = 2
    ) -> List[Action]:
        """Retrieve relevant actions for given topics."""
        pass
```

**`retrieval/static.py` - Static Retriever:**

```python
from .base import ActionRetriever
from app_v2.agent.memory.knowledge import Knowledge

class StaticRetriever(ActionRetriever):
    """Uses hardcoded knowledge from memory/knowledge.py."""

    def __init__(self, knowledge: Knowledge):
        self._knowledge = knowledge

    async def retrieve(self, topics, language, limit=2):
        actions = []
        for topic in topics:
            fallbacks = self._knowledge.get_fallback_actions(topic, language)
            actions.extend(fallbacks)
        return actions[:limit]
```

**`retrieval/rag.py` - RAG Retriever (Future):**

```python
from .base import ActionRetriever

class RAGRetriever(ActionRetriever):
    """Uses vector search against content library."""

    def __init__(self, vector_store, embedding_service, db=None):
        self._vector_store = vector_store
        self._embeddings = embedding_service
        self._db = db

    async def retrieve(self, topics, language, limit=2):
        # 1. Generate embedding for topics
        query = " ".join(topics)
        embedding = await self._embeddings.embed(query)

        # 2. Vector search in content library
        results = await self._vector_store.search(
            embedding,
            filter={"language": language, "coachEnabled": True},
            limit=limit
        )

        # 3. Convert to Action objects
        return [self._to_action(r) for r in results]
```

**Future retrievers can be added:**
- `retrieval/content_library.py` - Direct MongoDB query (no vectors)
- `retrieval/hybrid.py` - Combine static + RAG results

#### TopicDetector

```python
class TopicDetector:
    """Extracts topics from user messages using keyword matching."""

    def __init__(self, knowledge: Knowledge):
        self._knowledge = knowledge

    def detect(self, message: str) -> List[str]:
        """
        Detect topics from message text.

        Args:
            message: User message

        Returns:
            List of detected topic strings
        """
        message_lower = message.lower()
        topics = []

        for topic, keywords in self._knowledge.topic_keywords.items():
            if any(kw in message_lower for kw in keywords):
                topics.append(topic)

        return topics
```

#### Knowledge (in memory/)

```python
class Knowledge:
    """
    Static knowledge store for the agent.
    Contains topic keywords and fallback actions.
    Designed to be augmented/replaced by RAG in future.
    """

    # 12 coaching topics with detection keywords
    topic_keywords: Dict[str, List[str]] = {
        "delegation": ["delegate", "delegating", "hand off", "assign", "trust team"],
        "stress": ["stress", "stressed", "overwhelmed", "pressure", "anxious", "anxiety"],
        "team_dynamics": ["team", "collaboration", "conflict", "dynamics", "working together"],
        "communication": ["communicate", "communication", "feedback", "difficult conversation"],
        "leadership": ["leadership", "leader", "leading", "manage", "management"],
        "time_management": ["time", "prioritize", "busy", "schedule", "deadline"],
        "conflict": ["conflict", "disagreement", "tension", "difficult person"],
        "burnout": ["burnout", "burned out", "exhausted", "tired", "drained", "recovery"],
        "motivation": ["motivation", "motivated", "engagement", "inspire"],
        "decision_making": ["decision", "decide", "choice", "uncertain"],
        "mindfulness": ["mindful", "present", "awareness", "breathing"],
        "resilience": ["resilience", "bounce back", "setback", "failure"],
    }

    # Fallback actions per topic/language
    fallback_actions: Dict[str, Dict[str, List[Action]]] = {
        "stress": {
            "en": [
                Action(type="exercise", id="breathing-1", label="Try a Calming Exercise",
                       metadata={"duration": "3 min", "contentType": "audio_exercise"}),
                Action(type="learning", id="stress-mgmt-1", label="Learn: Stress Management",
                       metadata={"duration": "5 min", "contentType": "audio_article"}),
            ],
            "sv": [
                Action(type="exercise", id="breathing-1", label="Prova en andningsövning",
                       metadata={"duration": "3 min", "contentType": "audio_exercise"}),
                Action(type="learning", id="stress-mgmt-1", label="Lär dig: Stresshantering",
                       metadata={"duration": "5 min", "contentType": "audio_article"}),
            ],
        },
        # ... other topics
    }

    def get_topic_keywords(self) -> Dict[str, List[str]]:
        return self.topic_keywords

    def get_fallback_actions(self, topic: str, language: str) -> List[Action]:
        topic_actions = self.fallback_actions.get(topic, {})
        return topic_actions.get(language, topic_actions.get("en", []))
```

### Example Handler Implementation

```python
# actions/types/learning.py

class LearningHandler(ActionHandler):
    """Handles learning/module action recommendations."""

    def __init__(self, retriever: ActionRetriever):
        self._retriever = retriever

    @property
    def action_type(self) -> str:
        return "learning"

    async def generate(self, topics, language, context) -> List[Action]:
        return await self._retriever.retrieve(topics, language, limit=2)


# actions/types/exercise.py

class ExerciseHandler(ActionHandler):
    """Handles exercise recommendations (breathing, calming, etc.)."""

    def __init__(self, retriever: ActionRetriever):
        self._retriever = retriever

    @property
    def action_type(self) -> str:
        return "exercise"

    async def generate(self, topics, language, context) -> List[Action]:
        # Filter to exercise-type actions only
        actions = await self._retriever.retrieve(topics, language)
        return [a for a in actions if a.metadata.get("contentType", "").startswith("audio_exercise")]
```

### Adding New Action Types

To add a new action type (e.g., journaling prompts):

1. Create handler in `actions/types/journal.py`:

```python
class JournalHandler(ActionHandler):
    @property
    def action_type(self) -> str:
        return "journal"

    async def generate(self, topics, language, context):
        # Return journaling prompts based on topics
        prompts = self._get_prompts_for_topics(topics, language)
        return [
            Action(
                type="journal",
                id=f"journal-{topic}",
                label=prompt,
                metadata={"promptType": "reflection"}
            )
            for topic, prompt in prompts.items()
        ]
```

2. Register in dependencies:

```python
registry.register(JournalHandler())
```

### Integration with CoachService

```python
# In coach_service.py

async def chat(self, user_id, message, ...):
    # ... existing streaming logic ...

    # After text streaming, generate actions
    actions = await self._action_generator.generate(
        message=message,
        language=language,
        context={"user_id": user_id}
    )

    # Stream actions chunk
    yield StreamChunk(type="actions", content=[a.dict() for a in actions])
```

### Frontend Integration

#### Backend Streaming Response

Actions are sent as part of the SSE (Server-Sent Events) stream after the text response:

```
data: {"type": "text", "content": "I understand you're feeling stressed..."}
data: {"type": "text", "content": " Let me suggest something that might help."}
data: {"type": "actions", "content": [
  {
    "type": "exercise",
    "id": "breathing-1",
    "label": "Try a Calming Exercise",
    "metadata": {"duration": "3 min", "contentType": "audio_exercise"}
  },
  {
    "type": "learning",
    "id": "stress-mgmt-1",
    "label": "Learn: Stress Management",
    "metadata": {"duration": "5 min", "contentType": "audio_article"}
  }
]}
data: {"type": "quickReplies", "content": ["Tell me more", "I'd like to try the exercise"]}
data: {"type": "metadata", "content": {"conversationId": "conv_123", "topics": ["stress"]}}
data: [DONE]
```

#### Frontend API Client (`coachApi.js`)

The `streamMessage` function already supports `onActions` callback:

```javascript
await coachApi.streamMessage(
  message,
  { conversationId, language },
  {
    onText: (content) => { /* Append to streaming message */ },
    onActions: (actions) => { /* Display action buttons */ },
    onQuickReplies: (replies) => { /* Display quick reply chips */ },
    onMetadata: (metadata) => { /* Store conversationId */ },
    onDone: () => { /* Finalize message */ },
  }
);
```

#### Frontend Component (`Coach.jsx`)

Handle actions in state and render as clickable cards:

```jsx
const [actions, setActions] = useState([]);

// In streamMessage callbacks
onActions: (actionList) => {
  setActions(actionList);
},

// Render action cards
{actions.length > 0 && (
  <div className="coach-actions">
    {actions.map((action) => (
      <button
        key={action.id}
        className={`action-card action-${action.type}`}
        onClick={() => handleActionClick(action)}
      >
        <span className="action-icon">{getActionIcon(action.type)}</span>
        <span className="action-label">{action.label}</span>
        {action.metadata?.duration && (
          <span className="action-duration">{action.metadata.duration}</span>
        )}
      </button>
    ))}
  </div>
)}
```

#### Action Click Handling

```javascript
function handleActionClick(action) {
  switch (action.type) {
    case 'exercise':
      // Navigate to exercise player
      navigate(`/exercises/${action.id}`);
      break;
    case 'learning':
      // Navigate to learning module
      navigate(`/learn/${action.id}`);
      break;
    case 'journal':
      // Open journaling modal with prompt
      openJournalModal(action.metadata.prompt);
      break;
    default:
      console.warn('Unknown action type:', action.type);
  }
}
```

#### CSS Classes

```css
.coach-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-card:hover {
  background: var(--surface-hover);
  transform: translateY(-2px);
}

.action-exercise { border-left: 3px solid var(--color-calm); }
.action-learning { border-left: 3px solid var(--color-primary); }
.action-journal { border-left: 3px solid var(--color-accent); }

.action-duration {
  font-size: 12px;
  color: var(--text-muted);
}
```

### RAG Extension Path

The architecture is designed for seamless RAG integration:

1. **Current:** `StaticRetriever` → `memory/knowledge.py` (hardcoded)
2. **Future:** `RAGRetriever` → Vector search → Content Library

```python
# Swap retriever without changing handlers
retriever = RAGRetriever(vector_store, embeddings)
registry.register(LearningHandler(retriever))
registry.register(ExerciseHandler(retriever))
```

The `Knowledge` class in `memory/` serves as the bridge:
- Now: Static dictionaries
- Future: Can query vector embeddings or external knowledge bases

---

## Component 4: Voice System

### Purpose

Provide text-to-speech capabilities for the AI coach responses using ElevenLabs API.

### Architecture

The voice system re-exports the `TTSService` from `services/media/` for use within the agent module.

```
app_v2/agent/voice/
└── __init__.py          # Re-exports TTSService

app_v2/services/media/
└── tts_service.py       # Actual TTS implementation (ElevenLabs)
```

### API Endpoint

```
POST /api/coach/voice
```

**Request:**
```json
{
  "text": "Hello, how can I help you today?",
  "voice": "Aria",
  "language": "en"
}
```

**Response:** `audio/mpeg` (MP3 binary)

### Configuration

```bash
ELEVENLABS_API_KEY=your_api_key
```

### Available Voices

| Voice Name | Voice ID | Description |
|------------|----------|-------------|
| Aria | fO844Om1VZLpw8IpZj3T | Default coach voice |
| Sarah | EXAVITQu4vr4xnSDxMaL | Standard female |
| Roger | CwhRBWXzGAHq8TQ4Fs17 | Standard male |

See `tts_service.py` for full voice mappings.

---

## SOLID Principles Applied

| Principle | Application |
|-----------|-------------|
| **S** - Single Responsibility | `MemoryProvider` handles storage; `Agent` handles AI; `ActionHandler` handles one action type; `TopicDetector` handles topic extraction |
| **O** - Open/Closed | Add `RAGMemory` without modifying `EncryptedMemory`; add new action handlers without modifying `ActionGenerator`; add new retrievers without changing handlers |
| **L** - Liskov Substitution | Any `MemoryProvider` works anywhere memory is used; any `ActionRetriever` works in any handler |
| **I** - Interface Segregation | Small focused interfaces: `MemoryProvider`, `Agent`, `ActionHandler`, `ActionRetriever` |
| **D** - Dependency Inversion | `ClaudeAgent` depends on `PromptService` abstraction; handlers depend on `ActionRetriever` interface, not concrete implementations |

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
   - `memory/knowledge.py` - Static knowledge store

2. **Agent System**
   - `types.py` - Dataclasses (move from services/coach/agent.py)
   - `prompt_service.py` - Dynamic prompt loading
   - `agent.py` - Abstract Agent
   - `claude_agent.py` - Claude implementation (uses `ClaudeProvider` from common/ai/)
   - `openai_agent.py` - (Optional) OpenAI implementation

3. **Actions System**
   - `actions/base.py` - Action schema and ActionHandler abstract class
   - `actions/registry.py` - ActionRegistry
   - `actions/topic_detector.py` - TopicDetector
   - `actions/retrieval/base.py` - ActionRetriever interface
   - `actions/retrieval/static.py` - StaticRetriever
   - `actions/generator.py` - ActionGenerator
   - `actions/types/learning.py` - LearningHandler
   - `actions/types/exercise.py` - ExerciseHandler

4. **Voice System**
   - `voice/__init__.py` - Re-export TTSService

5. **Integration**
   - Update `dependencies.py` to initialize action registry and handlers
   - Update `CoachService` to use `ActionGenerator` and stream actions
   - Add `AGENT_TYPE` environment variable support

---

## Quick Reference

| Component | File | Purpose |
|-----------|------|---------|
| **Memory** | | |
| `MemoryProvider` | `memory/provider.py` | Abstract memory interface |
| `MemoryEncryptionService` | `memory/encryption.py` | AES-256-CBC encryption |
| `EncryptedMemory` | `memory/encrypted_memory.py` | MongoDB + encryption |
| `Knowledge` | `memory/knowledge.py` | Static knowledge (topics, fallback actions) |
| **Agent** | | |
| `Agent` | `agent.py` | Abstract AI interface |
| `ClaudeAgent` | `claude_agent.py` | Claude implementation (uses `ClaudeProvider`) |
| `OpenAIAgent` | `openai_agent.py` | OpenAI implementation (uses `OpenAIProvider`) |
| `PromptService` | `prompt_service.py` | Dynamic prompts from MongoDB |
| `CoachingContext` | `types.py` | Context dataclass |
| **Actions** | | |
| `Action` | `actions/base.py` | Universal action schema |
| `ActionHandler` | `actions/base.py` | Abstract handler base class |
| `ActionRegistry` | `actions/registry.py` | Pluggable handler registry |
| `ActionGenerator` | `actions/generator.py` | Orchestrates action generation |
| `TopicDetector` | `actions/topic_detector.py` | Keyword-based topic extraction |
| **Actions - Retrieval** | | |
| `ActionRetriever` | `actions/retrieval/base.py` | Abstract retriever interface |
| `StaticRetriever` | `actions/retrieval/static.py` | Uses memory/knowledge fallbacks |
| `RAGRetriever` | `actions/retrieval/rag.py` | Vector search (future) |
| **Actions - Types** | | |
| `LearningHandler` | `actions/types/learning.py` | Learning recommendations |
| `ExerciseHandler` | `actions/types/exercise.py` | Exercise recommendations |
| **Voice** | | |
| `TTSService` | `services/media/tts_service.py` | ElevenLabs TTS |
| **Common (reused)** | | |
| `ClaudeProvider` | `common/ai/claude.py` | Low-level Claude API |
| `OpenAIProvider` | `common/ai/openai.py` | Low-level OpenAI API |

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

### 5. RAG for Actions

Implement `RAGRetriever` to replace static fallbacks:
- Vector embeddings for content library items
- Semantic matching of user message to relevant content
- MongoDB Atlas Vector Search or Pinecone integration
- Content items tagged with `coachTopics` for filtering

### 6. Additional Action Types

Extend the actions system with new handlers:
- `JournalHandler` - Journaling prompts based on topics
- `TeamActivityHandler` - Team exercises and activities
- `BookRecommendationHandler` - Reading suggestions
