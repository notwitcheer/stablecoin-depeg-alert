"""
Sentry Error Tracking Configuration
Handles Sentry SDK initialization and error tracking setup
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """
    Initialize Sentry error tracking

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn or sentry_dsn.strip() == "":
        logger.info("SENTRY_DSN not configured, skipping Sentry initialization")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.aiohttp import AioHttpIntegration
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Environment configuration
        environment = os.getenv("SENTRY_ENVIRONMENT", "development")

        # Release information
        release = os.getenv("SENTRY_RELEASE")
        if not release:
            try:
                # Try to get git commit hash as release
                import subprocess

                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    release = f"depeg-alert@{result.stdout.strip()}"
            except:
                release = "depeg-alert@unknown"

        # Configure logging integration
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors and above as events
        )

        # Initialize Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            release=release,
            integrations=[
                logging_integration,
                AsyncioIntegration(),
                AioHttpIntegration(),
            ],
            # Performance monitoring
            traces_sample_rate=0.1,  # 10% of transactions
            # Error filtering
            before_send=filter_sensitive_data,
            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personally identifiable information
            max_breadcrumbs=50,
        )

        # Test Sentry connection
        sentry_sdk.capture_message("Sentry initialized successfully", level="info")

        logger.info(
            f"✅ Sentry initialized - Environment: {environment}, Release: {release}"
        )
        return True

    except ImportError:
        logger.error("sentry-sdk not installed, cannot initialize Sentry")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def filter_sensitive_data(event, hint):
    """
    Filter sensitive data from Sentry events before sending

    Args:
        event: Sentry event data
        hint: Additional context

    Returns:
        Modified event or None to drop the event
    """
    try:
        # Remove sensitive environment variables
        if "extra" in event and "sys.argv" in event["extra"]:
            del event["extra"]["sys.argv"]

        # Filter out sensitive data from exception values
        if "exception" in event:
            for exception in event["exception"]["values"]:
                if "value" in exception and exception["value"]:
                    # Remove bot tokens, API keys, etc.
                    value = exception["value"]
                    value = _sanitize_sensitive_strings(value)
                    exception["value"] = value

        # Filter breadcrumbs
        if "breadcrumbs" in event:
            for breadcrumb in event["breadcrumbs"]:
                if "message" in breadcrumb:
                    breadcrumb["message"] = _sanitize_sensitive_strings(
                        breadcrumb["message"]
                    )
                if "data" in breadcrumb:
                    breadcrumb["data"] = _sanitize_dict(breadcrumb["data"])

        # Filter request data
        if "request" in event:
            if "headers" in event["request"]:
                # Remove authorization headers
                event["request"]["headers"] = {
                    k: v
                    for k, v in event["request"]["headers"].items()
                    if k.lower() not in ["authorization", "x-api-key", "x-auth-token"]
                }

        return event

    except Exception as e:
        logger.warning(f"Error filtering Sentry event: {e}")
        return event


def _sanitize_sensitive_strings(text: str) -> str:
    """Sanitize sensitive information from strings"""
    if not isinstance(text, str):
        return text

    import re

    # Remove bot tokens
    text = re.sub(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b", "[BOT_TOKEN]", text)

    # Remove API keys
    text = re.sub(r"\b[A-Za-z0-9]{32,}\b", "[API_KEY]", text)

    # Remove potential database URLs
    text = re.sub(
        r"postgresql://[^@]+@[^/]+/\w+", "postgresql://[CREDENTIALS]@[HOST]/[DB]", text
    )

    # Remove potential channel IDs
    text = re.sub(r"-100\d{10}", "[CHANNEL_ID]", text)

    return text


def _sanitize_dict(data: dict) -> dict:
    """Recursively sanitize sensitive information from dictionaries"""
    if not isinstance(data, dict):
        return data

    sanitized = {}
    sensitive_keys = [
        "token",
        "password",
        "secret",
        "key",
        "api_key",
        "bot_token",
        "dsn",
        "credentials",
        "auth",
        "authorization",
    ]

    for key, value in data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, str):
            sanitized[key] = _sanitize_sensitive_strings(value)
        else:
            sanitized[key] = value

    return sanitized


def capture_exception(error: Exception, context: Optional[dict] = None) -> str:
    """
    Capture an exception with additional context

    Args:
        error: The exception to capture
        context: Additional context information

    Returns:
        Event ID from Sentry
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)

            return sentry_sdk.capture_exception(error)

    except ImportError:
        logger.debug("sentry-sdk not available, cannot capture exception")
        return ""
    except Exception as e:
        logger.warning(f"Failed to capture exception to Sentry: {e}")
        return ""


def capture_message(
    message: str, level: str = "info", context: Optional[dict] = None
) -> str:
    """
    Capture a message with additional context

    Args:
        message: The message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context information

    Returns:
        Event ID from Sentry
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)

            return sentry_sdk.capture_message(message, level)

    except ImportError:
        logger.debug("sentry-sdk not available, cannot capture message")
        return ""
    except Exception as e:
        logger.warning(f"Failed to capture message to Sentry: {e}")
        return ""


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[dict] = None,
):
    """
    Add a breadcrumb for debugging

    Args:
        message: Breadcrumb message
        category: Category of the breadcrumb
        level: Level of the breadcrumb
        data: Additional data
    """
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message, category=category, level=level, data=data or {}
        )

    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to add Sentry breadcrumb: {e}")


def set_user_context(user_id: str, username: str = None, tier: str = None):
    """
    Set user context for error tracking

    Args:
        user_id: User's Telegram ID
        username: User's username (optional)
        tier: User's subscription tier (optional)
    """
    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            scope.user = {"id": user_id, "username": username, "tier": tier}

    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to set Sentry user context: {e}")
