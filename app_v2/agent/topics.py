"""
Topic extraction for coaching conversations.

Extracts coaching topics from messages using keyword matching.
"""

from typing import List


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


TOPIC_KEYWORDS = {
    'delegation': ['delegate', 'delegating', 'assign', 'trust', 'let go', 'hand off'],
    'stress': ['stress', 'stressful', 'overwhelmed', 'pressure', 'anxious', 'anxiety'],
    'team_dynamics': ['team', 'group', 'collaborate', 'dynamics', 'working together', 'teamwork'],
    'communication': ['communicate', 'conversation', 'feedback', 'listen', 'speak', 'talk'],
    'leadership': ['leader', 'leadership', 'lead', 'manage', 'guide', 'vision'],
    'time_management': ['time', 'prioritize', 'schedule', 'busy', 'deadline', 'urgent'],
    'conflict': ['conflict', 'disagreement', 'tension', 'difficult conversation', 'argue'],
    'burnout': ['burnout', 'exhausted', 'tired', 'depleted', 'drained', 'worn out'],
    'motivation': ['motivation', 'motivated', 'purpose', 'drive', 'engagement', 'inspire'],
    'decision_making': ['decision', 'decide', 'choice', 'uncertain', 'options'],
    'mindfulness': ['mindful', 'present', 'aware', 'focus', 'meditation', 'breath'],
    'resilience': ['resilience', 'resilient', 'bounce back', 'recover', 'adapt', 'cope'],
    'psychological_safety': ['safe', 'safety', 'speak up', 'fear', 'trust', 'vulnerable'],
    'emotional_regulation': ['emotion', 'feeling', 'regulate', 'calm', 'react', 'anger'],
    'feedback': ['feedback', 'critique', 'review', 'performance', 'evaluation'],
}


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

    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                found_topics.append(topic)
                break

    return found_topics if found_topics else ['other']
