"""
CryptoGuard Enhanced Peg Checker - AI-Powered Risk Assessment
Evolved from basic peg checking to comprehensive risk monitoring with ML predictions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from core.models import PegStatus, StablecoinPeg, SubscriptionTier
from core.prices import fetch_prices, fetch_historical_prices
from core.stablecoins import FREE_TIER_STABLECOINS, PREMIUM_TIER_STABLECOINS, get_coingecko_ids
from core.ai_predictor import depeg_predictor, sentiment_analyzer

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


async def check_all_pegs(
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE,
    include_ai_predictions: bool = True,
    include_social_sentiment: bool = True
) -> List[StablecoinPeg]:
    """
    Enhanced peg checking with AI predictions and risk assessment

    Args:
        subscription_tier: User subscription level (affects which coins to check)
        include_ai_predictions: Whether to include AI risk assessment
        include_social_sentiment: Whether to include social media sentiment

    Returns:
        List of StablecoinPeg objects with enhanced data
    """
    try:
        # Select stablecoins based on subscription tier
        if subscription_tier == SubscriptionTier.FREE:
            stablecoins = FREE_TIER_STABLECOINS
        else:
            stablecoins = PREMIUM_TIER_STABLECOINS

        coin_ids = get_coingecko_ids(stablecoins)
        logger.info(f"Checking {len(stablecoins)} stablecoins for {subscription_tier.value} tier...")

        # Fetch current prices and volume data
        prices = await fetch_prices(coin_ids)
        if not prices:
            logger.error("No price data received")
            return []

        # Batch process all coins for efficiency
        tasks = []
        for stable in stablecoins:
            task = _enhanced_peg_check(
                stable,
                prices,
                include_ai_predictions,
                include_social_sentiment
            )
            tasks.append(task)

        # Execute all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed results and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to check {stablecoins[i].symbol}: {result}")
            else:
                valid_results.append(result)

        # Enhanced logging with risk levels
        stable_count = sum(1 for p in valid_results if p.status == PegStatus.STABLE)
        high_risk_count = sum(
            1 for p in valid_results
            if p.risk_assessment and p.risk_assessment.risk_level.value in ['high', 'critical']
        )

        logger.info(
            f"Enhanced peg check complete: {stable_count}/{len(valid_results)} stable, "
            f"{high_risk_count} high-risk detected"
        )

        return valid_results

    except Exception as e:
        logger.error(f"Error in enhanced peg checking: {e}")
        return []


async def _enhanced_peg_check(
    stable_def,
    prices: Dict[str, float],
    include_ai: bool,
    include_sentiment: bool
) -> StablecoinPeg:
    """
    Enhanced individual stablecoin check with AI and sentiment analysis
    """
    price = prices.get(stable_def.coingecko_id, 1.0)
    deviation = calculate_deviation(price)
    status = get_status(deviation)

    # Start with basic peg object
    peg = StablecoinPeg(
        symbol=stable_def.symbol,
        name=stable_def.name,
        coingecko_id=stable_def.coingecko_id,
        price=Decimal(str(price)),
        deviation_percent=deviation,
        status=status,
        last_updated=datetime.utcnow(),
    )

    # Add enhanced features if requested
    try:
        # Fetch historical data for AI analysis
        if include_ai:
            historical_prices = await fetch_historical_prices(
                stable_def.coingecko_id,
                days=7  # Last week for trend analysis
            )

            # Get social sentiment if enabled
            social_sentiment = None
            if include_sentiment:
                social_sentiment = await sentiment_analyzer.analyze_stablecoin_sentiment(
                    stable_def.symbol
                )
                peg.social_sentiment = social_sentiment

            # AI risk assessment
            if historical_prices:
                risk_assessment = await depeg_predictor.predict_depeg_probability(
                    stable_def.symbol,
                    historical_prices,
                    current_volume=price * 1000000,  # Simplified volume calculation
                    social_sentiment=social_sentiment
                )
                peg.risk_assessment = risk_assessment

                # Enhanced logging for high-risk coins
                if risk_assessment.risk_level.value in ['high', 'critical']:
                    logger.warning(
                        f"🚨 {stable_def.symbol} HIGH RISK: "
                        f"AI Risk={risk_assessment.risk_score:.1f}, "
                        f"Price=${price:.4f} ({deviation:+.2f}%), "
                        f"Confidence={risk_assessment.confidence:.1f}%"
                    )

    except Exception as e:
        logger.error(f"Enhanced analysis failed for {stable_def.symbol}: {e}")
        # Continue with basic peg data even if enhanced features fail

    return peg


async def check_specific_peg(symbol: str) -> Optional[StablecoinPeg]:
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
            last_updated=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error checking peg for {symbol}: {e}")
        raise
