"""Database connection and session management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from ..config import settings
from ..models.base import Base


# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI

    Yields a database session and ensures it's closed after use.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables

    Creates all tables defined in models.
    """

    # Import all models to ensure they're registered
    from ..models import User, Item, Interaction, Recommendation, ABTest, ABTestAssignment

    Base.metadata.create_all(bind=engine)
