"""
Telegram Bot Command Handlers
Handles all bot commands like /start, /status, /check, etc.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_msg = """
🔔 Welcome to DepegAlert Bot!

I monitor stablecoin pegs 24/7 and alert you when something goes wrong.

📊 Commands:
/status - Check all stablecoin pegs now
/check USDC - Check specific stablecoin
/subscribe - Get alerts in our channel
/help - Show all commands

🆓 Free alerts: Major depegs (>0.5%)
💎 Premium: Early warnings, more coins, custom alerts

Stay safe out there! 🛡️
    """
    await update.message.reply_text(welcome_msg)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show all stablecoin pegs"""
    await update.message.reply_text("🔍 Checking all stablecoin pegs...")

    try:
        from core.peg_checker import check_all_pegs
        from bot.alerts import format_status_message

        # Check all pegs
        pegs = await check_all_pegs()

        if not pegs:
            await update.message.reply_text("❌ Unable to fetch price data. Please try again later.")
            return

        # Format and send status message
        message = format_status_message(pegs)
        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text("❌ Error checking stablecoin pegs. Please try again later.")
        logger.error(f"Status command error: {e}")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check [SYMBOL] command - check specific stablecoin"""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /check USDC\n\nAvailable: USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD")
        return

    symbol = args[0].upper()
    await update.message.reply_text(f"🔍 Checking {symbol}...")

    try:
        from core.peg_checker import check_specific_peg
        from core.models import PegStatus

        # Check specific stablecoin
        peg = await check_specific_peg(symbol)

        # Status emoji
        status_emoji = {
            PegStatus.STABLE: "✅",
            PegStatus.WARNING: "⚠️",
            PegStatus.DEPEG: "🔴",
            PegStatus.CRITICAL: "🚨"
        }

        emoji = status_emoji[peg.status]
        message = f"{emoji} {peg.symbol}: ${peg.price:.4f} ({peg.deviation_percent:+.2f}%)"
        message += f"\n📊 Status: {peg.status.value.title()}"
        message += f"\n🕐 {peg.last_updated.strftime('%H:%M UTC')}"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ Error checking {symbol}. Please verify the symbol and try again.")
        logger.error(f"Check command error for {symbol}: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🔔 DepegAlert Bot Commands:

/status - Check all stablecoin pegs
/check SYMBOL - Check specific stablecoin (e.g. /check USDC)
/subscribe - Join our alert channel
/help - Show this help message

🚨 We monitor these stablecoins:
• USDT, USDC, DAI, USDS (Tier 1)
• FRAX, TUSD, USDP, PYUSD (Tier 2)
• And more in premium...

🔗 Dashboard: stablepeg.xyz (coming soon)
    """
    await update.message.reply_text(help_text)

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command"""
    subscribe_msg = """
📢 Get instant depeg alerts!

🆓 Free Channel: @DepegAlerts
• Major depegs (>0.5% deviation)
• Tier 1 + Tier 2 stablecoins
• 30min cooldown between alerts

💎 Premium Channel: Coming Soon!
• Early warnings (>0.2% deviation)
• All stablecoins tracked
• Real-time, no cooldown
• Custom thresholds

Join now: @DepegAlerts
    """
    await update.message.reply_text(subscribe_msg)

def setup_handlers(application):
    """Setup all command handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))

    logger.info("All command handlers registered")