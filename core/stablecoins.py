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

# Tier 2 - Premium tracking (All additional stablecoins for premium users)
TIER2_STABLECOINS = [
    # Main premium stablecoins
    StablecoinDefinition("FRAX", "Frax", "frax", "Hybrid", 2),
    StablecoinDefinition("TUSD", "TrueUSD", "true-usd", "Centralized", 2),
    StablecoinDefinition("USDP", "Pax Dollar", "paxos-standard", "Centralized", 2),
    StablecoinDefinition("PYUSD", "PayPal USD", "paypal-usd", "Centralized", 2),
    StablecoinDefinition("BUSD", "Binance USD", "binance-usd", "Fiat-backed", 2),
    StablecoinDefinition("LUSD", "Liquity USD", "liquity-usd", "Crypto-backed", 2),
    StablecoinDefinition("MIM", "Magic Internet Money", "magic-internet-money", "Crypto-backed", 2),
    StablecoinDefinition("GHO", "GHO", "gho", "Crypto-backed", 2),
    StablecoinDefinition("DOLA", "Dola USD", "dola-usd", "Crypto-backed", 2),
    StablecoinDefinition("USDe", "Ethena USDe", "ethena-usde", "Crypto-backed", 2),
    StablecoinDefinition("sUSD", "sUSD", "susd", "Crypto-backed", 2),
    StablecoinDefinition("USDD", "USDD", "usdd", "Algorithmic", 2),
    StablecoinDefinition("GUSD", "Gemini Dollar", "gemini-dollar", "Centralized", 2),
    StablecoinDefinition("FDUSD", "First Digital USD", "first-digital-usd", "Centralized", 2),

    # Specialized & cross-chain assets
    StablecoinDefinition("CRVUSD", "Curve.Fi USD", "crvusd", "Decentralized", 2),
    StablecoinDefinition("EURS", "STASIS EURS", "stasis-eurs", "EUR-pegged", 2),
    StablecoinDefinition("EURT", "Tether EURt", "tether-eurt", "EUR-pegged", 2),
    StablecoinDefinition("EURC", "Circle EUR Coin", "euro-coin", "Fiat-backed", 2),
    StablecoinDefinition("USD+", "USD Plus", "usd-plus", "Crypto-backed", 2),
    StablecoinDefinition("MAI", "MAI", "mimatic", "Crypto-backed", 2),
    StablecoinDefinition("USDbC", "USD Base Coin", "bridged-usdc-base", "Stable-backed", 2),
    StablecoinDefinition("USDC.e", "Bridged USDC", "bridged-usdc", "Fiat-backed", 2),
    StablecoinDefinition("DAI.e", "Bridged DAI", "dai", "Hybrid", 2),
    StablecoinDefinition("USDT.e", "Bridged USDT", "tether", "Fiat-backed", 2),
    StablecoinDefinition("eUSD", "Electronic USD", "electronic-usd", "Crypto-backed", 2),
    StablecoinDefinition("axlUSDC", "Axelar USDC", "axlusdc", "Crypto-backed", 2),
    StablecoinDefinition("xUSD", "xUSD", "xusd", "Crypto-backed", 2),
    StablecoinDefinition("miMATIC", "miMATIC", "mimatic", "Crypto-backed", 2),
    StablecoinDefinition("orUSDC", "Origin USDC", "origin-usdc", "Fiat-backed", 2),
    StablecoinDefinition("YUSD", "YUSD", "yusd", "Crypto-backed", 2),
    StablecoinDefinition("renBTC", "renBTC", "renbtc", "Crypto-backed", 2),
    StablecoinDefinition("aUSD", "aUSD", "ausd", "Crypto-backed", 2),
    StablecoinDefinition("UST", "TerraClassicUSD", "terrausd", "Algorithmic", 2),

    # Berachain stablecoins
    StablecoinDefinition("HONEY", "Berachain HONEY", "honey", "Crypto-backed", 2),
    StablecoinDefinition("NECT", "Berachain NECT", "nect", "Crypto-backed", 2),
]

# All stablecoins combined
ALL_STABLECOINS = TIER1_STABLECOINS + TIER2_STABLECOINS

# Default tracking for free tier (Tier 1 only)
FREE_TIER_STABLECOINS = TIER1_STABLECOINS

# Premium tier gets all stablecoins
PREMIUM_TIER_STABLECOINS = ALL_STABLECOINS

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
