"""A/B Testing models"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ABTest(Base, TimestampMixin):
    """A/B Test configuration"""

    __tablename__ = "ab_tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(String(500))
    variant_a_name = Column(String(100), default="control")
    variant_b_name = Column(String(100), default="treatment")
    variant_a_algorithm = Column(String(50), nullable=False)  # e.g., "collaborative"
    variant_b_algorithm = Column(String(50), nullable=False)  # e.g., "hybrid"
    split_ratio = Column(Float, default=0.5)  # Percentage for variant A
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default=dict)  # Additional configuration

    # Relationships
    assignments = relationship("ABTestAssignment", back_populates="ab_test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ABTest(name='{self.name}', active={self.is_active})>"


class ABTestAssignment(Base, TimestampMixin):
    """User assignments to A/B test variants"""

    __tablename__ = "ab_test_assignments"

    id = Column(Integer, primary_key=True, index=True)
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    variant = Column(String(10), nullable=False)  # 'A' or 'B'

    # Relationships
    ab_test = relationship("ABTest", back_populates="assignments")
    user = relationship("User", back_populates="ab_assignments")

    def __repr__(self):
        return f"<ABTestAssignment(test_id={self.ab_test_id}, user_id={self.user_id}, variant='{self.variant}')>"
