"""Item schemas"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class ItemBase(BaseModel):
    """Base item schema"""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = []
    features: Optional[Dict] = {}


class ItemCreate(ItemBase):
    """Schema for creating an item"""

    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item"""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    features: Optional[Dict] = None


class ItemResponse(ItemBase):
    """Schema for item response"""

    id: int
    popularity_score: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
