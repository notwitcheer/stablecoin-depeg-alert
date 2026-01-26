"""
Database Models for DepegAlert Bot
SQLAlchemy models for users, alerts, preferences, and system data
"""

from datetime import datetime, timedelta, timezone
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class UserTier(PyEnum):
    """User subscription tiers"""

    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class AlertStatus(PyEnum):
    """Alert delivery status"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    COOLDOWN = "cooldown"


class User(Base):
    """User accounts and subscription management"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Subscription information
    tier = Column(Enum(UserTier), default=UserTier.FREE, nullable=False)
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Preferences
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)

    # Tracking
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_active = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    preferences = relationship("UserPreference", back_populates="user")
    alert_history = relationship("AlertHistory", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, tier={self.tier.value})>"


class UserPreference(Base):
    """User-specific alert preferences and thresholds"""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Alert preferences
    custom_threshold = Column(Float, nullable=True)  # Custom deviation threshold
    enabled_tiers = Column(JSON, default=[1, 2])  # Which stablecoin tiers to monitor
    alert_channels = Column(JSON, default=["telegram"])  # Where to send alerts

    # Stablecoin-specific preferences
    excluded_stablecoins = Column(JSON, default=[])  # Stablecoins to ignore
    priority_stablecoins = Column(JSON, default=[])  # High-priority stablecoins

    # Notification timing
    quiet_hours_start = Column(Integer, nullable=True)  # Hour (0-23)
    quiet_hours_end = Column(Integer, nullable=True)  # Hour (0-23)
    max_alerts_per_hour = Column(Integer, default=10)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")


class StablecoinPrice(Base):
    """Historical price data for stablecoins"""

    __tablename__ = "stablecoin_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    coingecko_id = Column(String(50), nullable=False)

    # Price data
    price = Column(Float, nullable=False)
    deviation_percent = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)  # stable, warning, depeg, critical

    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source = Column(String(50), default="coingecko", nullable=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_symbol_timestamp", "symbol", "timestamp"),
        Index("idx_status_timestamp", "status", "timestamp"),
    )


class AlertHistory(Base):
    """Record of all alerts sent to users"""

    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Null for channel alerts

    # Alert details
    symbol = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    deviation_percent = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)

    # Delivery information
    channel = Column(String(50), nullable=False)  # telegram, email, webhook, etc.
    channel_id = Column(String(100), nullable=False)  # Telegram chat ID, email, etc.
    message = Column(Text, nullable=False)  # Full alert message
    alert_status = Column(Enum(AlertStatus), default=AlertStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="alert_history")

    # Indexes
    __table_args__ = (
        Index("idx_symbol_created", "symbol", "created_at"),
        Index("idx_user_created", "user_id", "created_at"),
    )


class SystemMetric(Base):
    """System health and performance metrics"""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Metric information
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=False)

    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tags = Column(JSON, default={})  # Additional metric tags

    # Index for time-series queries
    __table_args__ = (Index("idx_metric_timestamp", "metric_name", "timestamp"),)


class AlertCooldown(Base):
    """Track alert cooldowns to prevent spam"""

    __tablename__ = "alert_cooldowns"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Null for global cooldowns
    channel_id = Column(String(100), nullable=False)

    # Cooldown information
    last_alert_at = Column(DateTime(timezone=True), nullable=False)
    cooldown_until = Column(DateTime(timezone=True), nullable=False, index=True)
    tier = Column(Enum(UserTier), nullable=False)  # Different cooldowns per tier

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ContributionType(PyEnum):
    """Types of community contributions"""

    MARKET_INSIGHT = "market_insight"
    PRICE_REPORT = "price_report"
    NEWS_SHARE = "news_share"
    SENTIMENT_FEEDBACK = "sentiment_feedback"
    GENERAL_INFO = "general_info"


class UserContribution(Base):
    """Track user contributions to the community data network"""

    __tablename__ = "user_contributions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Contribution details
    contribution_type = Column(Enum(ContributionType), nullable=False)
    content = Column(Text, nullable=False)
    stablecoin_symbol = Column(String(10), nullable=True, index=True)

    # AI Analysis results
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    quality_score = Column(Float, nullable=True)    # 0.0 to 1.0
    relevance_score = Column(Float, nullable=True)  # 0.0 to 1.0

    # Rewards
    points_awarded = Column(Integer, default=0, nullable=False)
    bonus_multiplier = Column(Float, default=1.0, nullable=False)

    # Metadata
    source_message_id = Column(String(100), nullable=True)  # Telegram message ID
    processed = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="contributions")

    # Indexes
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_symbol_created", "stablecoin_symbol", "created_at"),
        Index("idx_type_created", "contribution_type", "created_at"),
    )


class UserPoints(Base):
    """Track user points and leaderboard rankings"""

    __tablename__ = "user_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Point totals
    total_points = Column(Integer, default=0, nullable=False, index=True)
    weekly_points = Column(Integer, default=0, nullable=False)
    monthly_points = Column(Integer, default=0, nullable=False)

    # Statistics
    contribution_count = Column(Integer, default=0, nullable=False)
    streak_days = Column(Integer, default=0, nullable=False)
    last_contribution_date = Column(DateTime(timezone=True), nullable=True)

    # Rankings (updated periodically)
    global_rank = Column(Integer, nullable=True, index=True)
    weekly_rank = Column(Integer, nullable=True)
    monthly_rank = Column(Integer, nullable=True)

    # Rewards earned
    rewards_earned = Column(JSON, default=[], nullable=False)  # List of reward milestones
    premium_months_earned = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Weekly/monthly reset tracking
    last_weekly_reset = Column(DateTime(timezone=True), nullable=True)
    last_monthly_reset = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="points")

    # Indexes
    __table_args__ = (
        Index("idx_total_points_desc", "total_points", postgresql_using="btree"),
        Index("idx_weekly_points_desc", "weekly_points", postgresql_using="btree"),
        Index("idx_monthly_points_desc", "monthly_points", postgresql_using="btree"),
    )


# Utility functions for database operations


def get_user_by_telegram_id(session, telegram_id: str) -> Optional[User]:
    """Get user by Telegram ID"""
    return session.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(session, telegram_id: str, **kwargs) -> User:
    """Create a new user"""
    user = User(telegram_id=telegram_id, **kwargs)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_preferences(session, user_id: int) -> Optional[UserPreference]:
    """Get user preferences"""
    return (
        session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    )


def record_price_data(
    session, symbol: str, coingecko_id: str, price: float, deviation: float, status: str
):
    """Record price data to database"""
    price_record = StablecoinPrice(
        symbol=symbol,
        coingecko_id=coingecko_id,
        price=price,
        deviation_percent=deviation,
        status=status,
    )
    session.add(price_record)
    session.commit()


def record_alert(
    session,
    symbol: str,
    price: float,
    deviation: float,
    status: str,
    channel: str,
    channel_id: str,
    message: str,
    user_id: Optional[int] = None,
) -> AlertHistory:
    """Record an alert in the database"""
    alert = AlertHistory(
        user_id=user_id,
        symbol=symbol,
        price=price,
        deviation_percent=deviation,
        status=status,
        channel=channel,
        channel_id=channel_id,
        message=message,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def is_in_cooldown(session, symbol: str, channel_id: str, tier: UserTier) -> bool:
    """Check if an alert is in cooldown period"""
    now = datetime.now(timezone.utc)
    cooldown = (
        session.query(AlertCooldown)
        .filter(
            AlertCooldown.symbol == symbol,
            AlertCooldown.channel_id == channel_id,
            AlertCooldown.tier == tier,
            AlertCooldown.cooldown_until > now,
        )
        .first()
    )

    return cooldown is not None


def update_cooldown(
    session, symbol: str, channel_id: str, tier: UserTier, cooldown_minutes: int
):
    """Update alert cooldown"""
    now = datetime.now(timezone.utc)
    cooldown_until = now + timedelta(minutes=cooldown_minutes)

    # Try to update existing cooldown
    cooldown = (
        session.query(AlertCooldown)
        .filter(
            AlertCooldown.symbol == symbol,
            AlertCooldown.channel_id == channel_id,
            AlertCooldown.tier == tier,
        )
        .first()
    )

    if cooldown:
        cooldown.last_alert_at = now
        cooldown.cooldown_until = cooldown_until
        cooldown.updated_at = now
    else:
        # Create new cooldown
        cooldown = AlertCooldown(
            symbol=symbol,
            channel_id=channel_id,
            tier=tier,
            last_alert_at=now,
            cooldown_until=cooldown_until,
        )
        session.add(cooldown)

    session.commit()


# Contribution and leaderboard utility functions


def record_user_contribution(
    session,
    user_id: int,
    content: str,
    contribution_type: ContributionType = ContributionType.GENERAL_INFO,
    stablecoin_symbol: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    quality_score: Optional[float] = None,
    relevance_score: Optional[float] = None,
    source_message_id: Optional[str] = None,
) -> UserContribution:
    """Record a user contribution to the database"""
    contribution = UserContribution(
        user_id=user_id,
        contribution_type=contribution_type,
        content=content,
        stablecoin_symbol=stablecoin_symbol,
        sentiment_score=sentiment_score,
        quality_score=quality_score,
        relevance_score=relevance_score,
        source_message_id=source_message_id,
    )
    session.add(contribution)
    session.commit()
    session.refresh(contribution)
    return contribution


def award_points_for_contribution(
    session,
    user_id: int,
    points: int,
    bonus_multiplier: float = 1.0,
) -> UserPoints:
    """Award points to a user for their contribution"""
    # Get or create user points record
    user_points = session.query(UserPoints).filter(UserPoints.user_id == user_id).first()

    if not user_points:
        user_points = UserPoints(
            user_id=user_id,
            total_points=0,
            weekly_points=0,
            monthly_points=0,
            contribution_count=0,
            streak_days=0
        )
        session.add(user_points)

    # Calculate final points with bonus
    final_points = int(points * bonus_multiplier)

    # Update points (ensure they're not None)
    user_points.total_points = (user_points.total_points or 0) + final_points
    user_points.weekly_points = (user_points.weekly_points or 0) + final_points
    user_points.monthly_points = (user_points.monthly_points or 0) + final_points
    user_points.contribution_count = (user_points.contribution_count or 0) + 1

    # Check for streak (before updating last_contribution_date)
    now = datetime.now(timezone.utc)
    previous_date = user_points.last_contribution_date

    if previous_date:
        # Ensure both dates are timezone-aware
        if previous_date.tzinfo is None:
            previous_date = previous_date.replace(tzinfo=timezone.utc)
        days_since_last = (now - previous_date).days
        if days_since_last <= 1:
            user_points.streak_days = (user_points.streak_days or 0) + 1
        else:
            user_points.streak_days = 1
    else:
        user_points.streak_days = 1

    # Update the last contribution date
    user_points.last_contribution_date = now

    session.commit()
    session.refresh(user_points)
    return user_points


def get_leaderboard(
    session,
    limit: int = 10,
    timeframe: str = "total"  # "total", "weekly", "monthly"
) -> List[dict]:
    """Get leaderboard data"""
    if timeframe == "weekly":
        order_column = UserPoints.weekly_points
    elif timeframe == "monthly":
        order_column = UserPoints.monthly_points
    else:
        order_column = UserPoints.total_points

    results = (
        session.query(UserPoints, User)
        .join(User, UserPoints.user_id == User.id)
        .filter(order_column > 0)
        .order_by(order_column.desc())
        .limit(limit)
        .all()
    )

    leaderboard = []
    for rank, (points, user) in enumerate(results, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username or f"User{user.id}",
            "first_name": user.first_name,
            "total_points": points.total_points,
            "weekly_points": points.weekly_points,
            "monthly_points": points.monthly_points,
            "contribution_count": points.contribution_count,
            "streak_days": points.streak_days,
            "tier": user.tier.value,
        })

    return leaderboard


def get_user_stats(session, user_id: int) -> Optional[dict]:
    """Get detailed statistics for a specific user"""
    user_points = session.query(UserPoints).filter(UserPoints.user_id == user_id).first()
    user = session.query(User).filter(User.id == user_id).first()

    if not user_points or not user:
        return None

    # Get contribution breakdown
    contribution_stats = (
        session.query(
            UserContribution.contribution_type,
            func.count(UserContribution.id).label("count"),
            func.sum(UserContribution.points_awarded).label("total_points"),
        )
        .filter(UserContribution.user_id == user_id)
        .group_by(UserContribution.contribution_type)
        .all()
    )

    # Calculate global rank
    global_rank = (
        session.query(func.count(UserPoints.id))
        .filter(UserPoints.total_points > user_points.total_points)
        .scalar() + 1
    )

    return {
        "user_id": user_id,
        "username": user.username or f"User{user.id}",
        "first_name": user.first_name,
        "tier": user.tier.value,
        "total_points": user_points.total_points,
        "weekly_points": user_points.weekly_points,
        "monthly_points": user_points.monthly_points,
        "contribution_count": user_points.contribution_count,
        "streak_days": user_points.streak_days,
        "global_rank": global_rank,
        "contribution_breakdown": {
            stat.contribution_type.value: {
                "count": stat.count,
                "points": stat.total_points or 0
            }
            for stat in contribution_stats
        },
        "premium_months_earned": user_points.premium_months_earned,
        "rewards_earned": user_points.rewards_earned,
    }


def update_contribution_analysis(
    session,
    contribution_id: int,
    sentiment_score: Optional[float] = None,
    quality_score: Optional[float] = None,
    relevance_score: Optional[float] = None,
    points_awarded: int = 0,
):
    """Update contribution with AI analysis results and award points"""
    contribution = session.query(UserContribution).filter(
        UserContribution.id == contribution_id
    ).first()

    if not contribution:
        return None

    # Update analysis scores
    if sentiment_score is not None:
        contribution.sentiment_score = sentiment_score
    if quality_score is not None:
        contribution.quality_score = quality_score
    if relevance_score is not None:
        contribution.relevance_score = relevance_score

    contribution.points_awarded = points_awarded
    contribution.processed = True
    contribution.processed_at = datetime.now(timezone.utc)

    session.commit()

    # Award points to user
    if points_awarded > 0:
        award_points_for_contribution(
            session,
            contribution.user_id,
            points_awarded,
            contribution.bonus_multiplier
        )

    return contribution
