"""
Telegram Bot Command Handlers
Handles all bot commands like /start, /status, /check, etc.
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.security import (
    is_rate_limited,
    sanitize_error_message,
    security_monitor,
    validate_stablecoin_symbol,
)
from core.sentry_config import add_breadcrumb, capture_exception, set_user_context
from core.user_manager import UserManager

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    try:
        # Set Sentry user context
        set_user_context(str(user.id), user.username)
        add_breadcrumb("User started bot", "command", "info", {"user_id": user.id})

        # Simplified approach - skip database for now
        user_tier = "free"
        logger.info(f"User {user.id} started bot (simplified mode)")

        # Update Sentry context with tier
        set_user_context(str(user.id), user.username, user_tier)

        welcome_msg = f"""
🔔 Welcome to DepegAlert Bot{', ' + user.first_name if user.first_name else ''}!

I monitor stablecoin pegs 24/7 and alert you when something goes wrong.

📊 Commands:
/status - Check all stablecoin pegs now
/check USDC - Check specific stablecoin
/subscribe - Get alerts in our channel
/help - Show all commands
/account - View your account info

"""

        # Add tier-specific information
        if user_tier == "free":
            welcome_msg += """🆓 Your Plan: FREE
• Major depegs (>0.5% deviation)
• 4 core stablecoins (USDT, USDC, DAI, USDS)
• 30min cooldown between alerts

💎 Upgrade to Premium for:
• Early warnings (>0.2% deviation)
• 39+ stablecoins across ALL chains:
  🔷 Ethereum • Arbitrum • Base • Polygon
  🔷 Optimism • Avalanche • BNB Chain • Gnosis • Berachain
• Cross-chain depeg detection
• Custom alert thresholds
• Real-time alerts, no cooldown
"""
        elif user_tier == "premium":
            welcome_msg += """💎 Your Plan: PREMIUM
• Early warnings (>0.2% deviation)
• 39+ stablecoins across ALL blockchains:
  🔷 Ethereum • Arbitrum • Base • Polygon
  🔷 Optimism • Avalanche • BNB Chain • Gnosis • Berachain
• Cross-chain depeg detection
• Custom alert thresholds
• 5min cooldown between alerts
• Priority support
"""
        elif user_tier == "enterprise":
            welcome_msg += """🏢 Your Plan: ENTERPRISE
• Ultra-fast alerts (>0.1% deviation)
• 39+ stablecoins across ALL blockchains
• Complete cross-chain coverage
• Custom alert thresholds
• 1min cooldown between alerts
• Priority support & custom features
"""

        welcome_msg += "\nStay safe out there! 🛡️"

        await update.message.reply_text(welcome_msg)
        logger.info(f"User {user.id} started bot, tier: {user_tier}")

    except Exception as e:
        # Capture exception to Sentry
        capture_exception(
            e,
            {
                "command": "start",
                "user_id": user.id if user else None,
                "username": user.username if user else None,
            },
        )
        await update.message.reply_text(
            "❌ Error setting up your account. Please try again later."
        )
        logger.error(
            f"Start command error for user {user.id}: {sanitize_error_message(e)}"
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show all stablecoin pegs"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    user_id = str(user.id)

    # Security: Rate limiting
    if is_rate_limited(user.id):
        await update.message.reply_text(
            "⏰ Too many requests. Please wait a moment before trying again."
        )
        security_monitor.log_security_event("rate_limit", user.id)
        security_monitor.increment_metric("rate_limit_violations")
        return

    try:
        # Register or get user in database
        UserManager.register_or_get_user(
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        # Get user info to determine tier access
        user_info = UserManager.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "❌ Error accessing your account. Please try /start first."
            )
            return

        logger.info(f"User {user_id} ({user_info['tier']}) requested status check")
        await update.message.reply_text("🔍 Checking stablecoin pegs for your tier...")

        from bot.alerts import format_status_message
        from core.peg_checker import check_all_pegs

        # Check all pegs
        pegs = await check_all_pegs()

        if not pegs:
            await update.message.reply_text(
                "❌ Unable to fetch price data. Please try again later."
            )
            logger.warning(f"No peg data available for user {user_id} status request")
            security_monitor.increment_metric("api_errors")
            return

        # Filter pegs based on user tier
        enabled_tiers = (
            user_info["preferences"]["enabled_tiers"]
            if user_info["preferences"]
            else [1, 2]
        )
        filtered_pegs = [
            peg for peg in pegs if any(tier in enabled_tiers for tier in [1, 2, 3])
        ]  # TODO: Add tier info to pegs

        # Format and send status message
        message = format_status_message(filtered_pegs, user_info["tier"])

        # Add tier-specific footer
        if user_info["tier"] == "free":
            message += "\n\n💎 Upgrade to Premium to track 39+ stablecoins across ALL blockchains!\n🔷 Ethereum • Arbitrum • Base • Polygon • Optimism • Avalanche • BNB • Gnosis • Berachain"

        await update.message.reply_text(message)
        logger.info(f"Status response sent to user {user_id}")

    except Exception as e:
        # Capture exception to Sentry
        capture_exception(
            e,
            {
                "command": "status",
                "user_id": user_id,
                "username": user.username if user else None,
            },
        )
        await update.message.reply_text(
            "❌ Error checking stablecoin pegs. Please try again later."
        )
        logger.error(
            f"Status command error for user {user_id}: {sanitize_error_message(e)}"
        )
        security_monitor.increment_metric("api_errors")


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check [SYMBOL] command - check specific stablecoin"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    user_id = str(user.id)

    # Security: Rate limiting
    if is_rate_limited(user.id):
        await update.message.reply_text(
            "⏰ Too many requests. Please wait a moment before trying again."
        )
        security_monitor.log_security_event("rate_limit", user.id)
        security_monitor.increment_metric("rate_limit_violations")
        return

    try:
        # Register or get user in database
        UserManager.register_or_get_user(
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /check USDC\n\nAvailable: USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD"
            )
            return

        # Input validation
        symbol = args[0].upper().strip()

        # Security: Validate symbol format
        if not validate_stablecoin_symbol(symbol):
            await update.message.reply_text(
                "❌ Invalid symbol format. Please use valid stablecoin symbols only."
            )
            security_monitor.log_security_event(
                "invalid_input", user.id, f"Invalid symbol: {symbol}"
            )
            security_monitor.increment_metric("invalid_inputs")
            return

        # Get user info for tier validation
        user_info = UserManager.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "❌ Error accessing your account. Please try /start first."
            )
            return

        logger.info(
            f"User {user_id} ({user_info['tier']}) requested check for {symbol}"
        )
        await update.message.reply_text(f"🔍 Checking {symbol}...")

        from core.models import PegStatus
        from core.peg_checker import check_specific_peg

        # Check specific stablecoin
        peg = await check_specific_peg(symbol)

        # Get user's threshold for personalized status
        user_threshold = UserManager.get_user_alert_threshold(user_id)

        # Status emoji
        status_emoji = {
            PegStatus.STABLE: "✅",
            PegStatus.WARNING: "⚠️",
            PegStatus.DEPEG: "🔴",
            PegStatus.CRITICAL: "🚨",
        }

        emoji = status_emoji[peg.status]
        message = (
            f"{emoji} {peg.symbol}: ${peg.price:.4f} ({peg.deviation_percent:+.2f}%)"
        )
        message += f"\n📊 Status: {peg.status.value.title()}"
        message += f"\n🕐 {peg.last_updated.strftime('%H:%M UTC')}"

        # Add personalized alert info
        abs_deviation = abs(peg.deviation_percent)
        if abs_deviation >= user_threshold:
            message += f"\n⚠️ Above your alert threshold ({user_threshold:.1f}%)"
        else:
            message += f"\n✅ Below your alert threshold ({user_threshold:.1f}%)"

        await update.message.reply_text(message)

    except Exception as e:
        # Capture exception to Sentry
        capture_exception(
            e,
            {
                "command": "check",
                "user_id": user_id,
                "username": user.username if user else None,
                "requested_symbol": context.args[0] if context.args else None,
            },
        )
        await update.message.reply_text(
            f"❌ Error checking stablecoin. Please verify the symbol and try again."
        )
        logger.error(
            f"Check command error for user {user_id}: {sanitize_error_message(e)}"
        )
        security_monitor.increment_metric("api_errors")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    user_id = str(user.id) if user else None

    # Get user tier for customized help
    user_tier = "free"
    if user_id:
        try:
            user_info = UserManager.get_user_info(user_id)
            user_tier = user_info["tier"] if user_info else "free"
        except:
            pass

    help_text = """
🔔 DepegAlert Bot Commands:

/status - Check all stablecoin pegs
/check SYMBOL - Check specific stablecoin (e.g. /check USDC)
/account - View your account information
/subscribe - Join our alert channel
/help - Show this help message

"""

    # Add premium commands if user has access
    if user_tier in ["premium", "enterprise"]:
        help_text += """💎 Premium Commands:
/threshold X.X - Set custom alert threshold (e.g. /threshold 0.3)

"""

    help_text += """🚨 We monitor these stablecoins:
• USDT, USDC, DAI, USDS (Tier 1)
• FRAX, TUSD, USDP, PYUSD (Tier 2)"""

    if user_tier != "free":
        help_text += (
            "\n• LUSD, GUSD, USDD, FDUSD, CRVUSD, GHO, DOLA, MIM, sUSD (Tier 3)"
        )

    help_text += "\n\n🔗 Dashboard: stablepeg.xyz (coming soon)"

    await update.message.reply_text(help_text)


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command"""
    subscribe_msg = """
📢 Get instant depeg alerts!

🆓 Free Channel: @DepegAlerts
• Major depegs (>0.5% deviation)
• 4 core stablecoins (USDT, USDC, DAI, USDS)
• 30min cooldown between alerts

💎 Premium Channel: Coming Soon!
• Early warnings (>0.2% deviation)
• 39+ stablecoins across ALL blockchains:
  🔷 Ethereum • Arbitrum • Base • Polygon
  🔷 Optimism • Avalanche • BNB Chain • Gnosis • Berachain
• Cross-chain depeg detection
• Real-time, no cooldown
• Custom thresholds

Join now: @DepegAlerts
    """
    await update.message.reply_text(subscribe_msg)


async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /account command - show user account information"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    user_id = str(user.id)

    try:
        # Register or get user in database
        UserManager.register_or_get_user(
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        user_info = UserManager.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "❌ Error accessing your account. Please try /start first."
            )
            return

        # Get subscription status
        from core.user_manager import SubscriptionManager

        sub_status = SubscriptionManager.get_subscription_status(user_id)

        account_msg = f"""
👤 Account Information

🆔 User ID: {user_info['telegram_id']}
👤 Username: @{user_info['username'] or 'Not set'}
🏷️ Plan: {user_info['tier'].upper()}
📊 Alert Threshold: {UserManager.get_user_alert_threshold(user_id):.1f}%

"""

        if user_info["tier"] != "free":
            if sub_status:
                if sub_status["is_expired"]:
                    account_msg += "❌ Subscription: EXPIRED\n"
                else:
                    account_msg += f"✅ Subscription: {sub_status['days_remaining']} days remaining\n"
                    if sub_status["subscription_end"]:
                        account_msg += f"📅 Expires: {sub_status['subscription_end'].strftime('%Y-%m-%d')}\n"

        account_msg += f"""
🔔 Preferences:
• Enabled coin tiers: {', '.join(map(str, user_info['preferences']['enabled_tiers'])) if user_info['preferences'] else '1, 2'}
• Max alerts/hour: {user_info['preferences']['max_alerts_per_hour'] if user_info['preferences'] else 10}
"""

        if user_info["preferences"] and user_info["preferences"]["custom_threshold"]:
            account_msg += (
                f"• Custom threshold: {user_info['preferences']['custom_threshold']}%\n"
            )

        if user_info["tier"] in ["premium", "enterprise"]:
            account_msg += "\n💎 Premium Commands:\n/threshold X.X - Set custom alert threshold\n/preferences - Manage alert preferences"

        await update.message.reply_text(account_msg)

    except Exception as e:
        # Capture exception to Sentry
        capture_exception(
            e,
            {
                "command": "account",
                "user_id": user_id,
                "username": user.username if user else None,
            },
        )
        await update.message.reply_text(
            "❌ Error accessing account information. Please try again later."
        )
        logger.error(
            f"Account command error for user {user_id}: {sanitize_error_message(e)}"
        )


async def threshold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /threshold command - set custom alert threshold for premium users"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    user_id = str(user.id)

    try:
        # Get user info
        user_info = UserManager.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "❌ Error accessing your account. Please try /start first."
            )
            return

        # Check if user has premium access
        if user_info["tier"] not in ["premium", "enterprise"]:
            await update.message.reply_text(
                "💎 This feature requires a Premium subscription.\n\nUpgrade to get:\n• Custom alert thresholds\n• Early warnings\n• All stablecoins tracked\n\nContact support for upgrade options."
            )
            return

        args = context.args
        if not args:
            current_threshold = UserManager.get_user_alert_threshold(user_id)
            await update.message.reply_text(
                f"Current threshold: {current_threshold:.2f}%\n\nUsage: /threshold 0.3\nRange: 0.01% to 5.0%"
            )
            return

        try:
            threshold = float(args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Please provide a valid number.\nExample: /threshold 0.3"
            )
            return

        # Set threshold
        if UserManager.set_custom_threshold(user_id, threshold):
            await update.message.reply_text(
                f"✅ Alert threshold set to {threshold:.2f}%\n\nYou'll now receive alerts when stablecoins deviate by more than {threshold:.2f}% from $1.00"
            )
            logger.info(f"User {user_id} set custom threshold to {threshold}%")
        else:
            await update.message.reply_text(
                "❌ Invalid threshold. Please use a value between 0.01% and 5.0%"
            )

    except Exception as e:
        # Capture exception to Sentry
        capture_exception(
            e,
            {
                "command": "threshold",
                "user_id": user_id,
                "username": user.username if user else None,
                "requested_threshold": context.args[0] if context.args else None,
            },
        )
        await update.message.reply_text(
            "❌ Error setting threshold. Please try again later."
        )
        logger.error(
            f"Threshold command error for user {user_id}: {sanitize_error_message(e)}"
        )


def setup_handlers(application):
    """Setup all command handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("account", account_command))
    application.add_handler(CommandHandler("threshold", threshold_command))

    logger.info("All command handlers registered")
