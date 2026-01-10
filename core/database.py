"""
Database Configuration and Connection Management
PostgreSQL with SQLAlchemy ORM for production scalability
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import (
    DatabaseError,
    DisconnectionError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

logger = logging.getLogger(__name__)

# Database configuration
DEFAULT_DB_URL = "postgresql://postgres:password@localhost:5432/depeg_alert"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def validate_database_url(url: str) -> bool:
    """Validate database URL format and security"""
    try:
        parsed = urlparse(url)

        # Check if it's a supported database
        if parsed.scheme not in ["postgresql", "postgresql+psycopg2", "sqlite"]:
            logger.error(f"Unsupported database scheme: {parsed.scheme}")
            return False

        # Security warnings
        if url == DEFAULT_DB_URL:
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env == "production":
                logger.error("Default database credentials detected in production!")
                return False
            else:
                logger.warning("Using default database credentials in development")

        # Check for insecure configurations
        if (
            "password" in url
            and "@localhost" in url
            and os.getenv("ENVIRONMENT") == "production"
        ):
            logger.warning("Potentially insecure database configuration in production")

        return True
    except Exception as e:
        logger.error(f"Invalid database URL format: {e}")
        return False


def create_database_engine() -> Engine:
    """Create and configure database engine with proper error handling"""
    if not validate_database_url(DATABASE_URL):
        raise ValueError(f"Invalid or insecure database configuration")

    # Parse URL to determine database type
    parsed = urlparse(DATABASE_URL)
    is_sqlite = parsed.scheme.startswith("sqlite")

    # Configure engine parameters based on database type
    if is_sqlite:
        # SQLite configuration (for development/testing)
        engine_kwargs = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False, "timeout": 30},
        }
    else:
        # PostgreSQL configuration (production)
        engine_kwargs = {
            "poolclass": QueuePool,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "30")),
            "pool_pre_ping": True,  # Verify connections before use
            "pool_recycle": 3600,  # Recreate connections every hour
            "connect_args": {
                "connect_timeout": 10,
                "server_settings": {"timezone": "UTC"},
            },
        }

    # Common configuration
    engine_kwargs.update(
        {
            "echo": os.getenv("SQL_DEBUG", "false").lower() == "true",
            "future": True,  # Use SQLAlchemy 2.0 style
        }
    )

    try:
        engine = create_engine(DATABASE_URL, **engine_kwargs)
        logger.info(
            f"Database engine created for {parsed.scheme}://{parsed.hostname}:{parsed.port}"
        )
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


# Create engine instance
engine = create_database_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DatabaseManager:
    """Manages database connections and operations with enhanced error handling"""

    @staticmethod
    def get_session() -> Session:
        """Get a database session with connection validation"""
        try:
            session = SessionLocal()
            # Test the connection immediately
            session.execute(text("SELECT 1"))
            return session
        except (OperationalError, DisconnectionError) as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Failed to establish database session: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}")
            raise

    @staticmethod
    def create_tables() -> bool:
        """Create all database tables with proper error handling"""
        try:
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return True
        except OperationalError as e:
            logger.error(f"Database operational error while creating tables: {e}")
            raise
        except DatabaseError as e:
            logger.error(f"Database error while creating tables: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating tables: {e}")
            raise

    @staticmethod
    def drop_tables() -> bool:
        """Drop all database tables (development only)"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            logger.error("Cannot drop tables in production environment!")
            return False

        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(bind=engine)
            logger.info("Database tables dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    @staticmethod
    def test_connection(timeout: int = 5) -> bool:
        """Test database connectivity with timeout and detailed error reporting"""
        start_time = time.time()

        try:
            with engine.connect() as connection:
                # Test basic connectivity
                result = connection.execute(text("SELECT 1 as test"))
                test_value = result.fetchone()

                if test_value and test_value[0] == 1:
                    response_time = round((time.time() - start_time) * 1000, 2)
                    logger.info(
                        f"Database connection test successful ({response_time}ms)"
                    )
                    return True
                else:
                    logger.error("Database connection test failed - unexpected result")
                    return False

        except OperationalError as e:
            logger.error(f"Database operational error: {e}")
            return False
        except TimeoutError as e:
            logger.error(f"Database connection timeout: {e}")
            return False
        except DisconnectionError as e:
            logger.error(f"Database disconnection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Database connection test failed with unexpected error: {e}")
            return False

    @staticmethod
    def get_connection_info() -> dict:
        """Get information about database connection and pool status"""
        try:
            pool = engine.pool

            # Sanitize URL for logging (hide password)
            sanitized_url = str(engine.url)
            if engine.url.password:
                sanitized_url = sanitized_url.replace(str(engine.url.password), "***")

            info = {
                "url": sanitized_url,
                "dialect": engine.dialect.name,
                "driver": engine.dialect.driver,
                "pool_size": getattr(pool, "size", lambda: "N/A")(),
                "checked_in": getattr(pool, "checkedin", lambda: "N/A")(),
                "checked_out": getattr(pool, "checkedout", lambda: "N/A")(),
                "overflow": getattr(pool, "overflow", lambda: "N/A")(),
            }

            return info
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {"error": str(e)}

    @staticmethod
    def health_check() -> dict:
        """Comprehensive database health check"""
        health_info = {
            "healthy": False,
            "connection_test": False,
            "response_time_ms": None,
            "connection_info": {},
            "error": None,
        }

        try:
            start_time = time.time()

            # Test connection
            health_info["connection_test"] = DatabaseManager.test_connection()
            health_info["response_time_ms"] = round(
                (time.time() - start_time) * 1000, 2
            )

            # Get connection info
            health_info["connection_info"] = DatabaseManager.get_connection_info()

            # Overall health
            health_info["healthy"] = health_info["connection_test"]

        except Exception as e:
            health_info["error"] = str(e)
            logger.error(f"Database health check failed: {e}")

        return health_info


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup and retry logic

    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
            session.add(new_record)
            # Automatic commit on success, rollback on error
    """
    session: Optional[Session] = None
    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            session = DatabaseManager.get_session()
            yield session
            session.commit()
            break  # Success, exit retry loop

        except (OperationalError, DisconnectionError) as e:
            if session:
                session.rollback()
                session.close()

            retry_count += 1
            if retry_count >= max_retries:
                logger.error(
                    f"Database session failed after {max_retries} retries: {e}"
                )
                raise DatabaseError(f"Database session failed after retries: {e}")
            else:
                logger.warning(
                    f"Database session retry {retry_count}/{max_retries}: {e}"
                )
                time.sleep(0.5 * retry_count)  # Exponential backoff

        except Exception as e:
            if session:
                session.rollback()
                session.close()
            logger.error(f"Database session error: {e}")
            raise

        finally:
            if session and retry_count >= max_retries:
                session.close()

    # Cleanup for successful case
    if session:
        session.close()


@contextmanager
def get_db_session_readonly() -> Generator[Session, None, None]:
    """Context manager for read-only database sessions (no commit/rollback)"""
    session: Optional[Session] = None
    try:
        session = DatabaseManager.get_session()
        yield session
    except Exception as e:
        logger.error(f"Read-only database session error: {e}")
        raise
    finally:
        if session:
            session.close()


# Database event listeners for connection optimization
@event.listens_for(engine, "connect")
def configure_database_connection(dbapi_connection, connection_record):
    """Configure database connection parameters based on database type"""
    try:
        parsed_url = urlparse(DATABASE_URL)

        if parsed_url.scheme.startswith("postgresql"):
            # PostgreSQL optimizations
            cursor = dbapi_connection.cursor()
            cursor.execute("SET timezone = 'UTC'")
            cursor.execute("SET statement_timeout = '30s'")  # 30-second query timeout
            cursor.execute("SET idle_in_transaction_session_timeout = '60s'")
            cursor.close()
            logger.debug("PostgreSQL connection configured")

        elif parsed_url.scheme.startswith("sqlite"):
            # SQLite optimizations
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
            cursor.execute(
                "PRAGMA journal_mode=WAL"
            )  # Enable WAL mode for better concurrency
            cursor.execute(
                "PRAGMA synchronous=NORMAL"
            )  # Balance between speed and safety
            cursor.close()
            logger.debug("SQLite connection configured")

    except Exception as e:
        logger.warning(f"Failed to configure database connection: {e}")


@event.listens_for(engine, "checkout")
def check_connection_on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Validate connection health on checkout from pool"""
    try:
        # Test the connection with a simple query
        cursor = dbapi_connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
    except Exception as e:
        logger.warning(f"Stale connection detected and will be discarded: {e}")
        # This will cause SQLAlchemy to discard the connection and create a new one
        raise DisconnectionError("Connection validation failed")


@event.listens_for(engine, "invalid")
def handle_connection_invalidated(dbapi_connection, connection_record, exception):
    """Handle invalidated connections"""
    logger.warning(f"Database connection invalidated: {exception}")
    # SQLAlchemy will automatically create a new connection


def init_database(create_tables: bool = True, timeout: int = 30) -> bool:
    """
    Initialize database with comprehensive setup and validation

    Args:
        create_tables: Whether to create database tables
        timeout: Connection timeout in seconds

    Returns:
        bool: True if initialization successful
    """
    try:
        logger.info("Initializing database system...")

        # Step 1: Validate configuration
        if not validate_database_url(DATABASE_URL):
            raise ValueError("Invalid database configuration")

        # Step 2: Test connectivity
        logger.info("Testing database connectivity...")
        if not DatabaseManager.test_connection(timeout):
            raise ConnectionError("Database connection test failed")

        # Step 3: Get connection info
        conn_info = DatabaseManager.get_connection_info()
        logger.info(f"Connected to {conn_info.get('dialect', 'unknown')} database")

        # Step 4: Create tables if requested
        if create_tables:
            logger.info("Creating database tables...")
            if not DatabaseManager.create_tables():
                raise RuntimeError("Failed to create database tables")

        # Step 5: Verify table creation with a test query
        if create_tables:
            try:
                with get_db_session_readonly() as session:
                    # Try to query a core table to verify it exists
                    result = session.execute(
                        text(
                            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'users'"
                        )
                    )
                    table_count = result.fetchone()[0]
                    if table_count == 0:
                        logger.warning("Users table not found after creation")
                    else:
                        logger.info("Database tables verified successfully")
            except Exception as e:
                logger.warning(f"Could not verify table creation: {e}")

        # Step 6: Final health check
        health = DatabaseManager.health_check()
        if not health["healthy"]:
            raise RuntimeError(
                f"Database health check failed: {health.get('error', 'Unknown error')}"
            )

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def cleanup_database():
    """Clean up database connections and resources"""
    try:
        logger.info("Cleaning up database connections...")
        engine.dispose()
        logger.info("Database cleanup completed")
    except Exception as e:
        logger.error(f"Database cleanup error: {e}")


# Database utility functions for common operations
def execute_raw_sql(sql: str, params: Optional[dict] = None) -> Any:
    """
    Execute raw SQL with proper error handling

    WARNING: Use with caution - prefer ORM operations when possible
    """
    try:
        with get_db_session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchall()
    except Exception as e:
        logger.error(f"Raw SQL execution failed: {e}")
        raise


def get_database_stats() -> dict:
    """Get database statistics and performance metrics"""
    stats = {
        "connection_info": DatabaseManager.get_connection_info(),
        "health": DatabaseManager.health_check(),
        "total_connections": "N/A",
        "active_connections": "N/A",
    }

    try:
        # Get PostgreSQL-specific stats if available
        parsed_url = urlparse(DATABASE_URL)
        if parsed_url.scheme.startswith("postgresql"):
            with get_db_session_readonly() as session:
                # Get connection count
                result = session.execute(
                    text(
                        """
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database()
                """
                    )
                )
                stats["total_connections"] = result.fetchone()[0]

                # Get active connections
                result = session.execute(
                    text(
                        """
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database() AND state = 'active'
                """
                    )
                )
                stats["active_connections"] = result.fetchone()[0]

    except Exception as e:
        logger.debug(f"Could not get database stats: {e}")

    return stats


# Export commonly used items
__all__ = [
    "engine",
    "Base",
    "SessionLocal",
    "DatabaseManager",
    "get_db_session",
    "get_db_session_readonly",
    "init_database",
    "cleanup_database",
    "validate_database_url",
    "get_database_stats",
]
