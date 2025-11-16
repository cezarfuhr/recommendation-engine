"""Pytest configuration and fixtures"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine"""
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables):
    """Create a new database session for a test"""

    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
