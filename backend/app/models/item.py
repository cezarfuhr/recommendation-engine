"""Item model"""

from sqlalchemy import Column, Integer, String, Text, JSON, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Item(Base, TimestampMixin):
    """Item table for storing items to be recommended"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), index=True)
    tags = Column(JSON, default=list)  # List of tags for content-based filtering
    features = Column(JSON, default=dict)  # Item features for content-based filtering
    popularity_score = Column(Float, default=0.0)  # Overall popularity

    # Relationships
    interactions = relationship("Interaction", back_populates="item", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(id={self.id}, title='{self.title}')>"
