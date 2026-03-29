"""
Email service configuration constants.

These are fixed values that don't change per environment.
Environment-specific values (API keys, URLs) are loaded from env vars.
"""

# Resend API endpoints
RESEND_API_URL = "https://api.resend.com/emails"
RESEND_BATCH_API_URL = "https://api.resend.com/emails/batch"

# Batch limits
EMAIL_MAX_BATCH_SIZE = 50

# Default values (can be overridden by env vars)
EMAIL_DEFAULTS = {
    "mode": "console",
    "from_name": "Human First AI",
    "team_name": "The Human First AI Team",
}
