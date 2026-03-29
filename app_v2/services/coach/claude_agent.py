"""
Claude-based AI agent implementation.

Implements the Agent interface using Anthropic's Claude API.
"""

import logging
import re
from typing import Optional, List, Dict, Any, Iterator, AsyncIterator

import anthropic

from app_v2.services.coach.agent import Agent, CoachingContext, CheckinInsightContext, CheckinInsight

logger = logging.getLogger(__name__)


COACHING_TOPICS = [
    'delegation', 'stress', 'team_dynamics', 'communication',
    'leadership', 'time_management', 'conflict', 'burnout',
    'motivation', 'decision_making', 'mindfulness', 'resilience',
    'psychological_safety', 'emotional_regulation', 'feedback', 'other'
]

TOPIC_KEYWORDS = {
    'delegation': ['delegate', 'delegating', 'assign', 'trust', 'let go'],
    'stress': ['stress', 'stressful', 'overwhelmed', 'pressure', 'anxious'],
    'team_dynamics': ['team', 'group', 'collaborate', 'dynamics', 'working together'],
    'communication': ['communicate', 'conversation', 'feedback', 'listen', 'speak'],
    'leadership': ['leader', 'leadership', 'lead', 'manage', 'guide'],
    'time_management': ['time', 'prioritize', 'schedule', 'busy', 'deadline'],
    'conflict': ['conflict', 'disagreement', 'tension', 'difficult conversation'],
    'burnout': ['burnout', 'exhausted', 'tired', 'depleted', 'drained'],
    'motivation': ['motivation', 'motivated', 'purpose', 'drive', 'engagement'],
    'decision_making': ['decision', 'decide', 'choice', 'uncertain'],
    'mindfulness': ['mindful', 'present', 'aware', 'focus', 'meditation'],
    'resilience': ['resilience', 'resilient', 'bounce back', 'recover', 'adapt'],
    'psychological_safety': ['safe', 'safety', 'speak up', 'fear', 'trust'],
    'emotional_regulation': ['emotion', 'feeling', 'regulate', 'calm', 'react'],
    'feedback': ['feedback', 'critique', 'review', 'performance'],
}


class ClaudeAgent(Agent):
    """
    Claude-based AI agent for coaching.
    """

    SYSTEM_PROMPT_EN = """You are Eve, an AI leadership coach focused on helping leaders grow, prevent burnout, and build psychologically safe teams.

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

Keep your responses focused and around 150-250 words."""

    SYSTEM_PROMPT_SV = """Du är Eve, en AI-ledarskapscoach som fokuserar på att hjälpa ledare att växa, förebygga utbrändhet och bygga psykologiskt trygga team.

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

Håll dina svar fokuserade och omkring 150-250 ord."""

    CHECKIN_INSIGHT_PROMPT_EN = """Based on the user's check-in data, provide a brief personalized insight and actionable tip.

Current check-in:
- Mood: {mood}/5
- Energy: {energy}/10
- Stress: {stress}/10
- Sleep: {sleep}/5

Trends (last {days} days):
- Mood change: {mood_change}%
- Energy change: {energy_change}%
- Stress change: {stress_change}%

Current streak: {streak} days

Provide:
1. A brief insight (1-2 sentences observing a pattern or trend)
2. A practical tip (1 sentence, actionable)

Format your response as:
INSIGHT: [your insight here]
TIP: [your tip here]"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250514",
        max_tokens: int = 1024
    ):
        """
        Initialize ClaudeAgent.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum response tokens
        """
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def generate_coaching_response(
        self,
        context: CoachingContext,
        message: str,
        stream: bool = True
    ) -> AsyncIterator[str] | str:
        """Generate a coaching response."""
        system_prompt = self._build_system_prompt(context)
        messages = self._build_messages(context, message)

        if stream:
            return self._stream_response(system_prompt, messages)
        else:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text

    async def _stream_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> AsyncIterator[str]:
        """Stream response chunks."""
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def _build_system_prompt(self, context: CoachingContext) -> str:
        """Build system prompt with context."""
        base_prompt = self.SYSTEM_PROMPT_EN if context.language == "en" else self.SYSTEM_PROMPT_SV

        context_parts = [base_prompt, "\n\n## Context About This User\n"]

        if context.user_profile:
            name = context.user_profile.get("firstName", "")
            role = context.user_profile.get("role", "")
            if name:
                context_parts.append(f"Name: {name}\n")
            if role:
                context_parts.append(f"Role: {role}\n")

        if context.wellbeing:
            context_parts.append("\n## Recent Wellbeing\n")
            for key, value in context.wellbeing.items():
                context_parts.append(f"- {key}: {value}\n")

        if context.due_commitments:
            context_parts.append("\n## Follow-Up on Previous Commitments\n")
            context_parts.append("The user has pending micro-commitments to follow up on:\n\n")
            for i, commitment in enumerate(context.due_commitments, 1):
                context_parts.append(f"**{i}. Commitment:**\n")
                context_parts.append(f'"{commitment.get("commitment", "")}"\n')
                if commitment.get("reflectionQuestion"):
                    context_parts.append(f'Reflection question: "{commitment["reflectionQuestion"]}"\n')
                context_parts.append("\n")
            context_parts.append("Ask how it went and what they learned.\n")

        if context.safety_level == 1:
            context_parts.append("\n## Note\n")
            context_parts.append("The user seems to be going through a difficult time. Be extra empathetic and supportive.\n")

        return "".join(context_parts)

    def _build_messages(
        self,
        context: CoachingContext,
        current_message: str
    ) -> List[Dict[str, str]]:
        """Build message history for API."""
        messages = []

        for msg in context.conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        messages.append({
            "role": "user",
            "content": current_message
        })

        return messages

    async def generate_checkin_insight(
        self,
        context: CheckinInsightContext
    ) -> CheckinInsight:
        """Generate insight and tip after check-in."""
        prompt = self.CHECKIN_INSIGHT_PROMPT_EN.format(
            mood=context.current_checkin.get("mood", 3),
            energy=context.current_checkin.get("energy", 5),
            stress=context.current_checkin.get("stress", 5),
            sleep=context.current_checkin.get("sleep", 3),
            days=14,
            mood_change=context.trends.get("mood_change", 0),
            energy_change=context.trends.get("energy_change", 0),
            stress_change=context.trends.get("stress_change", 0),
            streak=context.streak
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text
            insight, tip = self._parse_insight_response(text)

            return CheckinInsight(insight=insight, tip=tip)

        except Exception as e:
            logger.error(f"Failed to generate check-in insight: {e}")
            return CheckinInsight(
                insight="Keep checking in! Consistency helps build self-awareness.",
                tip="Take a moment today to notice how you're feeling."
            )

    def _parse_insight_response(self, text: str) -> tuple[str, str]:
        """Parse insight and tip from response."""
        insight = ""
        tip = ""

        insight_match = re.search(r'INSIGHT:\s*(.+?)(?=TIP:|$)', text, re.DOTALL)
        if insight_match:
            insight = insight_match.group(1).strip()

        tip_match = re.search(r'TIP:\s*(.+?)$', text, re.DOTALL)
        if tip_match:
            tip = tip_match.group(1).strip()

        if not insight:
            insight = "Keep tracking your wellbeing for personalized insights."
        if not tip:
            tip = "Try taking a few deep breaths before your next meeting."

        return insight, tip

    async def enhance_recommendation(
        self,
        base_description: str,
        patterns: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """Enhance a recommendation with personalized advice."""
        prompt = f"""Based on these detected patterns:
{patterns}

Enhance this recommendation with a personalized tip:
"{base_description}"

Keep it brief (1-2 sentences) and actionable."""

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Failed to enhance recommendation: {e}")
            return base_description

    def extract_topics(self, message: str) -> List[str]:
        """Extract coaching topics from a message."""
        message_lower = message.lower()
        found_topics = []

        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    found_topics.append(topic)
                    break

        return found_topics if found_topics else ['other']
