"""
CryptoGuard Data Models - Enhanced for AI-Powered Stablecoin Monitoring
Evolved from basic depeg alerting to comprehensive risk assessment platform
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal


class PegStatus(Enum):
    STABLE = "stable"  # < 0.2% deviation
    WARNING = "warning"  # 0.2% - 0.5% deviation
    DEPEG = "depeg"  # > 0.5% deviation
    CRITICAL = "critical"  # > 2% deviation


class RiskLevel(Enum):
    """AI-powered risk assessment levels"""
    LOW = "low"  # 0-25 risk score
    MEDIUM = "medium"  # 26-50 risk score
    HIGH = "high"  # 51-75 risk score
    CRITICAL = "critical"  # 76-100 risk score


class AlertSeverity(Enum):
    """Alert severity levels for different user tiers"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SubscriptionTier(Enum):
    """User subscription tiers with different feature access"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class StablecoinDefinition:
    """Enhanced stablecoin definition for CryptoGuard"""

    symbol: str
    name: str
    coingecko_id: str
    type: str  # "Centralized", "Decentralized", "Algorithmic", etc.
    tier: int  # 1 (free), 2 (premium), 3 (enterprise)
    blockchain: str = "ethereum"
    contract_address: Optional[str] = None
    is_active: bool = True
    market_cap_tier: str = "large"  # large, medium, small


@dataclass
class SocialSentiment:
    """Social media sentiment analysis for a stablecoin"""

    stablecoin_symbol: str
    platform: str  # twitter, reddit, telegram
    sentiment_score: float  # -100 to +100
    mention_count: int
    engagement_score: float
    fear_greed_index: float  # 0-100
    timestamp: datetime


@dataclass
class RiskAssessment:
    """AI-powered risk assessment for depeg probability"""

    stablecoin_symbol: str
    risk_score: float  # 0-100
    risk_level: RiskLevel
    confidence: float  # 0-100
    prediction_horizon: str  # "1h", "6h", "24h"
    contributing_factors: Dict[str, float]  # feature importance
    social_sentiment_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StablecoinPeg:
    """Enhanced peg status with AI predictions and risk assessment"""

    symbol: str
    name: str
    coingecko_id: str
    price: Decimal
    deviation_percent: float
    status: PegStatus
    last_updated: datetime

    # Enhanced CryptoGuard features
    risk_assessment: Optional[RiskAssessment] = None
    social_sentiment: Optional[SocialSentiment] = None
    volume_24h: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    volatility_1h: Optional[float] = None
    volatility_24h: Optional[float] = None

    @property
    def is_alertable(self) -> bool:
        """Enhanced alerting logic with AI risk assessment"""
        # Traditional peg-based alerts
        if self.status in [PegStatus.DEPEG, PegStatus.CRITICAL]:
            return True

        # AI-powered risk alerts
        if self.risk_assessment:
            if self.risk_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return True

        return False

    @property
    def is_stable(self) -> bool:
        """Check if stablecoin is stable considering both peg and risk"""
        peg_stable = self.status == PegStatus.STABLE
        risk_stable = True

        if self.risk_assessment:
            risk_stable = self.risk_assessment.risk_level == RiskLevel.LOW

        return peg_stable and risk_stable

    @property
    def overall_risk_score(self) -> float:
        """Combined risk score from price deviation and AI assessment"""
        price_risk = min(abs(self.deviation_percent) * 20, 100)  # Scale deviation to 0-100

        if self.risk_assessment:
            ai_risk = self.risk_assessment.risk_score
            # Weighted combination: 60% AI, 40% price deviation
            return (ai_risk * 0.6) + (price_risk * 0.4)

        return price_risk


@dataclass
class User:
    """User management for subscription tiers and preferences"""

    id: Optional[int] = None
    telegram_id: Optional[int] = None
    email: Optional[str] = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    custom_threshold: float = 0.5  # Custom alert threshold percentage
    webhook_url: Optional[str] = None  # For enterprise webhooks
    api_key: Optional[str] = None  # For API access
    preferred_coins: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)

    @property
    def can_access_premium_features(self) -> bool:
        """Check if user can access premium features"""
        return self.subscription_tier in [SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE]

    @property
    def can_access_enterprise_features(self) -> bool:
        """Check if user can access enterprise features"""
        return self.subscription_tier == SubscriptionTier.ENTERPRISE


@dataclass
class AlertRecord:
    """Enhanced alert record with AI context and multi-channel support"""

    stablecoin_symbol: str
    price: Decimal
    deviation_percent: float
    status: PegStatus
    alert_severity: AlertSeverity
    timestamp: datetime

    # Enhanced features
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    prediction_probability: Optional[float] = None
    social_sentiment_score: Optional[float] = None
    contributing_factors: Optional[Dict[str, Any]] = None

    # Distribution tracking
    channels_sent: List[str] = field(default_factory=list)  # telegram, email, webhook, etc.
    user_tier_sent: List[SubscriptionTier] = field(default_factory=list)
    total_recipients: int = 0

    # Effectiveness tracking
    user_actions: List[str] = field(default_factory=list)  # clicked, dismissed, upgraded, etc.
    accuracy_verified: Optional[bool] = None  # Did the predicted event occur?


@dataclass
class PredictionResult:
    """AI model prediction result"""

    stablecoin_symbol: str
    prediction_type: str  # "depeg", "recovery", "volatility"
    probability: float  # 0-1
    confidence: float  # 0-1
    time_horizon: str  # "1h", "6h", "24h"
    predicted_price_range: tuple[float, float]  # (min, max)
    model_version: str
    features_used: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhookAlert:
    """Webhook payload for enterprise customers"""

    alert_id: str
    stablecoin: str
    current_price: float
    deviation_percent: float
    risk_score: float
    alert_severity: str
    prediction: Optional[Dict[str, Any]] = None
    social_sentiment: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
