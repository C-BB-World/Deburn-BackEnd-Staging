"""
Static knowledge store for the AI agent.

Contains topic keywords and fallback actions.
Designed to be augmented/replaced by RAG in future.
"""

from typing import Dict, List, Any


class Knowledge:
    """
    Static knowledge store for the agent.
    Contains topic keywords and fallback actions.
    """

    # 15 coaching topics with detection keywords
    topic_keywords: Dict[str, List[str]] = {
        "delegation": [
            "delegate", "delegating", "assign", "trust", "let go", "hand off"
        ],
        "stress": [
            "stress", "stressful", "overwhelmed", "pressure", "anxious", "anxiety"
        ],
        "team_dynamics": [
            "team", "group", "collaborate", "dynamics", "working together", "teamwork"
        ],
        "communication": [
            "communicate", "conversation", "feedback", "listen", "speak", "talk"
        ],
        "leadership": [
            "leader", "leadership", "lead", "manage", "guide", "vision"
        ],
        "time_management": [
            "time", "prioritize", "schedule", "busy", "deadline", "urgent"
        ],
        "conflict": [
            "conflict", "disagreement", "tension", "difficult conversation", "argue"
        ],
        "burnout": [
            "burnout", "exhausted", "tired", "depleted", "drained", "worn out"
        ],
        "motivation": [
            "motivation", "motivated", "purpose", "drive", "engagement", "inspire"
        ],
        "decision_making": [
            "decision", "decide", "choice", "uncertain", "options"
        ],
        "mindfulness": [
            "mindful", "present", "aware", "focus", "meditation", "breath"
        ],
        "resilience": [
            "resilience", "resilient", "bounce back", "recover", "adapt", "cope"
        ],
        "psychological_safety": [
            "safe", "safety", "speak up", "fear", "trust", "vulnerable"
        ],
        "emotional_regulation": [
            "emotion", "feeling", "regulate", "calm", "react", "anger"
        ],
        "feedback": [
            "feedback", "critique", "review", "performance", "evaluation"
        ],
    }

    # Fallback actions per topic/language
    # Structure: topic -> language -> list of action dicts
    fallback_actions: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "stress": {
            "en": [
                {
                    "type": "exercise",
                    "id": "breathing-calm",
                    "label": "Try a Calming Exercise",
                    "metadata": {
                        "duration": "3 min",
                        "contentType": "audio_exercise",
                        "category": "breathing"
                    }
                },
                {
                    "type": "learning",
                    "id": "stress-management",
                    "label": "Learn: Stress Management",
                    "metadata": {
                        "duration": "5 min",
                        "contentType": "audio_article",
                        "category": "wellbeing"
                    }
                },
            ],
            "sv": [
                {
                    "type": "exercise",
                    "id": "breathing-calm",
                    "label": "Prova en lugnande övning",
                    "metadata": {
                        "duration": "3 min",
                        "contentType": "audio_exercise",
                        "category": "breathing"
                    }
                },
                {
                    "type": "learning",
                    "id": "stress-management",
                    "label": "Lär dig: Stresshantering",
                    "metadata": {
                        "duration": "5 min",
                        "contentType": "audio_article",
                        "category": "wellbeing"
                    }
                },
            ],
        },
        "burnout": {
            "en": [
                {
                    "type": "exercise",
                    "id": "breathing-reset",
                    "label": "Try a Reset Breathing Exercise",
                    "metadata": {
                        "duration": "5 min",
                        "contentType": "audio_exercise",
                        "category": "breathing"
                    }
                },
                {
                    "type": "learning",
                    "id": "burnout-prevention",
                    "label": "Learn: Preventing Burnout",
                    "metadata": {
                        "duration": "7 min",
                        "contentType": "audio_article",
                        "category": "wellbeing"
                    }
                },
            ],
            "sv": [
                {
                    "type": "exercise",
                    "id": "breathing-reset",
                    "label": "Prova en återhämtningsövning",
                    "metadata": {
                        "duration": "5 min",
                        "contentType": "audio_exercise",
                        "category": "breathing"
                    }
                },
                {
                    "type": "learning",
                    "id": "burnout-prevention",
                    "label": "Lär dig: Förebygg utbrändhet",
                    "metadata": {
                        "duration": "7 min",
                        "contentType": "audio_article",
                        "category": "wellbeing"
                    }
                },
            ],
        },
        "delegation": {
            "en": [
                {
                    "type": "learning",
                    "id": "delegation-basics",
                    "label": "Learn: Effective Delegation",
                    "metadata": {
                        "duration": "6 min",
                        "contentType": "audio_article",
                        "category": "leadership"
                    }
                },
            ],
            "sv": [
                {
                    "type": "learning",
                    "id": "delegation-basics",
                    "label": "Lär dig: Effektiv delegering",
                    "metadata": {
                        "duration": "6 min",
                        "contentType": "audio_article",
                        "category": "leadership"
                    }
                },
            ],
        },
        "conflict": {
            "en": [
                {
                    "type": "learning",
                    "id": "conflict-resolution",
                    "label": "Learn: Conflict Resolution",
                    "metadata": {
                        "duration": "8 min",
                        "contentType": "audio_article",
                        "category": "communication"
                    }
                },
            ],
            "sv": [
                {
                    "type": "learning",
                    "id": "conflict-resolution",
                    "label": "Lär dig: Konflikthantering",
                    "metadata": {
                        "duration": "8 min",
                        "contentType": "audio_article",
                        "category": "communication"
                    }
                },
            ],
        },
        "mindfulness": {
            "en": [
                {
                    "type": "exercise",
                    "id": "mindfulness-basic",
                    "label": "Try a Mindfulness Exercise",
                    "metadata": {
                        "duration": "5 min",
                        "contentType": "audio_exercise",
                        "category": "mindfulness"
                    }
                },
            ],
            "sv": [
                {
                    "type": "exercise",
                    "id": "mindfulness-basic",
                    "label": "Prova en mindfulnessövning",
                    "metadata": {
                        "duration": "5 min",
                        "contentType": "audio_exercise",
                        "category": "mindfulness"
                    }
                },
            ],
        },
        "leadership": {
            "en": [
                {
                    "type": "learning",
                    "id": "leadership-foundations",
                    "label": "Learn: Leadership Foundations",
                    "metadata": {
                        "duration": "10 min",
                        "contentType": "audio_article",
                        "category": "leadership"
                    }
                },
            ],
            "sv": [
                {
                    "type": "learning",
                    "id": "leadership-foundations",
                    "label": "Lär dig: Ledarskapets grunder",
                    "metadata": {
                        "duration": "10 min",
                        "contentType": "audio_article",
                        "category": "leadership"
                    }
                },
            ],
        },
        "communication": {
            "en": [
                {
                    "type": "learning",
                    "id": "communication-skills",
                    "label": "Learn: Communication Skills",
                    "metadata": {
                        "duration": "7 min",
                        "contentType": "audio_article",
                        "category": "communication"
                    }
                },
            ],
            "sv": [
                {
                    "type": "learning",
                    "id": "communication-skills",
                    "label": "Lär dig: Kommunikationsfärdigheter",
                    "metadata": {
                        "duration": "7 min",
                        "contentType": "audio_article",
                        "category": "communication"
                    }
                },
            ],
        },
        "emotional_regulation": {
            "en": [
                {
                    "type": "exercise",
                    "id": "grounding-exercise",
                    "label": "Try a Grounding Exercise",
                    "metadata": {
                        "duration": "4 min",
                        "contentType": "audio_exercise",
                        "category": "emotional"
                    }
                },
            ],
            "sv": [
                {
                    "type": "exercise",
                    "id": "grounding-exercise",
                    "label": "Prova en jordningsövning",
                    "metadata": {
                        "duration": "4 min",
                        "contentType": "audio_exercise",
                        "category": "emotional"
                    }
                },
            ],
        },
    }

    def get_topic_keywords(self) -> Dict[str, List[str]]:
        """Get all topic keywords."""
        return self.topic_keywords

    def get_topics(self) -> List[str]:
        """Get list of all topic names."""
        return list(self.topic_keywords.keys())

    def get_fallback_actions(
        self,
        topic: str,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get fallback actions for a topic.

        Args:
            topic: Topic name
            language: Language code ('en' or 'sv')

        Returns:
            List of action dicts
        """
        topic_actions = self.fallback_actions.get(topic, {})
        return topic_actions.get(language, topic_actions.get("en", []))

    def get_all_fallback_actions(
        self,
        language: str = "en"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all fallback actions for a language.

        Args:
            language: Language code

        Returns:
            Dict of topic -> actions
        """
        result = {}
        for topic in self.fallback_actions:
            result[topic] = self.get_fallback_actions(topic, language)
        return result


# Singleton instance
_knowledge_instance: Knowledge | None = None


def get_knowledge() -> Knowledge:
    """Get singleton Knowledge instance."""
    global _knowledge_instance
    if _knowledge_instance is None:
        _knowledge_instance = Knowledge()
    return _knowledge_instance
