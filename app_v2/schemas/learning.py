"""
Pydantic models for Learning system request/response validation.

Matches the API documentation in docs/v2/architecture/api/learning.md
"""

from typing import Optional
from pydantic import BaseModel


# =============================================================================
# Response Schemas (used inside success_response data)
# =============================================================================

class LearningModule(BaseModel):
    """Learning module in responses."""
    id: str
    title: str
    description: str
    type: str  # "video" | "audio" | "article" | "exercise"
    duration: int  # Duration in minutes
    thumbnail: Optional[str] = None
    progress: int  # Progress percentage (0-100)
