"""User schemas"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    preferences: Optional[Dict] = {}


class UserCreate(UserBase):
    """Schema for creating a user"""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    preferences: Optional[Dict] = None


class UserResponse(UserBase):
    """Schema for user response"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
