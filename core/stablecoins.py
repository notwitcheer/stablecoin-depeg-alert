"""
Stablecoin Definitions
Tracks all monitored stablecoins with their CoinGecko IDs and metadata
"""

from typing import List

from core.models import StablecoinDefinition

# Tier 1 - Always track (largest market caps)
TIER1_STABLECOINS = [
    StablecoinDefinition("USDT", "Tether", "tether", "Centralized", 1),
    StablecoinDefinition("USDC", "USD Coin", "usd-coin", "Centralized", 1),
    StablecoinDefinition("DAI", "Dai", "dai", "Decentralized", 1),
    StablecoinDefinition("USDS", "USDS", "usds", "Decentralized", 1),
]

# Tier 2 - Track in MVP
TIER2_STABLECOINS = [
    StablecoinDefinition("FRAX", "Frax", "frax", "Algorithmic", 2),
    StablecoinDefinition("TUSD", "TrueUSD", "true-usd", "Centralized", 2),
    StablecoinDefinition("USDP", "Pax Dollar", "paxos-standard", "Centralized", 2),
    StablecoinDefinition("PYUSD", "PayPal USD", "paypal-usd", "Centralized", 2),
]

# Tier 3 - Premium only
TIER3_STABLECOINS = [
    StablecoinDefinition("LUSD", "Liquity USD", "liquity-usd", "Decentralized", 3),
    StablecoinDefinition("GUSD", "Gemini Dollar", "gemini-dollar", "Centralized", 3),
    StablecoinDefinition("USDD", "USDD", "usdd", "Algorithmic", 3),
    StablecoinDefinition(
        "FDUSD", "First Digital USD", "first-digital-usd", "Centralized", 3
    ),
    StablecoinDefinition("CRVUSD", "Curve.Fi USD", "crvusd", "Decentralized", 3),
    StablecoinDefinition("GHO", "GHO", "gho", "Decentralized", 3),
    StablecoinDefinition("DOLA", "Dola USD", "dola-usd", "Decentralized", 3),
    StablecoinDefinition(
        "MIM", "Magic Internet Money", "magic-internet-money", "Decentralized", 3
    ),
    StablecoinDefinition("sUSD", "sUSD", "susd", "Synthetic", 3),
    StablecoinDefinition("EURS", "STASIS EURS", "stasis-eurs", "EUR-pegged", 3),
    StablecoinDefinition("EURT", "Tether EURt", "tether-eurt", "EUR-pegged", 3),
]

# All stablecoins combined
ALL_STABLECOINS = TIER1_STABLECOINS + TIER2_STABLECOINS + TIER3_STABLECOINS

# Default tracking for free tier (Tier 1 + Tier 2)
FREE_TIER_STABLECOINS = TIER1_STABLECOINS + TIER2_STABLECOINS

# Symbol to definition mapping for quick lookups
STABLECOIN_MAP = {stable.symbol: stable for stable in ALL_STABLECOINS}


def get_stablecoins_by_tier(tiers: List[int]) -> List[StablecoinDefinition]:
    """Get stablecoins filtered by tier(s)"""
    return [s for s in ALL_STABLECOINS if s.tier in tiers]


def get_stablecoin_by_symbol(symbol: str) -> StablecoinDefinition:
    """Get stablecoin definition by symbol"""
    return STABLECOIN_MAP.get(symbol.upper())


def get_coingecko_ids(stablecoins: List[StablecoinDefinition]) -> List[str]:
    """Extract CoinGecko IDs from stablecoin definitions"""
    return [s.coingecko_id for s in stablecoins]
