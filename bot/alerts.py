"""
Alert System for Stablecoin Depeg Notifications
Handles alert formatting and sending to Telegram channels
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from telegram import Bot

from config import FREE_COOLDOWN
from core.models import PegStatus, StablecoinPeg

logger = logging.getLogger(__name__)

# Track last alert time per coin to avoid spam
last_alerts: Dict[str, datetime] = {}


def format_alert_message(pegs: List[StablecoinPeg], triggered_by: StablecoinPeg) -> str:
    """Format a depeg alert message"""

    # Status emoji mapping
    status_emoji = {
        PegStatus.STABLE: "✅",
        PegStatus.WARNING: "⚠️",
        PegStatus.DEPEG: "🔴",
        PegStatus.CRITICAL: "🚨",
    }

    # Header
    msg = "🚨 DEPEG ALERT\n\n"
    msg += f"{status_emoji[triggered_by.status]} {triggered_by.symbol}: "
    msg += f"${triggered_by.price:.4f} ({triggered_by.deviation_percent:+.2f}%)\n\n"

    # All stablecoins status
    msg += "📊 All Stablecoins:\n"
    for peg in sorted(pegs, key=lambda x: abs(x.deviation_percent), reverse=True):
        emoji = status_emoji[peg.status]
        msg += (
            f"{emoji} {peg.symbol}: ${peg.price:.4f} ({peg.deviation_percent:+.2f}%)\n"
        )

    # Footer
    msg += f"\n🕐 {datetime.utcnow().strftime('%H:%M UTC')}\n"
    msg += "🔗 stablepeg.xyz"

    return msg


def format_status_message(pegs: List[StablecoinPeg], user_tier: str = "free") -> str:
    """Format a status check message customized for user tier"""
    status_emoji = {
        PegStatus.STABLE: "✅",
        PegStatus.WARNING: "⚠️",
        PegStatus.DEPEG: "🔴",
        PegStatus.CRITICAL: "🚨",
    }

    # Overall status
    has_issues = any(p.status != PegStatus.STABLE for p in pegs)
    header = "🔴 Issues Detected" if has_issues else "🟢 All Stablecoins Stable"

    # Add tier indicator to header
    tier_emoji = {"free": "🆓", "premium": "💎", "enterprise": "🏢"}
    header += f" {tier_emoji.get(user_tier, '🆓')}"

    msg = f"{header}\n\n"

    # List all stablecoins
    for peg in sorted(pegs, key=lambda x: abs(x.deviation_percent), reverse=True):
        emoji = status_emoji[peg.status]
        msg += (
            f"{emoji} {peg.symbol}: ${peg.price:.4f} ({peg.deviation_percent:+.2f}%)\n"
        )

    msg += f"\n🕐 Updated: {datetime.utcnow().strftime('%H:%M UTC')}"

    return msg


def is_on_cooldown(symbol: str) -> bool:
    """Check if a stablecoin is still on alert cooldown"""
    if symbol not in last_alerts:
        return False

    cooldown_time = last_alerts[symbol] + timedelta(minutes=FREE_COOLDOWN)
    return datetime.utcnow() < cooldown_time


def update_cooldown(symbol: str):
    """Update the last alert time for a stablecoin"""
    last_alerts[symbol] = datetime.utcnow()
    logger.info(f"Alert cooldown updated for {symbol}")


async def send_to_channel(bot: Bot, channel_id: str, message: str):
    """Send message to Telegram channel"""
    try:
        # Security: Validate message length to prevent abuse
        if len(message) > 4096:  # Telegram message limit
            logger.warning("Alert message too long, truncating")
            message = message[:4090] + "..."

        # Security: Basic sanitization (though Telegram handles most)
        if message.strip() == "":
            logger.warning("Attempted to send empty alert message")
            return

        await bot.send_message(chat_id=channel_id, text=message)
        logger.info(
            f"Alert sent to channel {channel_id[:10]}..."
        )  # Don't log full channel ID
    except Exception as e:
        logger.error(
            f"Failed to send alert to channel: {type(e).__name__}"
        )  # Don't expose channel ID or full error
