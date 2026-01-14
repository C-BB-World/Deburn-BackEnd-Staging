"""
Message safety checker.

Checks messages for safety concerns using escalation levels.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result of safety check."""
    level: int  # 0=normal, 1=soft, 2=professional, 3=crisis
    is_crisis: bool
    triggers: List[str]
    detected_language: Optional[str]
    action: str  # 'normal', 'caution', 'redirect', 'escalate'


@dataclass
class CrisisResponse:
    """Crisis response for Level 3."""
    text: str
    resources: Dict[str, Any]
    metadata: Dict[str, Any]


class SafetyChecker:
    """
    Checks messages for safety concerns.
    References escalation levels from Hub System.
    """

    CRISIS_KEYWORDS = {
        "en": [
            "suicide", "suicidal", "kill myself", "end my life",
            "self-harm", "hurt myself", "cutting", "don't want to live",
            "panic attack", "can't breathe", "dying", "want to die"
        ],
        "sv": [
            "självmord", "ta livet av mig", "skada mig själv",
            "panikattack", "vill inte leva", "dö", "vill dö"
        ]
    }

    SOFT_KEYWORDS = {
        "en": [
            "exhausted", "overwhelmed", "can't sleep", "insomnia",
            "burning out", "at my limit", "breaking point", "crying",
            "hopeless", "worthless", "failing", "can't cope"
        ],
        "sv": [
            "utmattad", "överväldigad", "kan inte sova", "utbränd",
            "gråter", "hopplös", "värdelös", "klarar inte"
        ]
    }

    PROFESSIONAL_TOPICS = [
        "legal rights", "lawsuit", "harassment claim",
        "medical symptoms", "diagnosis", "medication",
        "therapy", "psychiatrist", "mental illness",
        "disability", "discrimination"
    ]

    CRISIS_RESPONSE_EN = """I hear that you're going through something really difficult right now. I'm not able to provide the support you need in this moment, but please know that you're not alone.

**If you're in crisis, please reach out to:**
- Emergency services: 112 (EU) or 911 (US)
- National Suicide Prevention Lifeline: 988 (US)
- Crisis Text Line: Text HOME to 741741 (US)
- Samaritans: 116 123 (UK)

These trained professionals are available 24/7 and can provide the support you need.

Would you like me to help you find resources specific to your location?"""

    CRISIS_RESPONSE_SV = """Jag hör att du går igenom något riktigt svårt just nu. Jag kan inte ge dig det stöd du behöver i detta ögonblick, men du är inte ensam.

**Om du är i kris, kontakta:**
- Nödnummer: 112
- Mind Självmordslinjen: 90101
- Jourhavande medmänniska: 08-702 16 80

Dessa utbildade professionella finns tillgängliga dygnet runt och kan ge dig det stöd du behöver.

Vill du att jag hjälper dig hitta resurser specifika för din plats?"""

    def __init__(self, hub_settings=None):
        """
        Initialize SafetyChecker.

        Args:
            hub_settings: Optional HubSettingsService for configuration
        """
        self._hub_settings = hub_settings

    def check(self, message: str) -> SafetyResult:
        """
        Check message for safety concerns.

        Args:
            message: User's message

        Returns:
            SafetyResult with level and action
        """
        is_crisis, crisis_trigger, language = self._check_level_3(message)
        if is_crisis:
            return SafetyResult(
                level=3,
                is_crisis=True,
                triggers=[crisis_trigger] if crisis_trigger else [],
                detected_language=language,
                action="escalate"
            )

        is_professional, professional_trigger = self._check_level_2(message)
        if is_professional:
            return SafetyResult(
                level=2,
                is_crisis=False,
                triggers=[professional_trigger] if professional_trigger else [],
                detected_language=None,
                action="redirect"
            )

        is_soft, soft_triggers, language = self._check_level_1(message)
        if is_soft:
            return SafetyResult(
                level=1,
                is_crisis=False,
                triggers=soft_triggers,
                detected_language=language,
                action="caution"
            )

        return SafetyResult(
            level=0,
            is_crisis=False,
            triggers=[],
            detected_language=None,
            action="normal"
        )

    def get_crisis_response(self, language: str = "en") -> CrisisResponse:
        """
        Get crisis response for Level 3 escalation.

        Args:
            language: 'en' or 'sv'

        Returns:
            CrisisResponse with resources
        """
        text = self.CRISIS_RESPONSE_SV if language == "sv" else self.CRISIS_RESPONSE_EN

        resources = {
            "emergency": "112" if language == "sv" else "911",
            "hotlines": [
                {"name": "Mind Självmordslinjen", "number": "90101"} if language == "sv"
                else {"name": "National Suicide Prevention Lifeline", "number": "988"}
            ]
        }

        return CrisisResponse(
            text=text,
            resources=resources,
            metadata={"intent": "crisis", "safetyLevel": 3}
        )

    def _check_level_3(self, message: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check for crisis keywords (all languages)."""
        message_lower = message.lower()

        for lang, keywords in self.CRISIS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    logger.warning(f"Crisis keyword detected: {keyword}")
                    return True, keyword, lang

        return False, None, None

    def _check_level_2(self, message: str) -> Tuple[bool, Optional[str]]:
        """Check for professional referral topics."""
        message_lower = message.lower()

        for topic in self.PROFESSIONAL_TOPICS:
            if topic in message_lower:
                return True, topic

        return False, None

    def _check_level_1(self, message: str) -> Tuple[bool, List[str], Optional[str]]:
        """Check for soft escalation keywords."""
        message_lower = message.lower()
        found_triggers = []
        detected_lang = None

        for lang, keywords in self.SOFT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    found_triggers.append(keyword)
                    detected_lang = lang

        return len(found_triggers) > 0, found_triggers, detected_lang
