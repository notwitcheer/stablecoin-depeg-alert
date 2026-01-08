"""
Price Check Scheduler
Runs automated price checks and sends alerts when needed
"""
import asyncio
import logging
from typing import Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

from core.peg_checker import check_all_pegs
from core.models import StablecoinPeg
from bot.alerts import format_alert_message, send_to_channel, is_on_cooldown, update_cooldown
from config import BOT_TOKEN, ALERT_CHANNEL_ID, CHECK_INTERVAL

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def check_and_alert() -> None:
    """
    Main scheduled job - check pegs and send alerts if needed

    This function runs on a schedule to:
    1. Check all stablecoin pegs
    2. Send alerts for depegs that aren't on cooldown
    3. Update cooldown timers
    4. Log system status
    """
    try:
        logger.info("Checking stablecoin pegs...")

        # Check all peg statuses
        pegs = await check_all_pegs()

        if not pegs:
            logger.warning("No peg data received")
            return

        # Check for alertable depegs
        if not BOT_TOKEN or not ALERT_CHANNEL_ID:
            logger.error("BOT_TOKEN or ALERT_CHANNEL_ID not configured for alerts")
            return

        try:
            bot = Bot(BOT_TOKEN)
            for peg in pegs:
                if peg.is_alertable and not is_on_cooldown(peg.symbol):
                    message = format_alert_message(pegs, triggered_by=peg)
                    await send_to_channel(bot, ALERT_CHANNEL_ID, message)
                    update_cooldown(peg.symbol)
                    logger.info(f"Alert sent for {peg.symbol} at ${peg.price:.4f}")
        except Exception as e:
            logger.error(f"Failed to send alerts: {e}")

        # Log current status
        stable_count = sum(1 for p in pegs if p.is_stable)
        logger.info(f"Peg check complete: {stable_count}/{len(pegs)} stablecoins stable")

    except Exception as e:
        logger.error(f"Error in scheduled peg check: {e}")

def start_scheduler() -> None:
    """
    Initialize and start the price checking scheduler

    Sets up a recurring job that checks stablecoin prices
    every CHECK_INTERVAL seconds and sends alerts as needed.
    """
    try:
        # Add the main price checking job
        scheduler.add_job(
            check_and_alert,
            trigger=IntervalTrigger(seconds=CHECK_INTERVAL),
            id="peg_checker",
            replace_existing=True
        )

        scheduler.start()
        logger.info(f"Scheduler started - checking every {CHECK_INTERVAL} seconds")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

def stop_scheduler() -> None:
    """
    Stop the scheduler gracefully

    This should be called when shutting down the bot
    to ensure clean shutdown of scheduled tasks.
    """
    scheduler.shutdown()
    logger.info("Scheduler stopped")