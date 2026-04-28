# AI Coaching System

## Description

The AI Coaching System powers "Ask Eve" - an AI leadership coach that helps users grow, prevent burnout, and build psychologically safe teams. It handles conversational coaching, safety escalation, behavior change through micro-commitments, and personalized insights.

**Responsibilities:**
- Conduct streaming/non-streaming coaching conversations
- Check messages for safety concerns (reference Hub escalation levels)
- Extract topics and recommend relevant content
- Extract and track micro-commitments for behavior change
- Generate personalized insights after check-ins
- Detect patterns in user data for proactive recommendations
- Provide conversation starters based on wellbeing data

**Tech Stack:**
- **Agent** - Abstraction layer for AI operations (implementation TBD)
- **MongoDB** - Conversation history, commitments, insights
- **Content Service** - For content recommendations
- **Hub Settings** - Daily exchange limits, safety configuration

**AI Abstraction:**

All AI operations go through the `Agent` class. This allows swapping implementations (different models, RAG, memory systems) without changing the coaching logic.

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI COACHING SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │ CoachService│   │ InsightGen  │   │ CommitmentExtractor │   │
│  └──────┬──────┘   └──────┬──────┘   └──────────┬──────────┘   │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│                    ┌─────────────┐                              │
│                    │    Agent    │  ← You implement this        │
│                    │ (Abstract)  │                              │
│                    └─────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Safety Escalation Levels (from Hub System):**

| Level | Name | Action | Triggers |
|-------|------|--------|----------|
| 0 | Normal | Continue coaching | (default) |
| 1 | Soft Escalation | Continue with caution | "exhausted", "overwhelmed", "can't sleep" |
| 2 | Professional Referral | Redirect to expert | "legal rights", "medical symptoms" |
| 3 | Crisis | Stop coaching immediately | "suicide", "self-harm", "panic attack" |

---

## Pipelines

### Pipeline 1: Coaching Conversation

User sends a message and receives a streaming AI coach response with actions and quick replies.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COACHING CONVERSATION PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

User                             AI Coaching System                  External
────                             ──────────────────                  ────────
    │                                │                                   │
    │  send_message(                 │                                   │
    │    message, conversationId,    │                                   │
    │    language, context)          │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Check daily exchange limit    │
    │                                │     HubSettings.coachSettings     │
    │                                │     .dailyExchangeLimit           │
    │                                │                                   │
    │                                │     [If exceeded → return error]  │
    │                                │                                   │
    │                                │  2. Safety check                  │
    │                                │     SafetyChecker.check(message)  │
    │                                │                                   │
    │                                │     [If Level 3 → return crisis   │
    │                                │      response, stop here]         │
    │                                │                                   │
    │                                │  3. Load conversation history     │
    │                                │     ConversationService           │
    │                                │       .get_or_create()            │
    │                                │                                   │
    │                                │  4. Get due follow-ups            │
    │                                │     CommitmentService             │
    │                                │       .get_due_followups()        │
    │                                │                                   │
    │                                │  5. Build context                 │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ • User profile          │   │
    │                                │     │ • Wellbeing data        │   │
    │                                │     │ • Conversation history  │   │
    │                                │     │ • Due commitments       │   │
    │                                │     │ • Safety flags (L1)     │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  6. Generate response             │
    │                                │     Agent.generate_coaching_      │
    │                                │       response(context, message)  │
    │                                │                                   │
    │  [SSE Stream begins]           │                                   │
    │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │                                   │
    │                                │                                   │
    │  data: {type: "text", ...}     │  7. Stream response chunks        │
    │<───────────────────────────────│                                   │
    │  data: {type: "text", ...}     │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │                                │  8. Extract topics                │
    │                                │     TopicExtractor.extract()      │
    │                                │                                   │
    │                                │  9. Get content recommendations   │
    │                                │     ContentService.get_for_coach()│
    │                                │                                   │
    │                                │  10. Extract commitment           │
    │                                │      CommitmentExtractor          │
    │                                │        .extract(response)         │
    │                                │                                   │
    │                                │      [If found → save with        │
    │                                │       14-day follow-up]           │
    │                                │                                   │
    │                                │  11. Save to history              │
    │                                │      ConversationService.save()   │
    │                                │                                   │
    │                                │  12. Increment exchange count     │
    │                                │      User.coachExchanges++        │
    │                                │                                   │
    │  data: {type: "actions", ...}  │                                   │
    │<───────────────────────────────│                                   │
    │  data: {type: "quickReplies"}  │                                   │
    │<───────────────────────────────│                                   │
    │  data: {type: "metadata", ...} │                                   │
    │<───────────────────────────────│                                   │
    │  data: [DONE]                  │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Steps:**
1. Check if user has exceeded daily exchange limit (from Hub Settings)
2. Run safety check on incoming message
3. If Level 3 (crisis), return crisis response and stop
4. Load or create conversation with history
5. Get any commitments due for follow-up
6. Build context object with user data, wellbeing, history, and follow-ups
7. Call Agent to generate streaming response
8. Extract topics from user message and response
9. Get content recommendations matching topics
10. Extract micro-commitment from response (if present)
11. Save conversation turn to history
12. Increment user's daily exchange count
13. Stream actions, quick replies, and metadata

**SSE Event Types:**

| Type | Content |
|------|---------|
| `text` | Response text chunk |
| `actions` | Content recommendations (exercises, modules) |
| `quickReplies` | Suggested follow-up messages |
| `metadata` | conversationId, topics, commitment info |
| `[DONE]` | Stream complete |

**Error Cases:**
- Daily limit exceeded → 429 Too Many Requests
- Crisis detected → Return crisis response (not an error)
- Agent error → 500 Internal Server Error

---

### Pipeline 2: Check-in Insight Generation

After a user submits a check-in, generate a personalized insight and actionable tip.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CHECK-IN INSIGHT GENERATION PIPELINE                       │
└─────────────────────────────────────────────────────────────────────────────┘

Check-in System                  AI Coaching System
───────────────                  ──────────────────
    │                                │
    │  generate_checkin_insight(     │
    │    user_id, current_checkin)   │
    │───────────────────────────────>│
    │                                │
    │                                │  1. Get recent check-ins
    │                                │     CheckInService
    │                                │       .get_checkins_for_period()
    │                                │
    │                                │  2. Calculate trends
    │                                │     ┌─────────────────────────┐
    │                                │     │ • Mood change %         │
    │                                │     │ • Energy change %       │
    │                                │     │ • Stress change %       │
    │                                │     │ • Sleep patterns        │
    │                                │     └─────────────────────────┘
    │                                │
    │                                │  3. Build insight context
    │                                │     ┌─────────────────────────┐
    │                                │     │ • Current metrics       │
    │                                │     │ • Historical trends     │
    │                                │     │ • Day of week           │
    │                                │     │ • Current streak        │
    │                                │     └─────────────────────────┘
    │                                │
    │                                │  4. Generate insight
    │                                │     Agent.generate_checkin_
    │                                │       insight(context)
    │                                │
    │  { insight, tip }              │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Fetch recent check-ins (last 14-30 days)
2. Calculate trends (compare first half vs second half)
3. Build context with current metrics, trends, streak
4. Call Agent to generate insight and tip
5. Return insight (observation) and tip (actionable)

**Output Format:**
```python
{
    "insight": "Your stress tends to spike on Thursdays...",
    "tip": "Try the 2-minute breathing exercise before your 10am call"
}
```

**Error Cases:**
- Insufficient data → Return generic encouragement
- Agent error → Return fallback insight

---

### Pipeline 3: Pattern Detection & Insight Creation

Detect patterns in user data and create insights when triggers are matched.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  PATTERN DETECTION & INSIGHT CREATION PIPELINE                │
└─────────────────────────────────────────────────────────────────────────────┘

Progress System                  AI Coaching System                  Database
───────────────                  ──────────────────                  ────────
    │                                │                                   │
    │  detect_and_create_insights(   │                                   │
    │    user_id)                    │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Get check-in data             │
    │                                │     (last 30 days)                │
    │                                │                                   │
    │                                │  2. Detect patterns               │
    │                                │     PatternDetector.detect()      │
    │                                │                                   │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ Patterns detected:      │   │
    │                                │     │ • streak: 7 days        │   │
    │                                │     │ • morningCheckIns: 5    │   │
    │                                │     │ • stressDayPattern:     │   │
    │                                │     │   Thursday (4x)         │   │
    │                                │     │ • moodChange: +15%      │   │
    │                                │     │ • lowEnergyDays: 3      │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  3. Load active triggers          │
    │                                │     InsightService                │
    │                                │       .get_all_triggers()  ───────────>
    │                                │                                   │
    │                                │  4. For each trigger:             │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ a. Evaluate condition   │   │
    │                                │     │    against patterns     │   │
    │                                │     │                         │   │
    │                                │     │ b. Check duplicate      │   │
    │                                │     │    window (7 days)      │   │
    │                                │     │                         │   │
    │                                │     │ c. Build content from   │   │
    │                                │     │    template             │   │
    │                                │     │                         │   │
    │                                │     │ d. If recommendation    │   │
    │                                │     │    type → enhance       │   │
    │                                │     │    with Agent           │   │
    │                                │     │                         │   │
    │                                │     │ e. Create insight       │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │                                │  5. Save new insights ────────────────>
    │                                │                                   │
    │  { created: [...],             │                                   │
    │    patterns: {...} }           │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Steps:**
1. Fetch check-in data for detection period (default 30 days)
2. Run pattern detection algorithms
3. Load active insight triggers from database
4. For each trigger:
   - Evaluate condition against detected patterns
   - Check if similar insight was created recently (duplicate window)
   - Build title and description from template
   - If recommendation type, enhance description with Agent
   - Create insight document
5. Return created insights and detected patterns

**Pattern Types:**

| Pattern | Detection Logic |
|---------|-----------------|
| `streak` | Consecutive check-in days |
| `morningCheckIns` | Check-ins before 9am |
| `stressDayPattern` | Day with highest stress frequency (≥3x) |
| `moodChange` | % change between periods |
| `stressChange` | % change between periods |
| `lowEnergyDays` | Consecutive days with avg energy < 5 |
| `sleepMoodCorrelation` | Correlation coefficient (0-1) |

**Insight Types:**

| Type | AI Enhanced | Example |
|------|-------------|---------|
| `streak` | No | "One Week Strong!" |
| `pattern` | No | "Thursday Stress Pattern" |
| `trend` | No | "Mood on the Rise" |
| `recommendation` | Yes | "Energy Check-In" (with personalized tip) |

---

### Pipeline 4: Commitment Follow-up

Surface due commitments during coaching conversations and track completion.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       COMMITMENT FOLLOW-UP PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

                              DURING CONVERSATION
Coach Pipeline                   AI Coaching System                  Database
──────────────                   ──────────────────                  ────────
    │                                │                                   │
    │  get_due_followups(user_id)    │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Query commitments             │
    │                                │     status = "active"             │
    │                                │     followUpDate <= now  ─────────────>
    │                                │                                   │
    │  [commitments]                 │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
    │  build_followup_context(       │                                   │
    │    commitments, language)      │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  2. Format for prompt injection   │
    │                                │     ┌─────────────────────────┐   │
    │                                │     │ ## Follow-Up on         │   │
    │                                │     │ Previous Commitments    │   │
    │                                │     │                         │   │
    │                                │     │ 1. "Delegate the report │   │
    │                                │     │    to Sarah" (14 days)  │   │
    │                                │     │    Reflection: "What    │   │
    │                                │     │    did you notice?"     │   │
    │                                │     └─────────────────────────┘   │
    │                                │                                   │
    │  [context_string]              │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │

                              USER COMPLETES COMMITMENT
User                             AI Coaching System                  Database
────                             ──────────────────                  ────────
    │                                │                                   │
    │  complete_commitment(          │                                   │
    │    commitment_id,              │                                   │
    │    reflection_notes,           │                                   │
    │    helpfulness_rating)         │                                   │
    │───────────────────────────────>│                                   │
    │                                │                                   │
    │                                │  1. Validate ownership            │
    │                                │                                   │
    │                                │  2. Update commitment             │
    │                                │     status → "completed"          │
    │                                │     completedAt → now             │
    │                                │     reflectionNotes               │
    │                                │     helpfulnessRating  ───────────────>
    │                                │                                   │
    │  { success, commitment }       │                                   │
    │<───────────────────────────────│                                   │
    │                                │                                   │
```

**Follow-up Context Injection:**

When commitments are due, they're injected into the coaching context so the Agent can naturally follow up:

```markdown
## Follow-Up on Previous Commitments

The user has pending micro-commitments to follow up on:

**1. Commitment** (14 days ago):
"Delegate the weekly report to Sarah"
Reflection question: "What did you notice about trust?"

Ask how it went and what they learned.
```

**Commitment Lifecycle:**

```
active → completed (user marks done with reflection)
      → dismissed (user skips)
      → expired (30 days without action)
```

---

### Pipeline 5: Conversation Starters

Generate personalized conversation starters based on user's wellbeing data.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONVERSATION STARTERS PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

Frontend                         AI Coaching System
────────                         ──────────────────
    │                                │
    │  get_starters(                 │
    │    language,                   │
    │    wellbeing_data)             │
    │───────────────────────────────>│
    │                                │
    │                                │  1. Analyze wellbeing
    │                                │     ┌─────────────────────────┐
    │                                │     │ stress: 8 → high        │
    │                                │     │ energy: 3 → low         │
    │                                │     │ mood: 2 → concerning    │
    │                                │     └─────────────────────────┘
    │                                │
    │                                │  2. Prioritize starters
    │                                │     based on wellbeing:
    │                                │
    │                                │     stress ≥ 7 →
    │                                │       "My stress has been
    │                                │        building up"
    │                                │
    │                                │     energy ≤ 4 →
    │                                │       "I'm feeling low on
    │                                │        energy lately"
    │                                │
    │                                │     mood ≤ 2 →
    │                                │       "I've been feeling
    │                                │        off lately"
    │                                │
    │                                │  3. Add default starters
    │                                │     (leadership, team, etc.)
    │                                │
    │  { starters: [...] }           │
    │<───────────────────────────────│
    │                                │
```

**Steps:**
1. Analyze wellbeing metrics (stress, energy, mood)
2. Prioritize starters based on concerning metrics
3. Fill remaining slots with default leadership starters
4. Return localized starters (max 4)

**Starter Selection Logic:**

| Condition | Starter (EN) | Starter (SV) |
|-----------|--------------|--------------|
| stress ≥ 7 | "My stress has been building up" | "Min stress har ökat på sistone" |
| energy ≤ 4 | "I'm feeling low on energy lately" | "Jag känner mig energilös på sistone" |
| mood ≤ 2 | "I've been feeling off lately" | "Jag har inte mått så bra på sistone" |
| default | "I want to work on my leadership" | "Jag vill utveckla mitt ledarskap" |

---

## Components

### Agent (Abstract - You Implement)

The abstraction layer for all AI operations. Implementation details (model, prompts, RAG, memory) are hidden behind this interface.

```python
class Agent:
    """
    Abstract AI agent for coaching operations.
    Implementation provided separately - may use LLMs, RAG, memory systems.

    All methods receive structured context and return structured output.
    The Agent is responsible for prompt construction internally.
    """

    def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> Iterator[str] | str:
        """
        Generate a coaching response.

        Args:
            context: CoachingContext with user data, history, follow-ups
            message: User's message
            stream: Whether to stream response

        Returns:
            Iterator of text chunks if streaming, else full response string

        Context includes:
            - user_profile: name, role, organization
            - wellbeing: mood, energy, stress, streak
            - conversation_history: previous messages
            - due_commitments: commitments to follow up on
            - safety_level: 0, 1, or 2 (3 handled before calling Agent)
            - language: 'en' or 'sv'
        """
        raise NotImplementedError

    def generate_checkin_insight(
        self,
        context: CheckinInsightContext
    ) -> CheckinInsight:
        """
        Generate insight and tip after check-in.

        Args:
            context: CheckinInsightContext with metrics and trends

        Returns:
            CheckinInsight with insight string and tip string

        Context includes:
            - current_checkin: today's metrics
            - trends: mood_change, energy_change, stress_change
            - streak: current streak count
            - day_of_week: for pattern awareness
            - language: 'en' or 'sv'
        """
        raise NotImplementedError

    def enhance_recommendation(
        self,
        base_description: str,
        patterns: dict,
        language: str = "en"
    ) -> str:
        """
        Enhance a recommendation insight with personalized advice.

        Args:
            base_description: Template-generated description
            patterns: Detected patterns dict
            language: 'en' or 'sv'

        Returns:
            Enhanced description string
        """
        raise NotImplementedError

    def extract_topics(
        self,
        message: str
    ) -> list[str]:
        """
        Extract coaching topics from a message.

        Args:
            message: User message or coach response

        Returns:
            List of topic strings from enum:
            ['delegation', 'stress', 'team_dynamics', 'communication',
             'leadership', 'time_management', 'conflict', 'burnout',
             'motivation', 'decision_making', 'mindfulness', 'resilience']

        Note: Can be rule-based or AI-powered depending on implementation.
        """
        raise NotImplementedError
```

---

### CoachService

Orchestrates coaching conversations with safety checking, history, and follow-ups.

```python
class CoachService:
    """
    Main service for AI coaching conversations.
    Coordinates Agent, safety, history, and commitments.
    """

    def __init__(
        self,
        agent: Agent,
        safety_checker: SafetyChecker,
        conversation_service: ConversationService,
        commitment_service: CommitmentService,
        content_service: ContentService,
        hub_settings: HubSettingsService,
        user_service: UserService
    ):
        """
        Args:
            agent: AI agent for response generation
            safety_checker: For message safety checking
            conversation_service: For history management
            commitment_service: For commitment tracking
            content_service: For content recommendations
            hub_settings: For daily limits and config
            user_service: For user data and exchange counting
        """

    def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        language: str = "en",
        stream: bool = True
    ) -> CoachResponse | Iterator[CoachResponseChunk]:
        """
        Send a message and get a coaching response.

        Args:
            user_id: User's ID
            message: User's message
            conversation_id: Existing conversation or None for new
            language: 'en' or 'sv'
            stream: Whether to stream response

        Returns:
            CoachResponse or iterator of chunks if streaming

        Raises:
            RateLimitError: Daily exchange limit exceeded
        """

    def get_starters(
        self,
        user_id: str,
        language: str = "en",
        include_wellbeing: bool = True
    ) -> list[ConversationStarter]:
        """
        Get personalized conversation starters.

        Args:
            user_id: User's ID
            language: 'en' or 'sv'
            include_wellbeing: Whether to use wellbeing data

        Returns:
            List of up to 4 starters with label and context
        """

    def get_history(
        self,
        conversation_id: str
    ) -> Conversation | None:
        """Get conversation history."""

    def _check_daily_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded daily exchange limit.
        Limit from HubSettings.coachSettings.dailyExchangeLimit
        """

    def _build_context(
        self,
        user_id: str,
        conversation: Conversation,
        language: str
    ) -> CoachingContext:
        """Build context object for Agent."""

    def _increment_exchange_count(self, user_id: str) -> None:
        """Increment user's daily exchange count."""
```

---

### SafetyChecker

Checks messages for safety concerns using Hub escalation levels.

```python
class SafetyChecker:
    """
    Checks messages for safety concerns.
    References escalation levels from Hub System.
    """

    # Keywords loaded from Hub or hardcoded
    CRISIS_KEYWORDS: dict[str, list[str]]  # Level 3
    SOFT_KEYWORDS: dict[str, list[str]]    # Level 1
    PROFESSIONAL_TOPICS: list[str]         # Level 2

    def __init__(self, hub_settings: HubSettingsService = None):
        """
        Args:
            hub_settings: For loading safety configuration (optional)
        """

    def check(self, message: str) -> SafetyResult:
        """
        Check message for safety concerns.

        Args:
            message: User's message

        Returns:
            SafetyResult with:
                - level: 0 (normal), 1 (soft), 2 (professional), 3 (crisis)
                - is_crisis: bool
                - triggers: list of matched keywords
                - detected_language: 'en' or 'sv'
                - action: 'normal', 'caution', 'redirect', 'escalate'
        """

    def get_crisis_response(self, language: str = "en") -> CrisisResponse:
        """
        Get crisis response for Level 3 escalation.

        Args:
            language: 'en' or 'sv'

        Returns:
            CrisisResponse with:
                - text: Empathetic message with resources
                - resources: Emergency numbers, hotlines
                - metadata: { intent: 'crisis', safetyLevel: 3 }
        """

    def _check_level_3(self, message: str) -> tuple[bool, str | None, str | None]:
        """Check for crisis keywords (all languages)."""

    def _check_level_2(self, message: str) -> tuple[bool, str | None]:
        """Check for professional referral topics."""

    def _check_level_1(self, message: str) -> tuple[bool, list[str], str | None]:
        """Check for soft escalation keywords."""
```

---

### ConversationService

Manages conversation history and persistence.

```python
class ConversationService:
    """
    Manages coaching conversation history.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def get_or_create(
        self,
        conversation_id: str | None,
        user_id: str
    ) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            conversation_id: Existing ID or None for new
            user_id: User's ID

        Returns:
            Conversation object with messages history
        """

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict = None
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (topics, commitment, etc.)
        """

    def get_recent_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> list[Conversation]:
        """Get user's recent conversations."""

    def get_conversation(
        self,
        conversation_id: str
    ) -> Conversation | None:
        """Get single conversation by ID."""

    def update_topics(
        self,
        conversation_id: str,
        topics: list[str]
    ) -> None:
        """Update detected topics for conversation."""
```

---

### CommitmentService

Manages micro-commitments and follow-ups.

```python
class CommitmentService:
    """
    Tracks micro-commitments from coaching conversations.
    Handles 14-day follow-up cycle.
    """

    def __init__(self, db: Database):
        """
        Args:
            db: MongoDB database connection
        """

    def create_commitment(
        self,
        user_id: str,
        conversation_id: str,
        commitment_data: CommitmentData,
        topic: str = "other"
    ) -> Commitment:
        """
        Create a new commitment with 14-day follow-up.

        Args:
            user_id: User's ID
            conversation_id: Source conversation
            commitment_data: Extracted commitment data
            topic: Coaching topic

        Returns:
            Created Commitment with followUpDate set
        """

    def get_due_followups(self, user_id: str) -> list[Commitment]:
        """
        Get commitments due for follow-up.

        Args:
            user_id: User's ID

        Returns:
            Commitments where status='active' and followUpDate <= now
        """

    def get_active_commitments(self, user_id: str) -> list[Commitment]:
        """Get all active commitments for user."""

    def complete_commitment(
        self,
        commitment_id: str,
        user_id: str,
        reflection_notes: str = None,
        helpfulness_rating: int = None
    ) -> Commitment:
        """
        Mark commitment as completed.

        Args:
            commitment_id: Commitment ID
            user_id: User's ID (for validation)
            reflection_notes: User's reflection (max 2000 chars)
            helpfulness_rating: 1-5 rating

        Returns:
            Updated Commitment

        Raises:
            NotFoundError: If commitment not found or wrong user
        """

    def dismiss_commitment(
        self,
        commitment_id: str,
        user_id: str
    ) -> Commitment:
        """Mark commitment as dismissed."""

    def get_stats(self, user_id: str) -> CommitmentStats:
        """
        Get commitment statistics.

        Returns:
            CommitmentStats with:
                - active: int
                - completed: int
                - expired: int
                - dismissed: int
                - total: int
                - completion_rate: int (percentage)
        """

    def expire_old_commitments(self, days_old: int = 30) -> int:
        """
        Expire commitments older than threshold.
        Called by cron job.

        Returns:
            Count of commitments expired
        """

    def build_followup_context(
        self,
        commitments: list[Commitment],
        language: str = "en"
    ) -> str:
        """
        Build context string for prompt injection.

        Args:
            commitments: Due commitments
            language: 'en' or 'sv'

        Returns:
            Formatted markdown string for system prompt
        """
```

---

### CommitmentExtractor

Extracts micro-commitments from coach responses.

```python
class CommitmentExtractor:
    """
    Extracts structured micro-commitments from coach responses.
    Looks for specific patterns in the response text.
    """

    def extract(self, response_text: str) -> CommitmentData | None:
        """
        Extract commitment data from coach response.

        Args:
            response_text: The coach's response

        Returns:
            CommitmentData if found, None otherwise

        Looks for patterns:
            - **Micro-Commitment:** "..."
            - **Reflection Question:** "..."
            - **Why This Matters:** "..."
            - **For Your Leadership Circle:** "..."

        CommitmentData:
            - commitment: str (max 1000 chars)
            - reflection_question: str | None (max 500 chars)
            - psychological_trigger: str | None (max 500 chars)
            - circle_prompt: str | None (max 500 chars)
        """

    def _extract_pattern(
        self,
        text: str,
        patterns: list[str]
    ) -> str | None:
        """Extract first matching pattern."""
```

---

### CheckinInsightGenerator

Generates insights after check-in submission.

```python
class CheckinInsightGenerator:
    """
    Generates personalized insights after check-in.
    Called by Check-in System after submission.
    """

    def __init__(
        self,
        agent: Agent,
        checkin_service: CheckInService
    ):
        """
        Args:
            agent: AI agent for insight generation
            checkin_service: For historical check-in data
        """

    def generate(
        self,
        user_id: str,
        current_checkin: dict,
        language: str = "en"
    ) -> CheckinInsight:
        """
        Generate insight and tip for a check-in.

        Args:
            user_id: User's ID
            current_checkin: Just-submitted check-in metrics
            language: 'en' or 'sv'

        Returns:
            CheckinInsight with:
                - insight: str (pattern observation)
                - tip: str (actionable recommendation)
        """

    def _get_historical_data(
        self,
        user_id: str,
        days: int = 14
    ) -> list[dict]:
        """Get recent check-ins for trend analysis."""

    def _calculate_trends(
        self,
        checkins: list[dict]
    ) -> dict:
        """
        Calculate trend metrics.

        Returns:
            dict with mood_change, energy_change, stress_change
        """

    def _build_context(
        self,
        current: dict,
        trends: dict,
        streak: int,
        language: str
    ) -> CheckinInsightContext:
        """Build context for Agent."""
```

---

### PatternDetector

Detects patterns in check-in data for insight generation.

```python
class PatternDetector:
    """
    Analyzes check-in data to detect behavioral patterns.
    Used by Progress System for trigger-based insights.
    """

    def __init__(self, checkin_service: CheckInService):
        """
        Args:
            checkin_service: For fetching check-in data
        """

    def detect(
        self,
        user_id: str,
        days: int = 30
    ) -> PatternResult | None:
        """
        Detect patterns in user's check-in data.

        Args:
            user_id: User's ID
            days: Days of data to analyze

        Returns:
            PatternResult or None if insufficient data (< 5 check-ins)

        PatternResult contains:
            - streak: { current: int }
            - morning_checkins: int (before 9am)
            - stress_day_pattern: { weekday: str, count: int } | None
            - mood_change: int (percentage) | None
            - stress_change: int (percentage) | None
            - low_energy_days: int (consecutive)
            - sleep_mood_correlation: float (0-1)
        """

    def _count_morning_checkins(self, checkins: list[dict]) -> int:
        """Count check-ins submitted before 9am."""

    def _detect_stress_day_pattern(
        self,
        checkins: list[dict]
    ) -> dict | None:
        """
        Find day with highest stress frequency.
        Returns pattern if ≥3 occurrences.
        """

    def _calculate_metric_change(
        self,
        checkins: list[dict],
        metric: str
    ) -> int | None:
        """Calculate % change between first and second half."""

    def _count_low_energy_streak(self, checkins: list[dict]) -> int:
        """Count consecutive recent days with avg energy < 5."""

    def _calculate_sleep_mood_correlation(
        self,
        checkins: list[dict]
    ) -> float:
        """Calculate correlation between sleep and mood."""
```

---

### QuickReplyGenerator

Generates contextual quick reply suggestions.

```python
class QuickReplyGenerator:
    """
    Generates quick reply suggestions based on conversation context.
    """

    def generate(
        self,
        response_text: str,
        topics: list[str],
        language: str = "en"
    ) -> list[str]:
        """
        Generate quick reply suggestions.

        Args:
            response_text: Coach's response
            topics: Detected topics
            language: 'en' or 'sv'

        Returns:
            List of 2 quick reply strings

        Topic-specific replies when available:
            - delegation: "I don't trust they'll do it right"
            - stress: "My workload is too high"
            - burnout: "I'm feeling exhausted"

        Default replies:
            - "Tell me more"
            - "What should I try?"
        """
```

---

## Data Models

### Conversation (Collection)

```python
# conversations collection
{
    "_id": ObjectId,
    "conversationId": str,         # Unique ID (conv_timestamp_random)
    "userId": ObjectId,            # Reference to User
    "messages": [{
        "role": str,               # "user" | "assistant"
        "content": str,            # Message text
        "timestamp": datetime,
        "metadata": dict           # Optional: topics, commitment, etc.
    }],
    "topics": [str],               # Accumulated topics
    "status": str,                 # "active" | "archived"
    "lastMessageAt": datetime,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ conversationId: 1 }` - Unique
- `{ userId: 1, lastMessageAt: -1 }` - User's recent conversations
- `{ userId: 1, status: 1 }` - Active conversations
- `{ lastMessageAt: 1 }` - TTL index for archival (optional)

---

### CoachCommitment (Collection)

```python
# coach_commitments collection
{
    "_id": ObjectId,
    "userId": ObjectId,            # Reference to User
    "conversationId": str,         # Source conversation
    "commitment": str,             # The commitment text (max 1000)
    "trigger": str,                # Implementation intention trigger
    "reflectionQuestion": str,     # Question to consider
    "psychologicalTrigger": str,   # Why this matters
    "circlePrompt": str,           # Leadership Circle suggestion
    "topic": str,                  # Coaching topic enum
    "status": str,                 # "active" | "completed" | "expired" | "dismissed"
    "followUpDate": datetime,      # When to follow up (default: +14 days)
    "completedAt": datetime,       # When completed
    "reflectionNotes": str,        # User's reflection (max 2000)
    "helpfulnessRating": int,      # 1-5 rating
    "followUpCount": int,          # Times surfaced in follow-ups
    "lastFollowUpAt": datetime,
    "createdAt": datetime,
    "updatedAt": datetime
}
```

**Indexes:**
- `{ userId: 1, status: 1 }` - User's commitments by status
- `{ userId: 1, followUpDate: 1 }` - Due follow-ups
- `{ status: 1, followUpDate: 1 }` - Global follow-up query
- `{ conversationId: 1 }` - Commitments from conversation

---

### UserExchangeCount (In User Document)

```python
# In User document
{
    "coachExchanges": {
        "count": int,              # Total exchanges
        "dailyCount": int,         # Today's exchanges
        "lastExchangeAt": datetime,
        "lastResetAt": datetime    # When dailyCount was reset
    }
}
```

---

## Configuration

```python
# Environment variables

# Agent configuration (implementation-specific)
AGENT_TYPE = "claude"                    # Agent implementation to use
AGENT_MODEL = "claude-sonnet-4-5"        # Model for Claude agent
AGENT_MAX_TOKENS = 1024                  # Max response tokens

# Safety configuration
SAFETY_LEVEL_3_ENABLED = true            # Enable crisis detection
SAFETY_LEVEL_2_ENABLED = true            # Enable professional referral
SAFETY_LEVEL_1_ENABLED = true            # Enable soft escalation

# Commitment configuration
COMMITMENT_FOLLOWUP_DAYS = 14            # Days until follow-up
COMMITMENT_EXPIRY_DAYS = 30              # Days until auto-expire
COMMITMENT_MAX_ACTIVE = 5                # Max active per user

# Pattern detection
PATTERN_DETECTION_DAYS = 30              # Days of data to analyze
PATTERN_MIN_CHECKINS = 5                 # Minimum check-ins required

# Hub Settings (from database)
# HubSettings.coachSettings.dailyExchangeLimit = 15
```

---

## Integration Points

### With Hub System

```python
# Daily exchange limit from Hub Settings
limit = hub_settings.get_coach_settings().daily_exchange_limit

# Safety keywords (future: from Hub)
safety_config = hub_settings.get_safety_config()
```

### With Check-in System

```python
# Generate insight after check-in submission
insight = checkin_insight_generator.generate(user_id, checkin, language)

# Pattern detection uses check-in data
patterns = pattern_detector.detect(user_id, days=30)
```

### With Content System

```python
# Get recommendations for detected topics
recommendations = content_service.get_for_coach(topics, limit=2)
```

### With Progress System

```python
# Pattern-based insights
patterns = pattern_detector.detect(user_id)
insights = insight_engine.generate_from_patterns(user_id, patterns)
```

---

## Coaching Topics Enum

```python
COACHING_TOPICS = [
    'delegation',
    'stress',
    'team_dynamics',
    'communication',
    'leadership',
    'time_management',
    'conflict',
    'burnout',
    'motivation',
    'decision_making',
    'mindfulness',
    'resilience',
    'psychological_safety',
    'emotional_regulation',
    'feedback',
    'other'
]
```

---

## Quick Reference

| Component | Purpose |
|-----------|---------|
| `Agent` | AI abstraction (you implement) |
| `CoachService` | Conversation orchestration |
| `SafetyChecker` | Message safety (Hub levels) |
| `ConversationService` | History management |
| `CommitmentService` | Follow-up tracking |
| `CommitmentExtractor` | Extract from responses |
| `CheckinInsightGenerator` | Post check-in insights |
| `PatternDetector` | Behavioral patterns |
| `QuickReplyGenerator` | Suggested replies |
