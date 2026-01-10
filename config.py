"""
Configuration and Constants for DepegAlert Bot
"""

import os
from typing import Optional

# Telegram Configuration
BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
ALERT_CHANNEL_ID: Optional[str] = os.getenv("ALERT_CHANNEL_ID")  # @DepegAlerts
PREMIUM_CHANNEL_ID: Optional[str] = os.getenv(
    "PREMIUM_CHANNEL_ID"
)  # Private premium channel

# Alert Thresholds (percentage)
FREE_THRESHOLD_PERCENT = 0.5  # Free tier alerts at 0.5% deviation
PREMIUM_THRESHOLD_PERCENT = 0.2  # Premium alerts at 0.2% deviation
WARNING_THRESHOLD_PERCENT = 0.2  # Warning status at 0.2%
CRITICAL_THRESHOLD_PERCENT = 2.0  # Critical status at 2.0%

# Cooldown Periods (minutes)
FREE_COOLDOWN = 30  # 30 minute cooldown for free channel
PREMIUM_COOLDOWN = 5  # 5 minute cooldown for premium channel

# Price Check Configuration
CHECK_INTERVAL = 60  # Check prices every 60 seconds
API_TIMEOUT = 30  # API request timeout in seconds

# CoinGecko API Configuration
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
RATE_LIMIT_PER_MINUTE = 50  # Free tier limit

# Stablecoin Tracking Configuration
DEFAULT_PEG_PRICE = 1.0  # Target price for USD stablecoins

# Web Dashboard Configuration (optional)
WEB_URL: Optional[str] = os.getenv("WEB_URL", "https://stablepeg.xyz")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# Validation
def validate_config():
    """Validate required configuration"""
    if not BOT_TOKEN or BOT_TOKEN.strip() == "":
        raise ValueError(
            "TELEGRAM_BOT_TOKEN environment variable is required and cannot be empty"
        )

    if not ALERT_CHANNEL_ID or ALERT_CHANNEL_ID.strip() == "":
        raise ValueError(
            "ALERT_CHANNEL_ID environment variable is required and cannot be empty"
        )

    # Validate bot token format (basic check)
    if not BOT_TOKEN.count(":") >= 1:
        raise ValueError("TELEGRAM_BOT_TOKEN appears to have invalid format")

    # Validate channel ID format (should be numeric or start with @)
    if not (
        ALERT_CHANNEL_ID.startswith("-")
        or ALERT_CHANNEL_ID.startswith("@")
        or ALERT_CHANNEL_ID.isdigit()
    ):
        raise ValueError(
            "ALERT_CHANNEL_ID should be a channel ID (-100...) or username (@channel)"
        )

    print("✅ Configuration validated successfully")


def get_env_example():
    """Get example environment variables for .env file"""
    return """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALERT_CHANNEL_ID=-1001234567890
PREMIUM_CHANNEL_ID=-1009876543210

# Optional Configuration
WEB_URL=https://stablepeg.xyz
LOG_LEVEL=INFO
"""


if __name__ == "__main__":
    # Test configuration when run directly
    try:
        validate_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n📄 Create a .env file with these variables:")
        print(get_env_example())
