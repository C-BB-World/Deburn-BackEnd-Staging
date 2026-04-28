"""
Coach service for BrainBank.

Handles AI coaching interactions using the common AI provider abstraction.
Supports streaming responses and conversation history.
"""

import json
from typing import AsyncGenerator, Optional, List, Dict, Any

from common.ai import AIProvider


class CoachService:
    """
    BrainBank AI coaching service.

    Uses the generic AIProvider interface to support multiple AI backends
    (Claude, OpenAI) while providing BrainBank-specific coaching logic.
    """

    def __init__(
        self,
        ai_provider: AIProvider,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """
        Initialize coach service.

        Args:
            ai_provider: AI provider instance (Claude, OpenAI, etc.)
            system_prompt: Default system prompt for coaching
            max_tokens: Maximum tokens in responses
            temperature: Sampling temperature
        """
        self.ai = ai_provider
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Get the default coaching system prompt."""
        return """You are Eve, an AI wellness and leadership coach for BrainBank.

Your role is to help users with:
- Daily wellness and mental health support
- Leadership development and career guidance
- Work-life balance and stress management
- Goal setting and accountability

Guidelines:
- Be warm, empathetic, and encouraging
- Ask thoughtful follow-up questions
- Provide practical, actionable advice
- Remember context from the conversation
- Keep responses concise but meaningful
- Use the user's name when appropriate
- Acknowledge emotions before offering solutions

If the user seems distressed, remind them that you're an AI and suggest
professional resources when appropriate."""

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send a message and get a response.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_context: Optional user context (name, recent check-ins, etc.)

        Returns:
            The coach's response
        """
        # Build system prompt with user context
        system = self._build_system_prompt(user_context)

        return await self.ai.chat(
            message=message,
            system_prompt=system,
            conversation_history=conversation_history,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

    async def stream_chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response in chunks.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_context: Optional user context

        Yields:
            Text chunks as they are generated
        """
        # Build system prompt with user context
        system = self._build_system_prompt(user_context)

        async for chunk in self.ai.stream_chat(
            message=message,
            system_prompt=system,
            conversation_history=conversation_history,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        ):
            yield chunk

    async def stream_chat_sse(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response formatted for Server-Sent Events (SSE).

        Yields SSE-formatted chunks including:
        - metadata: Initial metadata about the response
        - text: Text content chunks
        - actions: Suggested actions
        - quickReplies: Quick reply options
        - done: End of stream marker

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_context: Optional user context

        Yields:
            SSE-formatted strings (data: {...}\n\n)
        """
        # Send metadata first
        metadata = {
            "type": "metadata",
            "model": getattr(self.ai, "model", "unknown"),
            "timestamp": None,  # Will be set by caller
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        # Stream text content
        full_response = ""
        async for chunk in self.stream_chat(message, conversation_history, user_context):
            full_response += chunk
            text_chunk = {"type": "text", "content": chunk}
            yield f"data: {json.dumps(text_chunk)}\n\n"

        # Generate actions based on response
        actions = self._generate_actions(full_response, user_context)
        if actions:
            actions_chunk = {"type": "actions", "items": actions}
            yield f"data: {json.dumps(actions_chunk)}\n\n"

        # Generate quick replies
        quick_replies = self._generate_quick_replies(full_response, message)
        if quick_replies:
            replies_chunk = {"type": "quickReplies", "items": quick_replies}
            yield f"data: {json.dumps(replies_chunk)}\n\n"

        # Send done marker
        yield "data: [DONE]\n\n"

    def _build_system_prompt(
        self,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build system prompt with optional user context."""
        prompt = self.system_prompt

        if user_context:
            context_parts = []

            if user_context.get("name"):
                context_parts.append(f"User's name: {user_context['name']}")

            if user_context.get("organization"):
                context_parts.append(f"Organization: {user_context['organization']}")

            if user_context.get("recent_mood"):
                context_parts.append(
                    f"Recent mood trend: {user_context['recent_mood']}"
                )

            if user_context.get("streak"):
                context_parts.append(
                    f"Check-in streak: {user_context['streak']} days"
                )

            if user_context.get("language"):
                lang_name = "Swedish" if user_context["language"] == "sv" else "English"
                context_parts.append(f"Preferred language: {lang_name}")

            if context_parts:
                prompt += "\n\nUser context:\n" + "\n".join(f"- {p}" for p in context_parts)

        return prompt

    def _generate_actions(
        self,
        response: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate suggested actions based on response content."""
        actions = []

        # Check for goal-related content
        if any(word in response.lower() for word in ["goal", "commitment", "plan"]):
            actions.append({
                "type": "button",
                "label": "Set a Goal",
                "action": "setGoal",
            })

        # Check for check-in related content
        if any(word in response.lower() for word in ["check-in", "mood", "how you feel"]):
            actions.append({
                "type": "button",
                "label": "Do Check-in",
                "action": "startCheckIn",
            })

        # Check for learning content
        if any(word in response.lower() for word in ["learn", "resource", "article"]):
            actions.append({
                "type": "button",
                "label": "Explore Resources",
                "action": "openLearning",
            })

        return actions

    def _generate_quick_replies(
        self,
        response: str,
        original_message: str,
    ) -> List[str]:
        """Generate quick reply suggestions."""
        quick_replies = []

        # Add contextual quick replies
        if "?" in response:
            # Response contains a question, suggest common answers
            quick_replies.extend([
                "Yes, I'd like to explore that",
                "Can you tell me more?",
                "Not right now, thanks",
            ])
        else:
            # Response is a statement, suggest follow-ups
            quick_replies.extend([
                "That's helpful, thank you!",
                "Can you explain more?",
                "What else should I consider?",
            ])

        return quick_replies[:4]  # Limit to 4 quick replies

    def get_conversation_starters(
        self,
        language: str = "en",
    ) -> List[Dict[str, str]]:
        """Get conversation starter suggestions."""
        if language == "sv":
            return [
                {"text": "Hur kan jag hantera stress bättre?", "category": "wellness"},
                {"text": "Jag behöver hjälp med att sätta mål", "category": "goals"},
                {"text": "Hur kan jag förbättra min ledarskapsstil?", "category": "leadership"},
                {"text": "Jag känner mig överväldigad på jobbet", "category": "work"},
            ]

        return [
            {"text": "How can I manage stress better?", "category": "wellness"},
            {"text": "I need help setting goals", "category": "goals"},
            {"text": "How can I improve my leadership style?", "category": "leadership"},
            {"text": "I'm feeling overwhelmed at work", "category": "work"},
        ]
