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

    # 12 coaching topics with detection keywords
    # Stem-friendly prefixes (e.g. "delegat") catch conjugations via substring match.
    topic_keywords: Dict[str, List[str]] = {
        "delegation": [
            "delegate", "delegating", "delegation", "assign", "let go",
            "hand off", "empower", "micromanag", "ownership", "responsibilit",
            "distribute work", "give task", "pass on",
            # sv
            "delegera", "delegering", "tilldela", "ansvar", "släppa taget",
        ],
        "stress": [
            "stress", "stressful", "overwhelmed", "pressure", "anxious", "anxiety",
            "swamped", "stretched thin", "can't keep up", "workload", "tense",
            "on edge", "under pressure", "nervous", "worry",
            # from emotional_regulation (dropped topic)
            "emotion", "feeling", "react", "anger", "angry", "frustrat",
            "irritat", "snapped", "lost my temper",
            # sv
            "stressad", "pressad", "orolig", "ångest", "spänd", "överväldigad",
            "känsla", "ilska", "arg", "reagera",
        ],
        "team_dynamics": [
            "team", "group", "collaborate", "dynamics", "working together", "teamwork",
            "cowork", "colleague", "morale", "cohesion", "silos",
            "team spirit", "cooperation", "interpersonal",
            # from psychological_safety (dropped topic)
            "trust", "safe", "safety", "vulnerable", "speak up", "psychological",
            "inclusion", "belong",
            # sv
            "lag", "samarbete", "kollega", "gruppdynamik", "laganda", "medarbetare",
            "trygg", "trygghet", "tillit", "inkludering",
        ],
        "communication": [
            "communicate", "conversation", "listen", "speak", "talk",
            "misunderstand", "unclear", "message", "one-on-one", "meeting",
            "dialogue", "articulate", "express",
            # from feedback (dropped topic)
            "feedback", "critique", "criticism", "appraisal", "recognition",
            "difficult conversation",
            # sv
            "kommunikation", "samtala", "lyssna", "prata", "budskap", "möte",
            "återkoppling", "kritik",
        ],
        "leadership": [
            "leader", "leadership", "lead", "manage", "guide", "vision",
            "strateg", "influence", "accountab", "responsib",
            "role model", "direction", "executive",
            # sv
            "ledare", "ledarskap", "leda", "styra", "ansvarig", "strategi",
        ],
        "time_management": [
            "time", "prioritize", "schedule", "busy", "deadline", "urgent",
            "priorit", "productiv", "efficien", "procrastinat", "overcommit",
            "too much on my plate", "calendar", "workload", "backlog",
            # sv
            "tid", "prioritera", "schema", "upptagen", "deadline", "brådskande",
            "produktiv", "prokrastiner",
        ],
        "conflict": [
            "conflict", "disagreement", "tension", "difficult conversation", "argue",
            "frustrat", "hostile", "passive aggressive", "clash", "confrontat",
            "dispute", "friction",
            # sv
            "konflikt", "oenighet", "spänning", "bråk", "tvist", "konfrontation",
        ],
        "burnout": [
            "burnout", "exhausted", "tired", "depleted", "drained", "worn out",
            "empty", "numb", "going through the motions", "nothing left",
            "running on fumes", "fatigue", "burnt out",
            # sv
            "utbränd", "utmattad", "trött", "slut", "tömd", "orkeslös",
        ],
        "motivation": [
            "motivation", "motivated", "purpose", "drive", "engagement", "inspire",
            "meaningless", "uninspired", "apathetic", "passion", "fulfill",
            "lack of energy", "unmotivated", "disengaged",
            # sv
            "motivation", "engagemang", "drivkraft", "inspirera", "meningslös",
            "omotiverad",
        ],
        "decision_making": [
            "decision", "decide", "choice", "uncertain", "options",
            "stuck", "paralyz", "trade-off", "weighing", "dilemma",
            "indecisive", "crossroads",
            # sv
            "beslut", "bestämma", "val", "osäker", "alternativ", "vägval",
        ],
        "mindfulness": [
            "mindful", "present", "aware", "focus", "meditation", "breath",
            "grounding", "centering", "overwhelm", "slow down", "pause",
            "attention", "calm",
            # from emotional_regulation (dropped topic)
            "regulate", "self-regulat", "composure",
            # sv
            "medveten", "närvaro", "fokus", "meditation", "andning", "lugn",
            "reglera",
        ],
        "resilience": [
            "resilience", "resilient", "bounce back", "recover", "adapt", "cope",
            "setback", "failure", "struggle", "persever", "tough time",
            "adversity", "overcome",
            # sv
            "motståndskraft", "återhämta", "anpassa", "hantera", "motgång",
            "klara av",
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
