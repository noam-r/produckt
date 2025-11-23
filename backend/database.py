"""
Database configuration and session management.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from backend.config import settings

logger = logging.getLogger(__name__)


# Create SQLAlchemy engine
# For SQLite, we need check_same_thread=False
# For PostgreSQL, we'll use connection pooling
if settings.database_url.startswith("sqlite"):
    logger.info(f"Configuring SQLite database: {settings.database_url}")
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.environment == "development"
    )
else:
    # PostgreSQL configuration
    logger.info(f"Configuring PostgreSQL database with connection pooling")
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.environment == "development"
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Automatically closes the session when done.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    Used in development and testing.
    In production, use Alembic migrations instead.
    """
    logger.info("Initializing database tables")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
