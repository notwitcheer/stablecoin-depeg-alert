"""
Peg Deviation Calculation Logic
Core logic for determining stablecoin peg status
"""
import logging
from datetime import datetime
from typing import List

from core.models import StablecoinPeg, PegStatus
from core.prices import fetch_prices
from core.stablecoins import FREE_TIER_STABLECOINS, get_coingecko_ids

logger = logging.getLogger(__name__)

def calculate_deviation(price: float, peg: float = 1.0) -> float:
    """
    Calculate percentage deviation from peg

    Args:
        price: Current price
        peg: Target peg price (default $1.00)

    Returns:
        Percentage deviation from peg
    """
    if peg == 0:
        return 0.0
    return ((price - peg) / peg) * 100

def get_status(deviation: float) -> PegStatus:
    """
    Determine peg status based on deviation percentage

    Args:
        deviation: Percentage deviation from peg

    Returns:
        PegStatus enum value
    """
    abs_dev = abs(deviation)
    if abs_dev < 0.2:
        return PegStatus.STABLE
    elif abs_dev < 0.5:
        return PegStatus.WARNING
    elif abs_dev < 2.0:
        return PegStatus.DEPEG
    else:
        return PegStatus.CRITICAL

async def check_all_pegs() -> List[StablecoinPeg]:
    """
    Check peg status for all tracked stablecoins

    Returns:
        List of StablecoinPeg objects with current status
    """
    try:
        # Use free tier stablecoins for now (Tier 1 + Tier 2)
        stablecoins = FREE_TIER_STABLECOINS
        coin_ids = get_coingecko_ids(stablecoins)

        logger.info(f"Checking pegs for {len(stablecoins)} stablecoins...")

        # Fetch current prices
        prices = await fetch_prices(coin_ids)

        if not prices:
            logger.error("No price data received")
            return []

        # Calculate peg status for each stablecoin
        results = []
        for stable in stablecoins:
            price = prices.get(stable.coingecko_id, 1.0)
            deviation = calculate_deviation(price)
            status = get_status(deviation)

            peg = StablecoinPeg(
                symbol=stable.symbol,
                name=stable.name,
                coingecko_id=stable.coingecko_id,
                price=price,
                deviation_percent=deviation,
                status=status,
                last_updated=datetime.utcnow()
            )

            results.append(peg)

            # Log significant deviations
            if status != PegStatus.STABLE:
                logger.warning(f"{stable.symbol} deviation: {deviation:+.2f}% (${price:.4f}) - Status: {status.value}")

        # Summary log
        stable_count = sum(1 for p in results if p.status == PegStatus.STABLE)
        logger.info(f"Peg check complete: {stable_count}/{len(results)} stable")

        return results

    except Exception as e:
        logger.error(f"Error checking pegs: {e}")
        return []

async def check_specific_peg(symbol: str) -> StablecoinPeg:
    """
    Check peg status for a specific stablecoin

    Args:
        symbol: Stablecoin symbol (e.g. 'USDC')

    Returns:
        StablecoinPeg object or None if not found

    Raises:
        Exception if stablecoin not found or API error
    """
    from core.stablecoins import get_stablecoin_by_symbol

    # Find stablecoin definition
    stable_def = get_stablecoin_by_symbol(symbol)
    if not stable_def:
        raise Exception(f"Stablecoin {symbol} not found")

    try:
        # Fetch price for this specific coin
        prices = await fetch_prices([stable_def.coingecko_id])
        price = prices.get(stable_def.coingecko_id, 1.0)

        # Calculate status
        deviation = calculate_deviation(price)
        status = get_status(deviation)

        return StablecoinPeg(
            symbol=stable_def.symbol,
            name=stable_def.name,
            coingecko_id=stable_def.coingecko_id,
            price=price,
            deviation_percent=deviation,
            status=status,
            last_updated=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Error checking peg for {symbol}: {e}")
        raise