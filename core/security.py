"""
Security Configuration and Utilities
Centralized security settings and validation functions
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Security configuration
SECURITY_CONFIG = {
    "max_message_length": 4096,
    "max_symbol_length": 10,
    "rate_limit_window": 60,  # seconds
    "max_requests_per_window": 10,
    "log_user_requests": True,
    "sanitize_error_messages": True,
    "validate_input_formats": True,
}

# User rate limiting
user_request_counts: Dict[int, list] = {}


def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited"""
    if not SECURITY_CONFIG["rate_limit_window"]:
        return False

    now = datetime.utcnow()
    window_start = now - timedelta(seconds=SECURITY_CONFIG["rate_limit_window"])

    # Clean old requests
    if user_id in user_request_counts:
        user_request_counts[user_id] = [
            req_time
            for req_time in user_request_counts[user_id]
            if req_time > window_start
        ]
    else:
        user_request_counts[user_id] = []

    # Check if over limit
    request_count = len(user_request_counts[user_id])
    if request_count >= SECURITY_CONFIG["max_requests_per_window"]:
        logger.warning(f"User {user_id} rate limited ({request_count} requests)")
        return True

    # Add current request
    user_request_counts[user_id].append(now)
    return False


def validate_stablecoin_symbol(symbol: str) -> bool:
    """Validate stablecoin symbol format"""
    if not symbol or not isinstance(symbol, str):
        return False

    # Security: Only allow alphanumeric characters
    if not re.match(r"^[A-Z]+$", symbol):
        return False

    # Check length
    if len(symbol) > SECURITY_CONFIG["max_symbol_length"]:
        return False

    return True


def validate_telegram_bot_token(token: Optional[str]) -> bool:
    """Validate Telegram bot token format"""
    if not token:
        return False

    # Basic format check: number:alphanumeric_string
    pattern = r"^\d+:[A-Za-z0-9_-]{35}$"
    return bool(re.match(pattern, token))


def validate_channel_id(channel_id: Optional[str]) -> bool:
    """Validate Telegram channel ID format"""
    if not channel_id:
        return False

    # Channel ID can be numeric (with optional -), or @username
    if channel_id.startswith("@"):
        # Username format: @username (alphanumeric + underscores)
        pattern = r"^@[A-Za-z0-9_]+$"
        return bool(re.match(pattern, channel_id))
    else:
        # Numeric channel ID (can be negative)
        try:
            int(channel_id)
            return True
        except ValueError:
            return False


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error message for logging"""
    if not SECURITY_CONFIG["sanitize_error_messages"]:
        return str(error)

    # Only return error type, not detailed message that might contain sensitive info
    return f"{type(error).__name__}"


def sanitize_log_data(data: Any) -> Any:
    """Sanitize data before logging"""
    if isinstance(data, str):
        # Truncate long strings
        if len(data) > 100:
            return data[:97] + "..."
        return data
    elif isinstance(data, dict):
        # Remove sensitive keys
        sensitive_keys = {"token", "password", "key", "secret", "credential"}
        return {k: "***" if k.lower() in sensitive_keys else v for k, v in data.items()}
    return data


def validate_environment_variables() -> Dict[str, bool]:
    """Validate all security-relevant environment variables"""
    results = {}

    # Check bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    results["bot_token"] = validate_telegram_bot_token(bot_token)

    # Check channel ID
    channel_id = os.getenv("ALERT_CHANNEL_ID")
    results["channel_id"] = validate_channel_id(channel_id)

    # Check database URL doesn't use default credentials in production
    db_url = os.getenv("DATABASE_URL", "")
    results["db_security"] = not (
        "password@localhost" in db_url
        and os.getenv("ENVIRONMENT", "development") == "production"
    )

    return results


def get_security_recommendations() -> list:
    """Get security recommendations based on current configuration"""
    recommendations = []

    validation_results = validate_environment_variables()

    if not validation_results.get("bot_token"):
        recommendations.append("Set a valid TELEGRAM_BOT_TOKEN")

    if not validation_results.get("channel_id"):
        recommendations.append("Set a valid ALERT_CHANNEL_ID")

    if not validation_results.get("db_security"):
        recommendations.append("Use secure database credentials for production")

    # Check if using HTTPS for webhooks (if applicable)
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url and not webhook_url.startswith("https://"):
        recommendations.append("Use HTTPS for webhook URLs")

    # Check if proper logging level is set
    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level == "DEBUG" and os.getenv("ENVIRONMENT") == "production":
        recommendations.append("Don't use DEBUG logging in production")

    return recommendations


# Security monitoring
class SecurityMonitor:
    """Monitor security events and metrics"""

    def __init__(self):
        self.events = []
        self.metrics = {
            "rate_limit_violations": 0,
            "invalid_inputs": 0,
            "api_errors": 0,
            "start_time": datetime.utcnow(),
        }

    def log_security_event(self, event_type: str, user_id: int, details: str = ""):
        """Log a security-related event"""
        event = {
            "type": event_type,
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.utcnow(),
        }
        self.events.append(event)

        # Keep only last 100 events to prevent memory issues
        if len(self.events) > 100:
            self.events = self.events[-100:]

        logger.warning(f"Security event: {event_type} from user {user_id}")

    def increment_metric(self, metric: str):
        """Increment a security metric"""
        if metric in self.metrics:
            self.metrics[metric] += 1

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary"""
        uptime = datetime.utcnow() - self.metrics["start_time"]

        return {
            "uptime_hours": uptime.total_seconds() / 3600,
            "metrics": self.metrics.copy(),
            "recent_events": len(self.events),
            "recommendations": get_security_recommendations(),
        }


# Global security monitor instance
security_monitor = SecurityMonitor()
