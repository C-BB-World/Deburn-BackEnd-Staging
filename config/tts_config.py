"""
Text-to-Speech configuration.

Voice mappings and language-specific defaults for ElevenLabs TTS.
"""

# Voice name -> ElevenLabs Voice ID mappings
VOICE_MAPPINGS = {
    # Custom voices
    "Aria": "fO844Om1VZLpw8IpZj3T",
    "Elin": "4Ct5uMEndw4cJ7q0Jx0l",
    "Leoni Vergara": "pBZVCk298iJlHAcHQwLr",
    "Ana-Rita": "wJqPPQ618aTW29mptyoc",
    "Andromeda": "HoU1B9WLbSprzhhX34v0",
    "LavenderLessons": "cL2JBnZF7ILVaQ86EQMQ",
    # High pitch voices
    "Sarah": "EXAVITQu4vr4xnSDxMaL",
    "Laura": "FGY2WhTYpPnrIDTdsKH5",
    "Alice": "Xb7hH8MSUJpSbSDYk0k2",
    "Matilda": "XrExE9yKIg1WjnnlVkGX",
    "Jessica": "cgSgspJ2msm6clMCkdW9",
    "Lily": "pFZP5JQG7iQjIQuC4Bku",
    # Low pitch voices
    "Roger": "CwhRBWXzGAHq8TQ4Fs17",
    "Charlie": "IKne3meq5aSn9XLyUdCD",
    "George": "JBFqnCBsd6RMkjVDRZzb",
    "Callum": "N2lVS1w4EtoT3dr4eOWO",
    "Liam": "TX3LPaxmHKxFdv7VOQHJ",
    "Daniel": "onwK4e9ZLuTAKqWW03F9",
}

# Language-specific TTS defaults
TTS_DEFAULTS = {
    "en": {
        "voice": "Aria",
        "model": "eleven_multilingual_v2",
    },
    "sv": {
        "voice": "Elin",
        "model": "eleven_flash_v2_5",
    },
}
