"""
Database Models for DepegAlert Bot
SQLAlchemy models for users, alerts, preferences, and system data
"""
from datetime import datetime, timezone, timedelta
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    Text, ForeignKey, Enum, JSON, Index
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
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
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_status_timestamp', 'status', 'timestamp'),
    )

class AlertHistory(Base):
    """Record of all alerts sent to users"""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for channel alerts

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
        Index('idx_symbol_created', 'symbol', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
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
    __table_args__ = (
        Index('idx_metric_timestamp', 'metric_name', 'timestamp'),
    )

class AlertCooldown(Base):
    """Track alert cooldowns to prevent spam"""
    __tablename__ = "alert_cooldowns"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for global cooldowns
    channel_id = Column(String(100), nullable=False)

    # Cooldown information
    last_alert_at = Column(DateTime(timezone=True), nullable=False)
    cooldown_until = Column(DateTime(timezone=True), nullable=False, index=True)
    tier = Column(Enum(UserTier), nullable=False)  # Different cooldowns per tier

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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
    return session.query(UserPreference).filter(UserPreference.user_id == user_id).first()

def record_price_data(session, symbol: str, coingecko_id: str, price: float,
                     deviation: float, status: str):
    """Record price data to database"""
    price_record = StablecoinPrice(
        symbol=symbol,
        coingecko_id=coingecko_id,
        price=price,
        deviation_percent=deviation,
        status=status
    )
    session.add(price_record)
    session.commit()

def record_alert(session, symbol: str, price: float, deviation: float,
                status: str, channel: str, channel_id: str, message: str,
                user_id: Optional[int] = None) -> AlertHistory:
    """Record an alert in the database"""
    alert = AlertHistory(
        user_id=user_id,
        symbol=symbol,
        price=price,
        deviation_percent=deviation,
        status=status,
        channel=channel,
        channel_id=channel_id,
        message=message
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert

def is_in_cooldown(session, symbol: str, channel_id: str, tier: UserTier) -> bool:
    """Check if an alert is in cooldown period"""
    now = datetime.now(timezone.utc)
    cooldown = session.query(AlertCooldown).filter(
        AlertCooldown.symbol == symbol,
        AlertCooldown.channel_id == channel_id,
        AlertCooldown.tier == tier,
        AlertCooldown.cooldown_until > now
    ).first()

    return cooldown is not None

def update_cooldown(session, symbol: str, channel_id: str, tier: UserTier,
                   cooldown_minutes: int):
    """Update alert cooldown"""
    now = datetime.now(timezone.utc)
    cooldown_until = now + timedelta(minutes=cooldown_minutes)

    # Try to update existing cooldown
    cooldown = session.query(AlertCooldown).filter(
        AlertCooldown.symbol == symbol,
        AlertCooldown.channel_id == channel_id,
        AlertCooldown.tier == tier
    ).first()

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
            cooldown_until=cooldown_until
        )
        session.add(cooldown)

    session.commit()