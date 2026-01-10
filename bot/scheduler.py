"""
Price Check Scheduler
Runs automated price checks and sends alerts when needed
"""

import asyncio
import logging
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

from bot.alerts import format_alert_message, send_to_channel
from config import ALERT_CHANNEL_ID, BOT_TOKEN, CHECK_INTERVAL, PREMIUM_CHANNEL_ID
from core.db_models import UserTier
from core.models import PegStatus, StablecoinPeg
from core.peg_checker import check_all_pegs
from core.sentry_config import add_breadcrumb, capture_exception
from core.user_manager import UserManager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_and_alert() -> None:
    """
    Main scheduled job - check pegs and send alerts if needed

    This function runs on a schedule to:
    1. Check all stablecoin pegs
    2. Send alerts to different channels based on tier thresholds
    3. Update cooldown timers using database
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
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not configured for alerts")
            return

        bot = Bot(BOT_TOKEN)

        # Check for alerts at different thresholds
        await _check_free_tier_alerts(bot, pegs)
        await _check_premium_tier_alerts(bot, pegs)

        # Log current status
        stable_count = sum(1 for p in pegs if _is_stable(p))
        logger.info(
            f"Peg check complete: {stable_count}/{len(pegs)} stablecoins stable"
        )

    except Exception as e:
        # Capture exception to Sentry with context
        capture_exception(
            e, {"function": "check_and_alert", "context": "scheduled_price_check"}
        )
        logger.error(f"Error in scheduled peg check: {e}")


async def _check_free_tier_alerts(bot: Bot, pegs: List[StablecoinPeg]) -> None:
    """Check and send alerts for free tier (>0.5% threshold)"""
    if not ALERT_CHANNEL_ID:
        logger.warning("Free tier channel not configured")
        return

    try:
        for peg in pegs:
            # Free tier threshold: 0.5%
            if abs(peg.deviation_percent) >= 0.5:
                # Check cooldown for free tier
                if not UserManager.check_alert_cooldown(
                    "system", peg.symbol, ALERT_CHANNEL_ID
                ):
                    # Filter to Tier 1 + 2 stablecoins for free channel
                    tier_1_2_symbols = [
                        "USDT",
                        "USDC",
                        "DAI",
                        "USDS",
                        "FRAX",
                        "TUSD",
                        "USDP",
                        "PYUSD",
                    ]
                    if peg.symbol in tier_1_2_symbols:
                        message = format_alert_message(pegs, triggered_by=peg)
                        await send_to_channel(bot, ALERT_CHANNEL_ID, message)
                        UserManager.update_alert_cooldown(
                            "system", peg.symbol, ALERT_CHANNEL_ID
                        )
                        logger.info(
                            f"Free tier alert sent for {peg.symbol} at ${peg.price:.4f}"
                        )
    except Exception as e:
        capture_exception(
            e,
            {
                "function": "_check_free_tier_alerts",
                "channel_id": ALERT_CHANNEL_ID,
                "context": "free_tier_alerting",
            },
        )
        logger.error(f"Failed to send free tier alerts: {e}")


async def _check_premium_tier_alerts(bot: Bot, pegs: List[StablecoinPeg]) -> None:
    """Check and send alerts for premium tier (>0.2% threshold)"""
    if not PREMIUM_CHANNEL_ID:
        logger.debug("Premium tier channel not configured")
        return

    try:
        for peg in pegs:
            # Premium tier threshold: 0.2%
            if abs(peg.deviation_percent) >= 0.2:
                # Check cooldown for premium tier
                if not UserManager.check_alert_cooldown(
                    "premium", peg.symbol, PREMIUM_CHANNEL_ID
                ):
                    message = format_alert_message(pegs, triggered_by=peg)
                    message += "\n\n💎 Premium Alert - Early Warning"
                    await send_to_channel(bot, PREMIUM_CHANNEL_ID, message)
                    UserManager.update_alert_cooldown(
                        "premium", peg.symbol, PREMIUM_CHANNEL_ID
                    )
                    logger.info(
                        f"Premium tier alert sent for {peg.symbol} at ${peg.price:.4f}"
                    )
    except Exception as e:
        capture_exception(
            e,
            {
                "function": "_check_premium_tier_alerts",
                "channel_id": PREMIUM_CHANNEL_ID,
                "context": "premium_tier_alerting",
            },
        )
        logger.error(f"Failed to send premium tier alerts: {e}")


def _is_stable(peg: StablecoinPeg) -> bool:
    """Helper function to check if a peg is stable"""
    return peg.status == PegStatus.STABLE


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
            replace_existing=True,
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
