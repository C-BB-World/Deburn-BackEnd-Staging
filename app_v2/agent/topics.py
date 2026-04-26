"""
Topic extraction for coaching conversations.

Extracts coaching topics from messages using keyword matching.
Uses the Knowledge singleton as the single source of truth for keywords.
"""

from typing import List

from app_v2.agent.memory.knowledge import get_knowledge


def _get_topic_keywords():
    """Get topic keywords from the Knowledge singleton."""
    return get_knowledge().get_topic_keywords()


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
    'other'
]


def extract_topics(message: str) -> List[str]:
    """
    Extract coaching topics from a message.

    Uses keyword matching to identify relevant topics.

    Args:
        message: User message or coach response

    Returns:
        List of topic strings. Returns ['other'] if no topics matched.
    """
    message_lower = message.lower()
    found_topics = []

    for topic, keywords in _get_topic_keywords().items():
        for keyword in keywords:
            if keyword in message_lower:
                found_topics.append(topic)
                break

    return found_topics if found_topics else ['other']
