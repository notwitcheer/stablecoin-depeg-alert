"""
Database Configuration and Connection Management
PostgreSQL with SQLAlchemy ORM for production scalability
"""
import os
import logging
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/depeg_alert"
)

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,  # Verify connections before use
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DatabaseManager:
    """Manages database connections and operations"""

    @staticmethod
    def get_session() -> Session:
        """Get a database session"""
        return SessionLocal()

    @staticmethod
    def create_tables():
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    @staticmethod
    def drop_tables():
        """Drop all database tables (development only)"""
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    @staticmethod
    def test_connection() -> bool:
        """Test database connectivity"""
        try:
            with engine.connect() as connection:
                connection.execute("SELECT 1")
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

# Context manager for database sessions
from contextlib import contextmanager

@contextmanager
def get_db_session():
    """Context manager for database sessions with automatic cleanup"""
    session = DatabaseManager.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

# Database event listeners for connection pooling
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database connection parameters"""
    if "postgresql" in DATABASE_URL:
        # PostgreSQL optimizations
        cursor = dbapi_connection.cursor()
        cursor.execute("SET timezone = 'UTC'")
        cursor.close()

def init_database():
    """Initialize database with tables and test connectivity"""
    try:
        logger.info("Initializing database...")

        # Test connection first
        if not DatabaseManager.test_connection():
            raise Exception("Database connection failed")

        # Create tables
        DatabaseManager.create_tables()

        logger.info("Database initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False