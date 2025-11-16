"""Interaction schemas"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InteractionBase(BaseModel):
    """Base interaction schema"""

    user_id: int
    item_id: int
    interaction_type: str = Field(..., min_length=1, max_length=50)
    rating: Optional[float] = Field(None, ge=0, le=5)
    weight: float = Field(default=1.0, ge=0, le=10)


class InteractionCreate(InteractionBase):
    """Schema for creating an interaction"""

    pass


class InteractionResponse(InteractionBase):
    """Schema for interaction response"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
