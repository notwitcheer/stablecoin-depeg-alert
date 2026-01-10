"""
Configuration Management
Centralized, type-safe configuration with validation
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""

    bot_token: str
    alert_channel_id: str
    premium_channel_id: Optional[str] = None

    def __post_init__(self):
        if not self.bot_token:
            raise ValueError("bot_token is required")
        if not self.alert_channel_id:
            raise ValueError("alert_channel_id is required")


@dataclass
class AlertConfig:
    """Alert system configuration"""

    free_threshold_percent: float = 0.5
    premium_threshold_percent: float = 0.2
    warning_threshold_percent: float = 0.2
    critical_threshold_percent: float = 2.0
    free_cooldown_minutes: int = 30
    premium_cooldown_minutes: int = 5


@dataclass
class APIConfig:
    """External API configuration"""

    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    rate_limit_per_minute: int = 50
    timeout_seconds: int = 30
    check_interval_seconds: int = 60


@dataclass
class DatabaseConfig:
    """Database configuration"""

    url: str = "postgresql://postgres:password@localhost:5432/depeg_alert"
    pool_size: int = 20
    max_overflow: int = 30
    pool_pre_ping: bool = True
    echo_sql: bool = False


@dataclass
class SecurityConfig:
    """Security configuration"""

    max_requests_per_minute: int = 10
    rate_limit_window_seconds: int = 60
    max_message_length: int = 4096
    log_user_requests: bool = True
    validate_inputs: bool = True


@dataclass
class AppConfig:
    """Complete application configuration"""

    environment: Environment
    telegram: TelegramConfig
    alerts: AlertConfig = field(default_factory=AlertConfig)
    api: APIConfig = field(default_factory=APIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables"""
        # Determine environment
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            logger.warning(f"Invalid environment '{env_str}', using development")
            environment = Environment.DEVELOPMENT

        # Telegram configuration
        telegram = TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            alert_channel_id=os.getenv("ALERT_CHANNEL_ID", ""),
            premium_channel_id=os.getenv("PREMIUM_CHANNEL_ID"),
        )

        # Alert configuration
        alerts = AlertConfig(
            free_threshold_percent=float(os.getenv("FREE_THRESHOLD_PERCENT", "0.5")),
            premium_threshold_percent=float(
                os.getenv("PREMIUM_THRESHOLD_PERCENT", "0.2")
            ),
            warning_threshold_percent=float(
                os.getenv("WARNING_THRESHOLD_PERCENT", "0.2")
            ),
            critical_threshold_percent=float(
                os.getenv("CRITICAL_THRESHOLD_PERCENT", "2.0")
            ),
            free_cooldown_minutes=int(os.getenv("FREE_COOLDOWN_MINUTES", "30")),
            premium_cooldown_minutes=int(os.getenv("PREMIUM_COOLDOWN_MINUTES", "5")),
        )

        # API configuration
        api = APIConfig(
            coingecko_base_url=os.getenv(
                "COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3"
            ),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "50")),
            timeout_seconds=int(os.getenv("API_TIMEOUT_SECONDS", "30")),
            check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "60")),
        )

        # Database configuration
        database = DatabaseConfig(
            url=os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:password@localhost:5432/depeg_alert",
            ),
            pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "30")),
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            echo_sql=os.getenv("DB_ECHO_SQL", "false").lower() == "true",
        )

        # Security configuration
        security = SecurityConfig(
            max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10")),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "4096")),
            log_user_requests=os.getenv("LOG_USER_REQUESTS", "true").lower() == "true",
            validate_inputs=os.getenv("VALIDATE_INPUTS", "true").lower() == "true",
        )

        # Debug mode
        debug = os.getenv("DEBUG", "false").lower() == "true"

        return cls(
            environment=environment,
            telegram=telegram,
            alerts=alerts,
            api=api,
            database=database,
            security=security,
            debug=debug,
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate Telegram configuration
        try:
            self.telegram.__post_init__()
        except ValueError as e:
            errors.append(f"Telegram config: {e}")

        # Validate bot token format
        if self.telegram.bot_token and ":" not in self.telegram.bot_token:
            errors.append("Invalid bot token format")

        # Validate thresholds
        if self.alerts.free_threshold_percent <= 0:
            errors.append("free_threshold_percent must be positive")

        if self.alerts.premium_threshold_percent >= self.alerts.free_threshold_percent:
            errors.append(
                "premium_threshold_percent should be less than free_threshold_percent"
            )

        # Production-specific validations
        if self.environment == Environment.PRODUCTION:
            if "password@localhost" in self.database.url:
                errors.append("Default database credentials detected in production")

            if self.debug:
                errors.append("Debug mode should not be enabled in production")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for serialization)"""
        return {
            "environment": self.environment.value,
            "telegram": {
                "bot_token": "***" if self.telegram.bot_token else "",
                "alert_channel_id": self.telegram.alert_channel_id,
                "premium_channel_id": self.telegram.premium_channel_id,
            },
            "alerts": {
                "free_threshold_percent": self.alerts.free_threshold_percent,
                "premium_threshold_percent": self.alerts.premium_threshold_percent,
                "warning_threshold_percent": self.alerts.warning_threshold_percent,
                "critical_threshold_percent": self.alerts.critical_threshold_percent,
                "free_cooldown_minutes": self.alerts.free_cooldown_minutes,
                "premium_cooldown_minutes": self.alerts.premium_cooldown_minutes,
            },
            "api": {
                "coingecko_base_url": self.api.coingecko_base_url,
                "rate_limit_per_minute": self.api.rate_limit_per_minute,
                "timeout_seconds": self.api.timeout_seconds,
                "check_interval_seconds": self.api.check_interval_seconds,
            },
            "database": {
                "url": "***" if self.database.url else "",
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
                "pool_pre_ping": self.database.pool_pre_ping,
                "echo_sql": self.database.echo_sql,
            },
            "security": {
                "max_requests_per_minute": self.security.max_requests_per_minute,
                "rate_limit_window_seconds": self.security.rate_limit_window_seconds,
                "max_message_length": self.security.max_message_length,
                "log_user_requests": self.security.log_user_requests,
                "validate_inputs": self.security.validate_inputs,
            },
            "debug": self.debug,
        }


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()

        # Validate configuration
        errors = _config.validate()
        if errors:
            logger.error("Configuration validation errors:")
            for error in errors:
                logger.error(f"  - {error}")

            # Only raise in production
            if _config.environment == Environment.PRODUCTION:
                raise ValueError(f"Configuration validation failed: {errors}")
            else:
                logger.warning(
                    "Configuration has errors but continuing in development mode"
                )

    return _config


def reload_config() -> AppConfig:
    """Reload configuration from environment"""
    global _config
    _config = None
    return get_config()


# Backward compatibility functions
def validate_config() -> None:
    """Validate configuration (legacy function)"""
    config = get_config()
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration validation failed: {errors}")
    logger.info("✅ Configuration validated successfully")


def get_env_example() -> str:
    """Get example environment variables"""
    return """# Environment
ENVIRONMENT=development

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALERT_CHANNEL_ID=-1001234567890
PREMIUM_CHANNEL_ID=-1009876543210

# Alert Configuration
FREE_THRESHOLD_PERCENT=0.5
PREMIUM_THRESHOLD_PERCENT=0.2
FREE_COOLDOWN_MINUTES=30
PREMIUM_COOLDOWN_MINUTES=5

# API Configuration
CHECK_INTERVAL_SECONDS=60
API_TIMEOUT_SECONDS=30

# Database Configuration
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Security Configuration
MAX_REQUESTS_PER_MINUTE=10
RATE_LIMIT_WINDOW_SECONDS=60

# Debugging
DEBUG=false
LOG_LEVEL=INFO
"""
