"""
CoinGecko API Client for Fetching Stablecoin Prices
Free tier: 50 calls/min - we only need 1 call/min
"""
import httpx
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
REQUEST_TIMEOUT = 30  # seconds

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
                COINGECKO_URL,
                params={
                    "ids": ",".join(coin_ids),
                    "vs_currencies": "usd",
                    "precision": "4"  # Get 4 decimal places
                }
            )

            response.raise_for_status()
            data = response.json()

            # Extract USD prices
            prices = {}
            for coin_id in coin_ids:
                if coin_id in data and "usd" in data[coin_id]:
                    prices[coin_id] = float(data[coin_id]["usd"])
                else:
                    logger.warning(f"Price not found for {coin_id}")
                    # Default to $1.00 if price not available (assume stable)
                    prices[coin_id] = 1.0

            logger.info(f"Successfully fetched {len(prices)} prices")
            return prices

    except httpx.TimeoutException:
        logger.error("Timeout while fetching prices from CoinGecko")
        raise Exception("CoinGecko API timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from CoinGecko: {e.response.status_code}")
        raise Exception(f"CoinGecko API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error fetching prices: {e}")
        raise Exception(f"Failed to fetch prices: {str(e)}")

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