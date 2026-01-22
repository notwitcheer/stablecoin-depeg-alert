"""
User Management System
Handles user registration, preferences, subscription tiers, and permissions
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.database import get_db_session
from core.db_models import (
    AlertCooldown,
    User,
    UserPreference,
    UserTier,
    create_user,
    get_user_by_telegram_id,
    get_user_preferences,
    is_in_cooldown,
    update_cooldown,
)

logger = logging.getLogger(__name__)


class UserManager:
    """Manages user accounts, preferences, and permissions"""

    @staticmethod
    def register_or_get_user(
        telegram_id: str,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> User:
        """Register a new user or get existing user"""
        with get_db_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)

            if user:
                # Update user info if provided
                if username and user.username != username:
                    user.username = username
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                if last_name and user.last_name != last_name:
                    user.last_name = last_name

                user.last_active = datetime.now(timezone.utc)
                session.commit()

                logger.info(f"Updated existing user: {telegram_id}")
            else:
                # Create new user
                user = create_user(
                    session,
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    last_active=datetime.now(timezone.utc),
                )

                # Create default preferences
                UserManager._create_default_preferences(session, user.id)

                logger.info(f"Created new user: {telegram_id}")

            return user

    @staticmethod
    def _create_default_preferences(session, user_id: int):
        """Create default user preferences"""
        default_prefs = UserPreference(
            user_id=user_id,
            enabled_tiers=[1],  # Free tier gets Tier 1 stablecoins only
            alert_channels=["telegram"],
            excluded_stablecoins=[],
            priority_stablecoins=["USDT", "USDC", "DAI"],
            max_alerts_per_hour=10,
        )
        session.add(default_prefs)
        session.commit()
        logger.info(f"Created default preferences for user {user_id}")

    @staticmethod
    def get_user_info(telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user information and preferences"""
        with get_db_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)
            if not user:
                return None

            preferences = get_user_preferences(session, user.id)

            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "tier": user.tier.value,
                "is_active": user.is_active,
                "subscription_end": user.subscription_end,
                "preferences": (
                    {
                        "custom_threshold": (
                            preferences.custom_threshold if preferences else None
                        ),
                        "enabled_tiers": (
                            preferences.enabled_tiers if preferences else [1, 2]
                        ),
                        "alert_channels": (
                            preferences.alert_channels if preferences else ["telegram"]
                        ),
                        "excluded_stablecoins": (
                            preferences.excluded_stablecoins if preferences else []
                        ),
                        "priority_stablecoins": (
                            preferences.priority_stablecoins if preferences else []
                        ),
                        "max_alerts_per_hour": (
                            preferences.max_alerts_per_hour if preferences else 10
                        ),
                        "quiet_hours_start": (
                            preferences.quiet_hours_start if preferences else None
                        ),
                        "quiet_hours_end": (
                            preferences.quiet_hours_end if preferences else None
                        ),
                    }
                    if preferences
                    else None
                ),
            }

    @staticmethod
    def upgrade_user_tier(
        telegram_id: str, new_tier: UserTier, subscription_duration_days: int = 30
    ) -> bool:
        """Upgrade user to a higher tier"""
        with get_db_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)
            if not user:
                logger.error(f"User not found for tier upgrade: {telegram_id}")
                return False

            now = datetime.now(timezone.utc)
            user.tier = new_tier
            user.subscription_start = now
            user.subscription_end = now + timedelta(days=subscription_duration_days)

            # Update preferences for premium users
            if new_tier in [UserTier.PREMIUM, UserTier.ENTERPRISE]:
                preferences = get_user_preferences(session, user.id)
                if preferences:
                    preferences.enabled_tiers = [1, 2]  # Access to all tiers
                    preferences.max_alerts_per_hour = (
                        50 if new_tier == UserTier.PREMIUM else 200
                    )

            session.commit()
            logger.info(f"Upgraded user {telegram_id} to {new_tier.value}")
            return True

    @staticmethod
    def update_user_preferences(telegram_id: str, **preferences) -> bool:
        """Update user preferences"""
        with get_db_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)
            if not user:
                return False

            user_prefs = get_user_preferences(session, user.id)
            if not user_prefs:
                # Create preferences if they don't exist
                UserManager._create_default_preferences(session, user.id)
                user_prefs = get_user_preferences(session, user.id)

            # Update provided preferences
            for key, value in preferences.items():
                if hasattr(user_prefs, key):
                    setattr(user_prefs, key, value)

            user_prefs.updated_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(f"Updated preferences for user {telegram_id}: {preferences}")
            return True

    @staticmethod
    def set_custom_threshold(telegram_id: str, threshold_percent: float) -> bool:
        """Set custom alert threshold for premium users"""
        user_info = UserManager.get_user_info(telegram_id)
        if not user_info:
            return False

        # Check if user has premium access
        if user_info["tier"] not in ["premium", "enterprise"]:
            logger.warning(
                f"User {telegram_id} tried to set custom threshold without premium"
            )
            return False

        # Validate threshold range
        if not 0.01 <= threshold_percent <= 5.0:
            logger.warning(
                f"Invalid threshold {threshold_percent}% for user {telegram_id}"
            )
            return False

        return UserManager.update_user_preferences(
            telegram_id, custom_threshold=threshold_percent
        )

    @staticmethod
    def get_user_alert_threshold(telegram_id: str) -> float:
        """Get user's effective alert threshold"""
        user_info = UserManager.get_user_info(telegram_id)
        if not user_info or not user_info["preferences"]:
            return 0.5  # Default free threshold

        custom_threshold = user_info["preferences"]["custom_threshold"]
        if custom_threshold is not None and user_info["tier"] in [
            "premium",
            "enterprise",
        ]:
            return custom_threshold

        # Default thresholds by tier
        tier_thresholds = {"free": 0.5, "premium": 0.2, "enterprise": 0.1}
        return tier_thresholds.get(user_info["tier"], 0.5)

    @staticmethod
    def can_receive_alerts(telegram_id: str) -> bool:
        """Check if user can receive alerts (active subscription, not in quiet hours)"""
        user_info = UserManager.get_user_info(telegram_id)
        if not user_info:
            return False

        # Check if user is active
        if not user_info["is_active"]:
            return False

        # Check subscription for premium users
        if user_info["tier"] in ["premium", "enterprise"]:
            subscription_end = user_info["subscription_end"]
            if subscription_end and datetime.now(timezone.utc) > subscription_end:
                # Subscription expired, downgrade to free
                UserManager._downgrade_expired_user(telegram_id)
                return True  # Still can receive free alerts

        # Check quiet hours
        if user_info["preferences"]:
            prefs = user_info["preferences"]
            if (
                prefs["quiet_hours_start"] is not None
                and prefs["quiet_hours_end"] is not None
            ):
                now_hour = datetime.now(timezone.utc).hour
                start = prefs["quiet_hours_start"]
                end = prefs["quiet_hours_end"]

                if start <= end:
                    # Normal range (e.g., 23:00-07:00)
                    if start <= now_hour < end:
                        return False
                else:
                    # Overnight range (e.g., 23:00-07:00)
                    if now_hour >= start or now_hour < end:
                        return False

        return True

    @staticmethod
    def _downgrade_expired_user(telegram_id: str):
        """Downgrade user to free tier when subscription expires"""
        with get_db_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)
            if user and user.tier != UserTier.FREE:
                user.tier = UserTier.FREE

                # Update preferences
                preferences = get_user_preferences(session, user.id)
                if preferences:
                    preferences.enabled_tiers = [1]  # Back to free tier (tier 1 only)
                    preferences.custom_threshold = None
                    preferences.max_alerts_per_hour = 10

                session.commit()
                logger.info(f"Downgraded expired user {telegram_id} to free tier")

    @staticmethod
    def check_alert_cooldown(telegram_id: str, symbol: str, channel_id: str) -> bool:
        """Check if user is in cooldown for specific symbol"""
        user_info = UserManager.get_user_info(telegram_id)
        if not user_info:
            return True  # Block if user not found

        tier = UserTier(user_info["tier"])

        with get_db_session() as session:
            return is_in_cooldown(session, symbol, channel_id, tier)

    @staticmethod
    def update_alert_cooldown(telegram_id: str, symbol: str, channel_id: str):
        """Update alert cooldown for user"""
        user_info = UserManager.get_user_info(telegram_id)
        if not user_info:
            return

        tier = UserTier(user_info["tier"])

        # Different cooldown periods by tier
        cooldown_minutes = {
            UserTier.FREE: 30,
            UserTier.PREMIUM: 5,
            UserTier.ENTERPRISE: 1,
        }

        with get_db_session() as session:
            update_cooldown(session, symbol, channel_id, tier, cooldown_minutes[tier])

    @staticmethod
    def get_user_statistics() -> Dict[str, int]:
        """Get user statistics for admin dashboard"""
        with get_db_session() as session:
            total_users = session.query(User).count()
            active_users = session.query(User).filter(User.is_active.is_(True)).count()
            free_users = session.query(User).filter(User.tier == UserTier.FREE).count()
            premium_users = (
                session.query(User).filter(User.tier == UserTier.PREMIUM).count()
            )
            enterprise_users = (
                session.query(User).filter(User.tier == UserTier.ENTERPRISE).count()
            )

            return {
                "total_users": total_users,
                "active_users": active_users,
                "free_users": free_users,
                "premium_users": premium_users,
                "enterprise_users": enterprise_users,
            }


class SubscriptionManager:
    """Handles subscription lifecycle and billing events"""

    @staticmethod
    def activate_premium_subscription(
        telegram_id: str, duration_days: int = 30
    ) -> bool:
        """Activate premium subscription for user"""
        return UserManager.upgrade_user_tier(
            telegram_id, UserTier.PREMIUM, duration_days
        )

    @staticmethod
    def activate_enterprise_subscription(
        telegram_id: str, duration_days: int = 365
    ) -> bool:
        """Activate enterprise subscription for user"""
        return UserManager.upgrade_user_tier(
            telegram_id, UserTier.ENTERPRISE, duration_days
        )

    @staticmethod
    def cancel_subscription(telegram_id: str) -> bool:
        """Cancel user subscription (immediate downgrade)"""
        with get_db_session() as session:
            user = get_user_by_telegram_id(session, telegram_id)
            if not user:
                return False

            user.tier = UserTier.FREE
            user.subscription_end = datetime.now(timezone.utc)

            # Reset preferences
            preferences = get_user_preferences(session, user.id)
            if preferences:
                preferences.enabled_tiers = [1]  # Back to free tier (tier 1 only)
                preferences.custom_threshold = None
                preferences.max_alerts_per_hour = 10

            session.commit()
            logger.info(f"Cancelled subscription for user {telegram_id}")
            return True

    @staticmethod
    def get_subscription_status(telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription status for user"""
        user_info = UserManager.get_user_info(telegram_id)
        if not user_info:
            return None

        now = datetime.now(timezone.utc)
        subscription_end = user_info["subscription_end"]

        is_expired = False
        days_remaining = 0

        if subscription_end:
            is_expired = now > subscription_end
            if not is_expired:
                days_remaining = (subscription_end - now).days

        return {
            "tier": user_info["tier"],
            "is_expired": is_expired,
            "days_remaining": days_remaining,
            "subscription_end": subscription_end,
            "custom_threshold": (
                user_info["preferences"]["custom_threshold"]
                if user_info["preferences"]
                else None
            ),
        }
