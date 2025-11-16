"""Recommendation schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlgorithmType(str, Enum):
    """Recommendation algorithm types"""

    COLLABORATIVE = "collaborative"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"


class RecommendationRequest(BaseModel):
    """Schema for requesting recommendations"""

    user_id: int
    top_n: int = Field(default=10, ge=1, le=100)
    algorithm: Optional[AlgorithmType] = AlgorithmType.HYBRID
    exclude_interacted: bool = True


class RecommendationItemResponse(BaseModel):
    """Schema for a single recommended item"""

    item_id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    score: float
    rank: int

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    """Schema for recommendation response"""

    user_id: int
    algorithm: str
    recommendations: List[RecommendationItemResponse]
    generated_at: datetime

    class Config:
        from_attributes = True
