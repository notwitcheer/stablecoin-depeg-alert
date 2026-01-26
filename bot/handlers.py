"""
Telegram Bot Command Handlers
Handles all bot commands like /start, /status, /check, etc.
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from core.security import (
    is_rate_limited,
    sanitize_error_message,
    security_monitor,
    validate_stablecoin_symbol,
)
from core.sentry_config import add_breadcrumb, capture_exception, set_user_context
from core.user_manager import UserManager
from core.ai_predictor import depeg_predictor, sentiment_analyzer
from core.models import SubscriptionTier

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
🤖 Welcome to CryptoGuard AI{', ' + user.first_name if user.first_name else ''}!

I'm an AI-powered stablecoin monitoring system that predicts depeg events before they happen. I monitor 38 stablecoins across 9 blockchains 24/7 with advanced risk assessment.

🧠 **AI Features:**
/risk USDT - Get AI risk assessment
/predict USDC 24h - Depeg predictions
/status - Check all stablecoin pegs

📱 **Get Started:**
/help - See all commands
/subscribe - Join our alert channel
/account - View your account info

🚀 *Powered by Ralph MCP AI Enhancement*
"""

        # Add tier-specific information
        if user_tier == "free":
            welcome_msg += """🆓 Your Plan: FREE
• Major depegs (>0.5% deviation)
• 4 core stablecoins (USDT, USDC, DAI, USDS)
• 30min cooldown between alerts

💎 Upgrade to Premium for:
• Early warnings (>0.2% deviation)
• 34+ additional stablecoins (38 total):
  🔷 Ethereum • Arbitrum • Base • Polygon
  🔷 Optimism • Avalanche • BNB Chain • Gnosis • Berachain
• Cross-chain depeg detection
• Custom alert thresholds
• Real-time alerts, no cooldown
"""
        elif user_tier == "premium":
            welcome_msg += """💎 Your Plan: PREMIUM
• Early warnings (>0.2% deviation)
• 38 stablecoins across ALL blockchains:
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
• 38 stablecoins across ALL blockchains
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
            message += (
                "\n\n💎 Upgrade to Premium to track 38+ stablecoins across "
                "ALL blockchains!\n🔷 Ethereum • Arbitrum • Base • Polygon • "
                "Optimism • Avalanche • BNB • Gnosis • Berachain"
            )

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
                "Usage: /check USDC\n\n"
                "🆓 Free: USDT, USDC, DAI, USDS\n"
                "💎 Premium: 38 stablecoins total (upgrade for full access)"
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
            "❌ Error checking stablecoin. Please verify the symbol and try again."
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
        except Exception:
            pass

    help_text = """
🤖 **CryptoGuard Commands**

**🔍 Monitoring:**
/status - Check all 38 stablecoins now
/check USDC - Check specific stablecoin
/risk USDT - AI risk assessment with ML predictions
/predict DAI - AI-powered depeg probability analysis

**📢 Alerts:**
/subscribe - Join our alert channels
/alerts - Manage your alert preferences

**🤝 Community:**
/contribute - Contribute social sentiment data and earn rewards
/leaderboard - View top community contributors
/rewards - Check your contribution points and badges

**ℹ️ Info:**
/help - Show this help message

**🚀 About CryptoGuard:**
• Real-time monitoring of 38 stablecoins across 9 blockchains
• AI-powered risk predictions using advanced ML models
• Free tier: 4 major stablecoins with >0.5% deviation alerts
• Premium tier: 34+ additional stablecoins (38 total) with >0.2% deviation alerts

**💎 Upgrade to Premium ($15/month):**
• Early warning alerts (0.2% vs 0.5% threshold)
• All 38 stablecoins monitored
• Advanced AI features (cross-chain correlation, predictive scoring)
• Priority support
• Enhanced contribution rewards

**🏢 Enterprise & White-Label:**
• Custom API access for your platform
• White-label licensing available
• Contact us for enterprise pricing

Stay safe in DeFi! 🛡️
    """

    await update.message.reply_text(help_text, parse_mode='Markdown')


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command"""
    subscribe_msg = """
📢 **Get instant depeg alerts!**

🆓 **Free Channel: @DepegAlerts**
• Major depegs (>0.5% deviation)
• 4 core stablecoins (USDT, USDC, DAI, USDS)
• 30min cooldown between alerts

💎 **Premium Channel ($15/month):**
• Early warnings (>0.2% deviation)
• 34+ additional stablecoins (38 total):
  🔷 Ethereum • Arbitrum • Base • Polygon
  🔷 Optimism • Avalanche • BNB Chain • Gnosis • Berachain
• Cross-chain depeg detection
• Real-time alerts, no cooldown
• Advanced AI features (cross-chain correlation, predictive scoring)
• Enhanced community contribution rewards

🏢 **Enterprise & White-Label:**
• Custom API access for exchanges, DeFi protocols
• White-label licensing ($50-500/month)
• Custom integration support

Join now: @DepegAlerts
Contact for Premium/Enterprise: Support coming soon!
    """
    await update.message.reply_text(subscribe_msg, parse_mode='Markdown')


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
                    days_remaining = sub_status["days_remaining"]
                    account_msg += f"✅ Subscription: {days_remaining} days remaining\n"
                    if sub_status["subscription_end"]:
                        expires = sub_status["subscription_end"].strftime("%Y-%m-%d")
                        account_msg += f"📅 Expires: {expires}\n"

        prefs = user_info["preferences"]
        enabled_tiers = ", ".join(map(str, prefs["enabled_tiers"])) if prefs else "1, 2"
        max_alerts = prefs["max_alerts_per_hour"] if prefs else 10

        account_msg += f"""
🔔 Preferences:
• Enabled coin tiers: {enabled_tiers}
• Max alerts/hour: {max_alerts}
"""

        if user_info["preferences"] and user_info["preferences"]["custom_threshold"]:
            account_msg += (
                f"• Custom threshold: {user_info['preferences']['custom_threshold']}%\n"
            )

        if user_info["tier"] in ["premium", "enterprise"]:
            account_msg += (
                "\n💎 Premium Commands:\n/threshold X.X - Set custom alert threshold\n"
                "/preferences - Manage alert preferences"
            )

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
                "💎 This feature requires a Premium subscription.\n\n"
                "Upgrade to get:\n• Custom alert thresholds\n• Early warnings\n"
                "• All stablecoins tracked\n\nContact support for upgrade options."
            )
            return

        args = context.args
        if not args:
            current_threshold = UserManager.get_user_alert_threshold(user_id)
            await update.message.reply_text(
                f"Current threshold: {current_threshold:.2f}%\n\n"
                "Usage: /threshold 0.3\nRange: 0.01% to 5.0%"
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
                f"✅ Alert threshold set to {threshold:.2f}%\n\n"
                f"You'll now receive alerts when stablecoins deviate by more than "
                f"{threshold:.2f}% from $1.00"
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


async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /risk command - show AI risk assessment for a stablecoin"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    user_id = str(user.id)

    # Check rate limiting
    if is_rate_limited(user_id):
        await update.message.reply_text(
            "⏱️ Please wait a moment before using this command again."
        )
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📊 AI Risk Assessment\n\n"
            "Usage: /risk SYMBOL\n"
            "Example: /risk USDT\n\n"
            "Supported coins: USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD"
        )
        return

    symbol = args[0].upper()

    # Validate symbol
    if not validate_stablecoin_symbol(symbol):
        await update.message.reply_text(
            f"❌ Unknown stablecoin: {symbol}\n\n"
            "Supported coins: USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD"
        )
        return

    try:
        # Get current price and historical data
        from core.peg_checker import check_specific_peg
        from core.prices import fetch_historical_prices
        from core.stablecoins import get_stablecoin_by_symbol

        await update.message.reply_text(f"🤖 Analyzing {symbol} with AI models...")

        # Get stablecoin info
        stable_def = get_stablecoin_by_symbol(symbol)
        if not stable_def:
            await update.message.reply_text(f"❌ Could not find data for {symbol}")
            return

        # Get current peg status
        peg_data = await check_specific_peg(symbol)
        if not peg_data:
            await update.message.reply_text(f"❌ Could not fetch current data for {symbol}")
            return

        # Get historical prices for AI analysis
        historical_prices = await fetch_historical_prices(stable_def.coingecko_id, days=7)

        # Get social sentiment
        social_sentiment = await sentiment_analyzer.analyze_stablecoin_sentiment(symbol)

        # Generate AI risk assessment (works with or without historical data)
        risk_assessment = await depeg_predictor.predict_depeg_probability(
            symbol,
            historical_prices=historical_prices,  # May be None/empty due to API limits
            current_volume=float(peg_data.price) * 1000000,  # Simplified volume
            social_sentiment=social_sentiment
        )

        # Format response
        response = f"🤖 **CryptoGuard AI Risk Assessment**\n\n"
        response += f"**{symbol}** ({stable_def.name})\n"
        response += f"💰 Price: ${float(peg_data.price):.4f}\n"
        response += f"📊 Deviation: {peg_data.deviation_percent:+.2f}%\n"
        response += f"🎯 Status: {peg_data.status.value.title()}\n\n"

        if risk_assessment:
            # AI Risk Analysis
            response += f"🧠 **AI Risk Analysis**\n"
            response += f"⚠️ Risk Score: {risk_assessment.risk_score:.1f}/100\n"
            response += f"🎯 Risk Level: {risk_assessment.risk_level.value.title()}\n"
            response += f"🎲 Confidence: {risk_assessment.confidence:.1f}%\n"
            response += f"⏱️ Timeframe: {risk_assessment.prediction_horizon}\n\n"

            # Key factors
            if risk_assessment.contributing_factors:
                response += f"📈 **Key Risk Factors**\n"
                factors = risk_assessment.contributing_factors
                for factor, value in factors.items():
                    if isinstance(value, (int, float)):
                        response += f"• {factor.replace('_', ' ').title()}: {value:.1f}\n"
        else:
            response += f"⚠️ **Limited Analysis** (using basic model)\n"
            response += f"📊 Price-based risk: {abs(peg_data.deviation_percent) * 20:.1f}/100\n\n"

        if social_sentiment:
            response += f"📱 **Social Sentiment**\n"
            response += f"💬 Score: {social_sentiment.sentiment_score:+.1f}/100\n"
            response += f"📢 Mentions: {social_sentiment.mention_count}\n"
            response += f"😨 Fear/Greed: {social_sentiment.fear_greed_index:.0f}/100\n\n"

        response += f"🕐 Analysis time: {peg_data.last_updated.strftime('%H:%M UTC')}\n"
        response += f"🤖 *Powered by CryptoGuard AI*"

        await update.message.reply_text(response)
        logger.info(f"Risk assessment provided for {symbol} to user {user_id}")

    except Exception as e:
        capture_exception(
            e,
            extra={
                "command": "risk",
                "user_id": user_id,
                "symbol": symbol,
            },
        )
        await update.message.reply_text(
            f"❌ Error analyzing {symbol}. Please try again later."
        )
        logger.error(f"Risk command error for {symbol}: {sanitize_error_message(e)}")


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /predict command - show AI depeg predictions"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    user_id = str(user.id)

    # Check rate limiting
    if is_rate_limited(user_id):
        await update.message.reply_text(
            "⏱️ Please wait a moment before using this command again."
        )
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "🔮 AI Depeg Predictions\n\n"
            "Usage: /predict SYMBOL [timeframe]\n"
            "Example: /predict USDT 24h\n\n"
            "Timeframes: 1h, 6h, 24h (default: 24h)\n"
            "Supported coins: USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD"
        )
        return

    symbol = args[0].upper()
    timeframe = args[1] if len(args) > 1 else "24h"

    # Validate inputs
    if not validate_stablecoin_symbol(symbol):
        await update.message.reply_text(
            f"❌ Unknown stablecoin: {symbol}\n\n"
            "Supported coins: USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD"
        )
        return

    if timeframe not in ["1h", "6h", "24h"]:
        await update.message.reply_text(
            f"❌ Invalid timeframe: {timeframe}\n\n"
            "Valid options: 1h, 6h, 24h"
        )
        return

    try:
        from core.prices import fetch_historical_prices
        from core.stablecoins import get_stablecoin_by_symbol

        await update.message.reply_text(f"🔮 Generating {timeframe} prediction for {symbol}...")

        # Get stablecoin info
        stable_def = get_stablecoin_by_symbol(symbol)
        if not stable_def:
            await update.message.reply_text(f"❌ Could not find data for {symbol}")
            return

        # Get historical prices for prediction
        historical_prices = await fetch_historical_prices(stable_def.coingecko_id, days=7)

        # Get social sentiment
        social_sentiment = await sentiment_analyzer.analyze_stablecoin_sentiment(symbol)

        # Generate prediction (works with or without historical data)
        risk_assessment = await depeg_predictor.predict_depeg_probability(
            symbol,
            historical_prices=historical_prices,  # May be None/empty due to API limits
            current_volume=1000000,  # Simplified volume
            social_sentiment=social_sentiment,
            horizon=timeframe
        )

        # Format prediction response
        response = f"🔮 **CryptoGuard AI Prediction**\n\n"
        response += f"**{symbol}** - {timeframe} Forecast\n\n"

        # Risk probability
        depeg_probability = risk_assessment.risk_score / 100.0
        response += f"⚠️ Depeg Probability: {depeg_probability:.1%}\n"
        response += f"🎯 Risk Level: {risk_assessment.risk_level.value.title()}\n"
        response += f"🎲 Model Confidence: {risk_assessment.confidence:.1f}%\n\n"

        # Risk interpretation
        if depeg_probability < 0.1:
            interpretation = "🟢 **Very Low Risk** - Stable conditions expected"
        elif depeg_probability < 0.25:
            interpretation = "🟡 **Low Risk** - Minor volatility possible"
        elif depeg_probability < 0.5:
            interpretation = "🟠 **Medium Risk** - Monitor closely"
        elif depeg_probability < 0.75:
            interpretation = "🔴 **High Risk** - Significant concern"
        else:
            interpretation = "🚨 **Critical Risk** - Immediate attention needed"

        response += f"{interpretation}\n\n"

        # Key factors driving prediction
        if risk_assessment.contributing_factors:
            response += f"📈 **Key Prediction Factors**\n"
            factors = risk_assessment.contributing_factors
            for factor, value in list(factors.items())[:3]:  # Show top 3
                if isinstance(value, (int, float)):
                    response += f"• {factor.replace('_', ' ').title()}: {value:.1f}\n"
            response += "\n"

        if social_sentiment and social_sentiment.sentiment_score != 0:
            response += f"📱 **Social Sentiment Impact**\n"
            if social_sentiment.sentiment_score > 0:
                response += f"🟢 Positive sentiment ({social_sentiment.sentiment_score:+.0f}) supports stability\n"
            else:
                response += f"🔴 Negative sentiment ({social_sentiment.sentiment_score:+.0f}) increases risk\n"
            response += "\n"

        response += f"⏱️ Prediction valid for: {timeframe}\n"
        response += f"🕐 Generated: {risk_assessment.timestamp.strftime('%H:%M UTC')}\n"
        response += f"🤖 *CryptoGuard Predictive AI*\n\n"
        response += f"💡 *This is not financial advice. Use for informational purposes only.*"

        await update.message.reply_text(response)
        logger.info(f"Prediction provided for {symbol} ({timeframe}) to user {user_id}")

    except Exception as e:
        capture_exception(
            e,
            extra={
                "command": "predict",
                "user_id": user_id,
                "symbol": symbol,
                "timeframe": timeframe,
            },
        )
        await update.message.reply_text(
            f"❌ Error generating prediction for {symbol}. Please try again later."
        )
        logger.error(f"Predict command error for {symbol}: {sanitize_error_message(e)}")


async def contribute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /contribute command - community sentiment contribution system"""
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

        contribute_msg = """
🤝 **Community Data Contribution**

Help improve CryptoGuard's AI predictions by contributing market intelligence! Earn points and unlock rewards.

**📱 What You Can Contribute:**
• Social sentiment from Twitter, Reddit, Discord
• Breaking news about stablecoins or protocols
• Unusual trading patterns you've observed
• Regulatory announcements affecting stablecoins

**🎯 How to Contribute:**
1. Reply to this message with your observation
2. Include the stablecoin symbol (e.g., USDT, USDC)
3. Add source links when possible
4. Tag sentiment: POSITIVE, NEGATIVE, or NEUTRAL

**🏆 Reward System:**
• 10 points per verified contribution
• 50 points for first-to-report breaking news
• 100 points bonus for high-quality analysis
• Top contributors get free Premium access!

**📊 Your Stats:**
• Current Points: 0 (new contributor)
• Rank: Unranked
• Contributions: 0

**Example Contribution:**
"USDT - Reddit discussing Tether reserves concern. Sentiment: NEGATIVE. Source: reddit.com/r/cryptocurrency"

Start contributing and help make CryptoGuard smarter! 🤖
        """

        await update.message.reply_text(contribute_msg, parse_mode='Markdown')
        logger.info(f"User {user_id} accessed contribute system")

    except Exception as e:
        capture_exception(
            e,
            extra={
                "command": "contribute",
                "user_id": user_id,
            },
        )
        await update.message.reply_text(
            "❌ Error accessing contribution system. Please try again later."
        )
        logger.error(f"Contribute command error: {sanitize_error_message(e)}")


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command - show top contributors"""
    user = update.effective_user
    if not user:
        await update.message.reply_text("❌ Unable to identify user. Please try again.")
        return

    # Mock leaderboard for now - will be replaced with real data
    leaderboard_msg = """
🏆 **Community Leaderboard**

**Top Contributors This Month:**

🥇 **CryptoAnalyst** - 2,350 points
   • 47 contributions • 12 first alerts • Premium member

🥈 **DeFiWatcher** - 1,890 points
   • 38 contributions • 8 first alerts • Premium member

🥉 **StablecoinGuru** - 1,245 points
   • 25 contributions • 5 first alerts

**4.** BlockchainBob - 890 points
**5.** PegMonitor - 750 points
**6.** RiskAssessor - 680 points
**7.** MarketSentinel - 525 points
**8.** DegenDetector - 450 points
**9.** AlertMaster - 380 points
**10.** CryptoGuardian - 320 points

**🎯 Your Rank:** Not on leaderboard yet
**📊 Your Points:** 0

**🏅 Rewards:**
• Top 10: Premium access for 1 month
• Top 3: Permanent Premium + API access
• #1: Premium + Enterprise features

Start contributing with /contribute to climb the ranks! 🚀
    """

    await update.message.reply_text(leaderboard_msg, parse_mode='Markdown')


async def rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rewards command - show user's contribution points and rewards"""
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

        # Mock user contribution data - will be replaced with real database
        rewards_msg = """
🎁 **Your Contribution Rewards**

**📊 Current Status:**
• Total Points: 0
• Rank: Unranked
• Contributions: 0
• First Reports: 0

**🏆 Achievements:**
🔒 First Contributor (contribute 1 observation)
🔒 News Hunter (first to report breaking news)
🔒 Quality Analyst (5 high-quality contributions)
🔒 Sentiment Master (10 sentiment reports)
🔒 Premium Earner (reach top 10 leaderboard)

**🎯 Point Values:**
• Basic contribution: 10 points
• Breaking news (first): 50 points
• High-quality analysis: 25 points bonus
• Verified prediction: 100 points bonus

**🏅 Reward Tiers:**
• **100 points:** Community Badge
• **500 points:** 1 week Premium trial
• **1,000 points:** 1 month Premium access
• **Top 10:** Permanent Premium
• **Top 3:** Premium + Enterprise API access

**Next Goal:** Earn your first 10 points with /contribute

Ready to start contributing? Use /contribute to begin! 🚀
        """

        await update.message.reply_text(rewards_msg, parse_mode='Markdown')

    except Exception as e:
        capture_exception(
            e,
            extra={
                "command": "rewards",
                "user_id": user_id,
            },
        )
        await update.message.reply_text(
            "❌ Error accessing rewards system. Please try again later."
        )
        logger.error(f"Rewards command error: {sanitize_error_message(e)}")


async def handle_contribution_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages that could be contributions"""
    user = update.effective_user
    if not user:
        return

    message = update.message
    if not message or not message.text:
        return

    # Check if this is a reply to the contribute command
    if message.reply_to_message and message.reply_to_message.from_user.is_bot:
        reply_text = message.reply_to_message.text or ""
        if "Community Data Contribution" in reply_text:
            await process_user_contribution(update, context)

    # Also check for contribution-like patterns in regular messages
    text = message.text.upper()
    stablecoin_symbols = ['USDT', 'USDC', 'DAI', 'USDS', 'FRAX', 'TUSD', 'USDP', 'PYUSD']
    sentiment_words = ['POSITIVE', 'NEGATIVE', 'NEUTRAL', 'BULLISH', 'BEARISH', 'GOOD', 'BAD']

    # Check if message contains stablecoin symbol and sentiment
    has_symbol = any(symbol in text for symbol in stablecoin_symbols)
    has_sentiment = any(word in text for word in sentiment_words)

    if has_symbol and (has_sentiment or len(message.text) > 20):
        await process_user_contribution(update, context)


async def process_user_contribution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process and acknowledge user contribution"""
    user = update.effective_user
    user_id = str(user.id)
    contribution_text = update.message.text

    try:
        # Register user if needed
        UserManager.register_or_get_user(
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        # Simple contribution processing (mock for now)
        # In production, this would analyze the text and store in database

        # Extract stablecoin symbol
        stablecoins = ['USDT', 'USDC', 'DAI', 'USDS', 'FRAX', 'TUSD', 'USDP', 'PYUSD']
        mentioned_coins = [coin for coin in stablecoins if coin in contribution_text.upper()]

        # Extract sentiment
        sentiment = "NEUTRAL"
        text_upper = contribution_text.upper()
        if any(word in text_upper for word in ['POSITIVE', 'GOOD', 'BULLISH', 'STRONG']):
            sentiment = "POSITIVE"
        elif any(word in text_upper for word in ['NEGATIVE', 'BAD', 'BEARISH', 'WEAK', 'CONCERN']):
            sentiment = "NEGATIVE"

        # Mock point calculation
        base_points = 10
        quality_bonus = 5 if len(contribution_text) > 30 else 0
        symbol_bonus = 5 if mentioned_coins else 0
        total_points = base_points + quality_bonus + symbol_bonus

        # Send acknowledgment
        response = f"""
🎉 **Contribution Received!**

**Your Analysis:**
• Text: "{contribution_text[:100]}{'...' if len(contribution_text) > 100 else ''}"
• Detected Coins: {', '.join(mentioned_coins) if mentioned_coins else 'None detected'}
• Sentiment: {sentiment}

**Points Earned:**
• Base contribution: {base_points} points
• Quality bonus: {quality_bonus} points
• Symbol detection: {symbol_bonus} points
• **Total: +{total_points} points** 🏆

**Updated Stats:**
• Total Points: {total_points} (new contributor)
• Rank: Contributing
• Next Goal: 100 points for Community Badge

Thank you for helping improve CryptoGuard's AI! 🤖

Use /rewards to see your full contribution history.
        """

        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"Processed contribution from user {user_id}: {total_points} points")

    except Exception as e:
        capture_exception(
            e,
            extra={
                "function": "process_user_contribution",
                "user_id": user_id,
                "contribution_text": contribution_text[:200],
            },
        )
        await update.message.reply_text(
            "❌ Error processing your contribution. Please try again later."
        )
        logger.error(f"Error processing contribution: {sanitize_error_message(e)}")


def setup_handlers(application):
    """Setup all command handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("risk", risk_command))
    application.add_handler(CommandHandler("predict", predict_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("account", account_command))
    application.add_handler(CommandHandler("threshold", threshold_command))

    # Community contribution commands
    application.add_handler(CommandHandler("contribute", contribute_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("rewards", rewards_command))

    # Message handler for processing user contributions (process text messages last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contribution_message))

    logger.info("All command handlers registered")
