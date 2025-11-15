"""Interaction model"""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Interaction(Base, TimestampMixin):
    """User-Item interaction table"""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # view, click, purchase, rating, etc.
    rating = Column(Float)  # Optional rating value
    weight = Column(Float, default=1.0)  # Weight of interaction for scoring

    # Relationships
    user = relationship("User", back_populates="interactions")
    item = relationship("Item", back_populates="interactions")

    # Composite index for faster queries
    __table_args__ = (
        Index('ix_user_item', 'user_id', 'item_id'),
        Index('ix_interaction_type', 'interaction_type'),
    )

    def __repr__(self):
        return f"<Interaction(user_id={self.user_id}, item_id={self.item_id}, type='{self.interaction_type}')>"
