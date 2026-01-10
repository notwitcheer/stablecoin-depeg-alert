"""
DepegAlert Bot - Main Entry Point
Telegram bot for monitoring stablecoin pegs in real-time
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import NoReturn

from telegram.ext import Application

from bot.handlers import setup_handlers
from bot.scheduler import start_scheduler
from config import BOT_TOKEN
from core.sentry_config import init_sentry


# Configure structured logging
def setup_logging() -> None:
    """Setup structured logging configuration"""
    import os

    # Configure logging level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.addHandler(console_handler)

    # Set specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce HTTP noise
    logging.getLogger("telegram").setLevel(logging.WARNING)  # Reduce Telegram noise


setup_logging()

logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialize and run the bot."""
    logger.info("Starting DepegAlert Bot...")

    try:
        # Validate configuration before starting
        from config import validate_config

        validate_config()

        # Initialize error tracking
        sentry_enabled = init_sentry()
        if sentry_enabled:
            logger.info("✅ Sentry error tracking enabled")
        else:
            logger.info("ℹ️ Sentry error tracking disabled (no SENTRY_DSN configured)")

        # Validate required token exists
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN is required but not set")
            raise ValueError("BOT_TOKEN environment variable is required")

        # Create application
        application = Application.builder().token(BOT_TOKEN).build()

        # Setup command handlers
        setup_handlers(application)

        # Start price checking scheduler
        start_scheduler()

        # Start the bot
        logger.info("Bot is online and monitoring stablecoins 24/7...")
        await application.run_polling()

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
