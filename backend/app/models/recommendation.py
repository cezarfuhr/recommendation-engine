"""Recommendation model"""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Recommendation(Base, TimestampMixin):
    """Stored recommendations for users"""

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    algorithm = Column(String(50), nullable=False)  # collaborative, content_based, hybrid
    rank = Column(Integer)  # Position in recommendation list

    # Relationships
    user = relationship("User", back_populates="recommendations")
    item = relationship("Item", back_populates="recommendations")

    # Composite index for faster queries
    __table_args__ = (
        Index('ix_user_algorithm_rank', 'user_id', 'algorithm', 'rank'),
    )

    def __repr__(self):
        return f"<Recommendation(user_id={self.user_id}, item_id={self.item_id}, algorithm='{self.algorithm}')>"
