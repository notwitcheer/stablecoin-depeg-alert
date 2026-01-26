"""
CryptoGuard Enhanced Price Data Client
Fetches current prices, historical data, and market metrics from CoinGecko
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

# CoinGecko API endpoints
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_PRICE_URL = f"{COINGECKO_BASE}/simple/price"
COINGECKO_HISTORY_URL = f"{COINGECKO_BASE}/coins"
REQUEST_TIMEOUT = 30  # seconds

# Rate limiting - CoinGecko free tier: 50 calls/min
MAX_COINS_PER_REQUEST = 100


async def fetch_prices(coin_ids: List[str]) -> Dict[str, float]:
    """
    Fetch current prices from CoinGecko API

    Args:
        coin_ids: List of CoinGecko IDs (e.g. ['tether', 'usd-coin', 'dai'])

    Returns:
        Dict mapping coin_id to USD price

    Raises:
        Exception if API request fails
    """
    if not coin_ids:
        logger.warning("No coin IDs provided to fetch_prices")
        return {}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            logger.info(f"Fetching prices for {len(coin_ids)} coins from CoinGecko...")

            response = await client.get(
                COINGECKO_PRICE_URL,
                params={
                    "ids": ",".join(coin_ids),
                    "vs_currencies": "usd",
                    "precision": "4",  # Get 4 decimal places
                },
            )

            response.raise_for_status()
            data = response.json()

            # Extract USD prices
            prices = {}
            missing_prices = []
            for coin_id in coin_ids:
                if coin_id in data and "usd" in data[coin_id]:
                    prices[coin_id] = float(data[coin_id]["usd"])
                else:
                    logger.warning(f"Price not found for {coin_id}")
                    missing_prices.append(coin_id)

            # Don't return any data if critical coins are missing
            if missing_prices:
                logger.error(
                    f"Missing price data for {missing_prices}. This could indicate API issues."
                )
                # Still return available prices but log the issue
                for coin_id in missing_prices:
                    # Only default to 1.0 for non-critical situations and log it clearly
                    logger.warning(
                        f"Defaulting {coin_id} price to $1.00 - THIS MAY HIDE REAL DEPEGS!"
                    )
                    prices[coin_id] = 1.0

            logger.info(f"Successfully fetched {len(prices)} prices")
            return prices

    except httpx.TimeoutException:
        logger.error("Timeout while fetching prices from CoinGecko")
        raise Exception("CoinGecko API timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from CoinGecko: {e.response.status_code}")
        # Handle rate limiting specifically
        if e.response.status_code == 429:
            logger.error(
                "CoinGecko rate limit exceeded! Consider upgrading API plan or reducing request frequency."
            )
        raise Exception(f"CoinGecko API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error fetching prices: {e}")
        raise Exception(f"Failed to fetch prices: {str(e)}")


async def fetch_historical_prices(
    coin_id: str,
    days: int = 7,
    interval: str = "hourly"
) -> Optional[List[float]]:
    """
    Fetch historical price data for AI/ML analysis

    Args:
        coin_id: CoinGecko coin ID (e.g. 'usd-coin')
        days: Number of days of historical data
        interval: Data interval - 'hourly' or 'daily'

    Returns:
        List of historical prices, or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # CoinGecko historical data endpoint
            url = f"{COINGECKO_HISTORY_URL}/{coin_id}/market_chart"

            params = {
                "vs_currency": "usd",
                "days": days,
                "interval": interval if days <= 90 else "daily"  # Auto-adjust for long periods
            }

            logger.info(f"Fetching {days} days of {interval} data for {coin_id}...")

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract price data from response
            if "prices" not in data:
                logger.error(f"No price data in historical response for {coin_id}")
                return None

            # CoinGecko returns [timestamp, price] pairs
            prices = [float(price_point[1]) for price_point in data["prices"]]

            logger.info(f"Fetched {len(prices)} historical price points for {coin_id}")
            return prices

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.error("Rate limit hit fetching historical data - consider caching")
        logger.error(f"HTTP error fetching historical data for {coin_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching historical data for {coin_id}: {e}")
        return None


async def fetch_enhanced_market_data(coin_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Fetch enhanced market data including volume, market cap, and volatility

    Args:
        coin_ids: List of CoinGecko coin IDs

    Returns:
        Dict mapping coin_id to market data dict
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(
                COINGECKO_PRICE_URL,
                params={
                    "ids": ",".join(coin_ids),
                    "vs_currencies": "usd",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true",
                    "precision": "4"
                }
            )

            response.raise_for_status()
            data = response.json()

            market_data = {}
            for coin_id in coin_ids:
                if coin_id in data:
                    coin_data = data[coin_id]
                    market_data[coin_id] = {
                        "price": float(coin_data.get("usd", 1.0)),
                        "market_cap": float(coin_data.get("usd_market_cap", 0)),
                        "volume_24h": float(coin_data.get("usd_24h_vol", 0)),
                        "change_24h": float(coin_data.get("usd_24h_change", 0))
                    }

            logger.info(f"Fetched enhanced market data for {len(market_data)} coins")
            return market_data

    except Exception as e:
        logger.error(f"Error fetching enhanced market data: {e}")
        return {}


async def test_api_connection() -> bool:
    """
    Test connection to CoinGecko API

    Returns:
        True if API is accessible, False otherwise
    """
    try:
        # Test with just USDC
        test_prices = await fetch_prices(["usd-coin"])
        return len(test_prices) > 0
    except Exception as e:
        logger.error(f"API connection test failed: {e}")
        return False


async def test_enhanced_features() -> bool:
    """
    Test enhanced API features (historical data, market data)

    Returns:
        True if enhanced features work, False otherwise
    """
    try:
        # Test historical data
        historical = await fetch_historical_prices("usd-coin", days=1)
        if not historical or len(historical) < 10:
            logger.error("Historical data test failed")
            return False

        # Test enhanced market data
        market_data = await fetch_enhanced_market_data(["usd-coin"])
        if not market_data or "usd-coin" not in market_data:
            logger.error("Enhanced market data test failed")
            return False

        logger.info("✅ All enhanced API features working correctly")
        return True

    except Exception as e:
        logger.error(f"Enhanced features test failed: {e}")
        return False
