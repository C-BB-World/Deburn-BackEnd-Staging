"""
Pydantic models for Progress system request/response validation.

Matches the API documentation in docs/v2/architecture/api/progress.md
"""

from typing import List
from pydantic import BaseModel


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class Insight(BaseModel):
    """Individual insight."""
    title: str
    description: str
