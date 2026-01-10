"""
Pytest configuration and shared fixtures
"""

import asyncio
import os
import tempfile
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token:test"
os.environ["ALERT_CHANNEL_ID"] = "-1001234567890"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
        yield db_url

    # Cleanup
    try:
        os.unlink(tmp.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_database(temp_db):
    """Create test database with tables"""
    from core.database import Base, create_database_engine

    # Create engine for test database
    os.environ["DATABASE_URL"] = temp_db
    engine = create_database_engine()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_database):
    """Create a database session for testing"""
    from core.database import SessionLocal

    SessionLocal.configure(bind=test_database)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_coingecko_api():
    """Mock CoinGecko API responses"""
    mock_responses = {
        "tether": {"usd": 0.999},
        "usd-coin": {"usd": 1.001},
        "dai": {"usd": 0.998},
        "usds": {"usd": 1.000},
        "frax": {"usd": 1.002},
        "true-usd": {"usd": 0.997},
        "paxos-standard": {"usd": 1.001},
        "paypal-usd": {"usd": 1.000},
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_responses
        mock_response.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )
        yield mock_responses


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot for testing"""
    with patch("telegram.Bot") as mock_bot:
        mock_instance = AsyncMock()
        mock_instance.send_message.return_value = AsyncMock()
        mock_bot.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_stablecoin_data():
    """Sample stablecoin test data"""
    return {
        "stable": {
            "symbol": "USDC",
            "name": "USD Coin",
            "coingecko_id": "usd-coin",
            "price": 1.001,
            "deviation": 0.1,
            "status": "stable",
        },
        "warning": {
            "symbol": "DAI",
            "name": "Dai",
            "coingecko_id": "dai",
            "price": 0.997,
            "deviation": -0.3,
            "status": "warning",
        },
        "depeg": {
            "symbol": "USDT",
            "name": "Tether",
            "coingecko_id": "tether",
            "price": 0.994,
            "deviation": -0.6,
            "status": "depeg",
        },
    }


@pytest.fixture
def mock_user_data():
    """Sample user test data"""
    return {
        "free_user": {
            "telegram_id": "123456789",
            "username": "testuser",
            "first_name": "Test",
            "tier": "free",
        },
        "premium_user": {
            "telegram_id": "987654321",
            "username": "premiumuser",
            "first_name": "Premium",
            "tier": "premium",
        },
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch("redis.Redis") as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def isolated_test_env():
    """Ensure tests run in isolated environment"""
    # Save original env vars
    original_env = dict(os.environ)

    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite:///test.db",
        "LOG_LEVEL": "WARNING",
        "TELEGRAM_BOT_TOKEN": "test_token:test",
        "ALERT_CHANNEL_ID": "-1001234567890",
    }

    os.environ.update(test_env)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Simple performance timer for testing"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()
            return self.elapsed

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# Test data generators
@pytest.fixture
def price_data_generator():
    """Generate price data for testing"""

    def _generate(symbol: str, base_price: float = 1.0, deviation_percent: float = 0.0):
        price = base_price * (1 + deviation_percent / 100)
        return {
            "symbol": symbol,
            "price": price,
            "deviation_percent": deviation_percent,
            "timestamp": "2024-01-01T00:00:00Z",
        }

    return _generate


# Async testing helpers
@pytest.fixture
async def async_mock_session():
    """Mock async database session"""
    with patch("core.database.get_db_session") as mock_session:
        mock_ctx = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_ctx
        yield mock_ctx
