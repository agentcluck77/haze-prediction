"""
Database connection utilities.
Provides engine and session management for PostgreSQL.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base


def get_database_url():
    """Get database URL from environment or use default."""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://hazeuser:testpassword@localhost:5432/haze_prediction'
    )


def get_engine():
    """Create and return database engine."""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)
    return engine


def get_session():
    """Create and return database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize database by creating all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
