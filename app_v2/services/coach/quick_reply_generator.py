"""
Quick reply suggestion generator.

Generates contextual quick reply suggestions for coaching conversations.
"""

from typing import List, Dict


class QuickReplyGenerator:
    """
    Generates quick reply suggestions based on conversation context.
    """

    TOPIC_REPLIES = {
        "en": {
            "delegation": [
                "I don't trust they'll do it right",
                "How do I let go of control?"
            ],
            "stress": [
                "My workload is too high",
                "I can't say no to requests"
            ],
            "burnout": [
                "I'm feeling exhausted",
                "I've lost my motivation"
            ],
            "time_management": [
                "I never have enough time",
                "I'm always in meetings"
            ],
            "conflict": [
                "There's tension in my team",
                "How do I have difficult conversations?"
            ],
            "communication": [
                "My team doesn't listen",
                "I struggle with feedback"
            ],
            "leadership": [
                "I want to be a better leader",
                "I'm new to management"
            ],
        },
        "sv": {
            "delegation": [
                "Jag litar inte på att de gör det rätt",
                "Hur släpper jag kontrollen?"
            ],
            "stress": [
                "Min arbetsbörda är för hög",
                "Jag kan inte säga nej"
            ],
            "burnout": [
                "Jag känner mig utmattad",
                "Jag har tappat motivationen"
            ],
        }
    }

    DEFAULT_REPLIES = {
        "en": [
            "Tell me more",
            "What should I try?"
        ],
        "sv": [
            "Berätta mer",
            "Vad ska jag prova?"
        ]
    }

    def generate(
        self,
        response_text: str,
        topics: List[str],
        language: str = "en"
    ) -> List[str]:
        """
        Generate quick reply suggestions.

        Args:
            response_text: Coach's response
            topics: Detected topics
            language: 'en' or 'sv'

        Returns:
            List of 2 quick reply strings
        """
        replies = []
        topic_replies = self.TOPIC_REPLIES.get(language, self.TOPIC_REPLIES["en"])

        for topic in topics:
            if topic in topic_replies and len(replies) < 2:
                topic_specific = topic_replies[topic]
                for reply in topic_specific:
                    if reply not in replies and len(replies) < 2:
                        replies.append(reply)

        if len(replies) < 2:
            default = self.DEFAULT_REPLIES.get(language, self.DEFAULT_REPLIES["en"])
            for reply in default:
                if reply not in replies and len(replies) < 2:
                    replies.append(reply)

        return replies[:2]
