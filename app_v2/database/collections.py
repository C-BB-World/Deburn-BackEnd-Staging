"""
Deburn collection accessors.

Provides typed collection access for Deburn-specific collections.
Uses the centralized MongoDB singletons from common.database.
"""

from common.database import get_main_database, get_hub_database


# ─────────────────────────────────────────────────────────────────
# Main Database Collections (deburn)
# ─────────────────────────────────────────────────────────────────

def get_users_collection():
    """Get the users collection from main database."""
    return get_main_database().get_collection("users")


def get_userpreferences_collection():
    """Get the userpreferences collection from main database."""
    return get_main_database().get_collection("userpreferences")


def get_checkins_collection():
    """Get the checkins collection from main database."""
    return get_main_database().get_collection("checkins")


def get_circles_collection():
    """Get the circles collection from main database."""
    return get_main_database().get_collection("circles")


# ─────────────────────────────────────────────────────────────────
# Hub Database Collections (deburn-hub)
# ─────────────────────────────────────────────────────────────────

def get_conversations_collection():
    """Get the conversations collection from hub database."""
    return get_hub_database().get_collection("conversations")


def get_aiprompt_collection():
    """Get the aiprompt collection from hub database."""
    return get_hub_database().get_collection("aiprompt")
