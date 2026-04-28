"""
Topic detection for coaching conversations.

Extracts coaching topics from messages using keyword matching.
"""

from typing import List

from app_v2.agent.memory.knowledge import Knowledge, get_knowledge


class TopicDetector:
    """
    Extracts topics from user messages using keyword matching.

    Uses the Knowledge store for topic keywords.
    """

    def __init__(self, knowledge: Knowledge | None = None):
        """
        Initialize TopicDetector.

        Args:
            knowledge: Knowledge instance (uses singleton if not provided)
        """
        self._knowledge = knowledge or get_knowledge()

    def detect(self, message: str) -> List[str]:
        """
        Detect topics from message text.

        Uses keyword matching against the Knowledge store.

        Args:
            message: User message to analyze

        Returns:
            List of detected topic strings. Empty list if no topics matched.
        """
        message_lower = message.lower()
        topics: List[str] = []

        for topic, keywords in self._knowledge.topic_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    topics.append(topic)
                    break  # Only add topic once

        return topics

    def detect_with_scores(self, message: str) -> List[tuple[str, int]]:
        """
        Detect topics with match scores.

        Returns topics sorted by number of keyword matches.

        Args:
            message: User message to analyze

        Returns:
            List of (topic, score) tuples, sorted by score descending
        """
        message_lower = message.lower()
        scores: dict[str, int] = {}

        for topic, keywords in self._knowledge.topic_keywords.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[topic] = score

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
