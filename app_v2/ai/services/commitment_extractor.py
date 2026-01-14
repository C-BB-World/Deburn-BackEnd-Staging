"""
Commitment extractor service.

Extracts micro-commitments from coach responses.
"""

import re
import logging
from typing import Optional

from app_v2.ai.services.commitment_service import CommitmentData

logger = logging.getLogger(__name__)


class CommitmentExtractor:
    """
    Extracts structured micro-commitments from coach responses.
    """

    COMMITMENT_PATTERNS = [
        r"\*\*Micro-Commitment:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"\*\*Mikro-Åtagande:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"Micro-Commitment:\s*[\"']?(.+?)[\"']?(?:\n|$)",
    ]

    REFLECTION_PATTERNS = [
        r"\*\*Reflection Question:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"\*\*Reflektionsfråga:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"Reflection Question:\s*[\"']?(.+?)[\"']?(?:\n|$)",
    ]

    TRIGGER_PATTERNS = [
        r"\*\*Why This Matters:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"\*\*Varför det Spelar Roll:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"Why This Matters:\s*[\"']?(.+?)[\"']?(?:\n|$)",
    ]

    CIRCLE_PATTERNS = [
        r"\*\*For Your Leadership Circle:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
        r"\*\*För Din Ledarskapscirkel:\*\*\s*[\"']?(.+?)[\"']?(?:\n|$)",
    ]

    def extract(self, response_text: str) -> Optional[CommitmentData]:
        """
        Extract commitment data from coach response.

        Args:
            response_text: The coach's response

        Returns:
            CommitmentData if found, None otherwise
        """
        commitment = self._extract_pattern(response_text, self.COMMITMENT_PATTERNS)

        if not commitment:
            return None

        reflection = self._extract_pattern(response_text, self.REFLECTION_PATTERNS)
        trigger = self._extract_pattern(response_text, self.TRIGGER_PATTERNS)
        circle = self._extract_pattern(response_text, self.CIRCLE_PATTERNS)

        logger.info(f"Extracted commitment: {commitment[:50]}...")

        return CommitmentData(
            commitment=commitment[:1000],
            reflection_question=reflection[:500] if reflection else None,
            psychological_trigger=trigger[:500] if trigger else None,
            circle_prompt=circle[:500] if circle else None
        )

    def _extract_pattern(
        self,
        text: str,
        patterns: list[str]
    ) -> Optional[str]:
        """Extract first matching pattern."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                extracted = extracted.strip('"\'')
                return extracted
        return None
