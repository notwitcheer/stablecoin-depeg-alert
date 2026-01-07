"""
Data Models for Stablecoin Depeg Alert System
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class PegStatus(Enum):
    STABLE = "stable"        # < 0.2% deviation
    WARNING = "warning"      # 0.2% - 0.5% deviation
    DEPEG = "depeg"          # > 0.5% deviation
    CRITICAL = "critical"    # > 2% deviation

@dataclass
class StablecoinDefinition:
    """Definition of a tracked stablecoin"""
    symbol: str
    name: str
    coingecko_id: str
    type: str  # "Centralized", "Decentralized", "Algorithmic", etc.
    tier: int  # 1, 2, or 3

@dataclass
class StablecoinPeg:
    """Current peg status of a stablecoin"""
    symbol: str
    name: str
    coingecko_id: str
    price: float
    deviation_percent: float
    status: PegStatus
    last_updated: datetime

    @property
    def is_alertable(self) -> bool:
        """Check if this peg status should trigger an alert"""
        return self.status in [PegStatus.DEPEG, PegStatus.CRITICAL]

    @property
    def is_stable(self) -> bool:
        """Check if this stablecoin is considered stable"""
        return self.status == PegStatus.STABLE

@dataclass
class AlertRecord:
    """Record of a sent alert"""
    symbol: str
    price: float
    deviation_percent: float
    status: PegStatus
    timestamp: datetime
    channel_id: str