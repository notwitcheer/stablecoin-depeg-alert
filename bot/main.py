"""
DepegAlert Bot - Main Entry Point
Telegram bot for monitoring stablecoin pegs in real-time
"""
import asyncio
import logging
from datetime import datetime

from telegram.ext import Application
from bot.handlers import setup_handlers
from bot.scheduler import start_scheduler
from config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Initialize and run the bot."""
    logger.info("Starting DepegAlert Bot...")

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Setup command handlers
    setup_handlers(application)

    # Start price checking scheduler
    start_scheduler()

    # Start the bot
    logger.info("Bot is online and monitoring stablecoins 24/7...")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())