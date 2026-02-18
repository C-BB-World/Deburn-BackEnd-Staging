"""
Pydantic models for Admin request/response validation.

Matches the API documentation in docs/v2/architecture/api/admin.md
"""

from pydantic import BaseModel


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class AdminStats(BaseModel):
    """Admin statistics."""
    totalUsers: int
    activeUsers: int
    totalCheckins: int
    totalSessions: int
