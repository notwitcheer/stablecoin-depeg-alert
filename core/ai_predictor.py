"""
CryptoGuard AI Prediction Engine
Advanced ML-powered depeg prediction and risk assessment system
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import asdict

from core.models import (
    RiskAssessment,
    RiskLevel,
    PredictionResult,
    SocialSentiment,
    StablecoinPeg
)


logger = logging.getLogger(__name__)


class DepegPredictor:
    """
    AI-powered depeg prediction engine combining:
    1. Time-series price analysis (LSTM)
    2. Social sentiment analysis
    3. Market volatility indicators
    4. Cross-stablecoin correlation analysis
    """

    def __init__(self):
        self.models = {}
        self.feature_weights = {
            "price_volatility_1h": 0.25,
            "price_volatility_24h": 0.20,
            "volume_anomaly": 0.15,
            "social_sentiment": 0.15,
            "market_stress": 0.10,
            "peer_correlation": 0.10,
            "treasury_risk": 0.05
        }
        self.model_version = "v1.0.0"

    async def predict_depeg_probability(
        self,
        stablecoin_symbol: str,
        historical_prices: Optional[List[float]] = None,
        current_volume: Optional[float] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        horizon: str = "24h"
    ) -> RiskAssessment:
        """
        Predict depeg probability using ensemble of ML models

        Args:
            stablecoin_symbol: Symbol like 'USDT', 'USDC'
            historical_prices: Recent price history (last 100+ data points)
            current_volume: Current 24h volume
            social_sentiment: Social media sentiment data
            horizon: Prediction timeframe ('1h', '6h', '24h')

        Returns:
            RiskAssessment with probability, confidence, and feature importance
        """
        try:
            # Handle missing data gracefully (API limitations)
            if not historical_prices:
                historical_prices = []
            if current_volume is None:
                current_volume = 0.0

            # Feature engineering
            features = await self._extract_features(
                stablecoin_symbol,
                historical_prices,
                current_volume,
                social_sentiment
            )

            # Model predictions
            time_series_risk = await self._lstm_prediction(features, horizon)
            sentiment_risk = await self._sentiment_risk_score(social_sentiment)
            volatility_risk = await self._volatility_risk_score(historical_prices)
            correlation_risk = await self._correlation_risk_score(stablecoin_symbol)

            # Ensemble prediction (weighted combination)
            risk_score = (
                time_series_risk * 0.4 +
                sentiment_risk * 0.3 +
                volatility_risk * 0.2 +
                correlation_risk * 0.1
            )

            # Calculate confidence based on data quality and model agreement
            confidence = await self._calculate_confidence(
                [time_series_risk, sentiment_risk, volatility_risk, correlation_risk]
            )

            # Determine risk level
            risk_level = self._get_risk_level(risk_score)

            # Feature importance for explainability
            contributing_factors = {
                "time_series_pattern": time_series_risk,
                "social_sentiment": sentiment_risk,
                "price_volatility": volatility_risk,
                "peer_correlation": correlation_risk,
                "data_quality_score": confidence
            }

            return RiskAssessment(
                stablecoin_symbol=stablecoin_symbol,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                prediction_horizon=horizon,
                contributing_factors=contributing_factors,
                social_sentiment_score=sentiment_risk if social_sentiment else None,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Prediction failed for {stablecoin_symbol}: {e}")
            # Return conservative high-risk assessment on failure
            return RiskAssessment(
                stablecoin_symbol=stablecoin_symbol,
                risk_score=75.0,  # Conservative high risk
                risk_level=RiskLevel.HIGH,
                confidence=0.1,  # Low confidence due to error
                prediction_horizon=horizon,
                contributing_factors={"error": str(e)},
                timestamp=datetime.utcnow()
            )

    async def _extract_features(
        self,
        symbol: str,
        prices: List[float],
        volume: float,
        sentiment: Optional[SocialSentiment]
    ) -> Dict[str, float]:
        """Extract ML features from raw data"""

        if len(prices) < 2:
            return {"insufficient_data": 1.0}

        prices_array = np.array(prices)

        # Price-based features
        returns = np.diff(prices_array) / prices_array[:-1]
        volatility_1h = np.std(returns[-60:]) if len(returns) >= 60 else np.std(returns)
        volatility_24h = np.std(returns[-1440:]) if len(returns) >= 1440 else np.std(returns)

        # Volume anomaly detection
        avg_volume = volume  # Simplified - would normally use historical average
        volume_zscore = 0.0  # Simplified calculation

        # Price deviation from $1.00
        current_price = prices[-1]
        price_deviation = abs(current_price - 1.0)

        # Trend analysis
        recent_trend = np.mean(returns[-10:]) if len(returns) >= 10 else 0.0

        features = {
            "price_deviation": price_deviation,
            "volatility_1h": volatility_1h,
            "volatility_24h": volatility_24h,
            "volume_zscore": volume_zscore,
            "price_trend": recent_trend,
            "current_price": current_price,
        }

        # Add sentiment features if available
        if sentiment:
            features.update({
                "sentiment_score": sentiment.sentiment_score / 100.0,  # Normalize to 0-1
                "mention_count_log": np.log1p(sentiment.mention_count),
                "engagement_score": sentiment.engagement_score,
                "fear_greed_index": sentiment.fear_greed_index / 100.0
            })

        return features

    async def _lstm_prediction(self, features: Dict[str, float], horizon: str) -> float:
        """
        LSTM-based time series prediction
        Simplified version - in production, this would use trained TensorFlow/PyTorch models
        """

        # Simplified heuristic-based prediction for MVP
        # In production, this would be a proper LSTM model

        price_risk = min(features.get("price_deviation", 0) * 100, 100)
        volatility_risk = min(features.get("volatility_24h", 0) * 1000, 100)
        trend_risk = abs(features.get("price_trend", 0)) * 500

        # Time horizon adjustment
        horizon_multiplier = {"1h": 0.3, "6h": 0.7, "24h": 1.0}.get(horizon, 1.0)

        lstm_risk = (price_risk * 0.5 + volatility_risk * 0.3 + trend_risk * 0.2) * horizon_multiplier

        return min(lstm_risk, 100.0)

    async def _sentiment_risk_score(self, sentiment: Optional[SocialSentiment]) -> float:
        """Calculate risk score from social sentiment"""

        if not sentiment:
            return 25.0  # Neutral risk when no sentiment data

        # Negative sentiment increases risk
        sentiment_risk = max(0, -sentiment.sentiment_score) / 100.0 * 100

        # High mention count during negative sentiment = higher risk
        if sentiment.sentiment_score < -20 and sentiment.mention_count > 100:
            sentiment_risk *= 1.5

        # Fear & greed index contribution
        if sentiment.fear_greed_index < 25:  # Extreme fear
            sentiment_risk += 20

        return min(sentiment_risk, 100.0)

    async def _volatility_risk_score(self, prices: List[float]) -> float:
        """Calculate risk based on price volatility patterns"""

        if len(prices) < 10:
            return 50.0  # Default moderate risk for insufficient data

        prices_array = np.array(prices)
        returns = np.diff(prices_array) / prices_array[:-1]

        # Recent volatility vs historical
        recent_vol = np.std(returns[-10:])
        historical_vol = np.std(returns[:-10]) if len(returns) > 20 else recent_vol

        # Volatility spike detection
        vol_ratio = recent_vol / (historical_vol + 1e-8)  # Avoid division by zero

        volatility_risk = min(vol_ratio * 30, 100)

        return volatility_risk

    async def _correlation_risk_score(self, symbol: str) -> float:
        """
        Calculate risk based on correlation with other stablecoins
        Simplified version - in production would analyze cross-stablecoin correlations
        """

        # Simplified heuristic based on stablecoin type
        high_risk_coins = ["UST", "USDD", "MIM"]  # Algorithmic stablecoins
        medium_risk_coins = ["DAI", "FRAX", "LUSD"]  # Crypto-backed

        if symbol in high_risk_coins:
            return 60.0
        elif symbol in medium_risk_coins:
            return 30.0
        else:
            return 15.0  # Centralized stablecoins (USDT, USDC)

    async def _calculate_confidence(self, model_predictions: List[float]) -> float:
        """
        Calculate prediction confidence based on model agreement
        High agreement between models = high confidence
        """

        if not model_predictions:
            return 0.1

        # Standard deviation of predictions (lower = higher agreement = higher confidence)
        std_dev = np.std(model_predictions)

        # Convert to confidence score (0-100)
        # Lower std_dev = higher confidence
        confidence = max(10, 100 - (std_dev * 2))

        return min(confidence, 100.0)

    def _get_risk_level(self, risk_score: float) -> RiskLevel:
        """Convert numerical risk score to categorical risk level"""

        if risk_score <= 25:
            return RiskLevel.LOW
        elif risk_score <= 50:
            return RiskLevel.MEDIUM
        elif risk_score <= 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    async def batch_predict(self, stablecoins_data: List[Dict]) -> List[RiskAssessment]:
        """
        Batch prediction for multiple stablecoins
        Optimized for real-time monitoring of entire portfolio
        """

        tasks = []
        for coin_data in stablecoins_data:
            task = self.predict_depeg_probability(
                coin_data["symbol"],
                coin_data["historical_prices"],
                coin_data["volume"],
                coin_data.get("social_sentiment"),
                coin_data.get("horizon", "24h")
            )
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def update_model_weights(self, feedback_data: List[Dict]) -> None:
        """
        Update model weights based on prediction accuracy feedback
        Implements online learning for continuous improvement
        """

        logger.info(f"Updating model weights with {len(feedback_data)} feedback samples")

        # Simplified weight update logic
        # In production, this would use proper online learning algorithms

        accuracy_scores = []
        for feedback in feedback_data:
            predicted_risk = feedback.get("predicted_risk", 50)
            actual_outcome = feedback.get("actual_outcome", 0)  # 0-100 scale

            # Calculate prediction accuracy
            accuracy = 1.0 - abs(predicted_risk - actual_outcome) / 100.0
            accuracy_scores.append(accuracy)

        avg_accuracy = np.mean(accuracy_scores)
        logger.info(f"Current model accuracy: {avg_accuracy:.3f}")

        # Adjust feature weights based on performance
        if avg_accuracy < 0.7:  # If accuracy is low, increase conservative weights
            self.feature_weights["price_volatility_24h"] += 0.05
            self.feature_weights["social_sentiment"] -= 0.05

        # Normalize weights
        total_weight = sum(self.feature_weights.values())
        for key in self.feature_weights:
            self.feature_weights[key] /= total_weight


class SocialSentimentAnalyzer:
    """
    Social media sentiment analysis for stablecoins
    Integrates Twitter, Reddit, and other social platforms
    """

    def __init__(self):
        self.platforms = ["twitter", "reddit", "telegram"]
        self.sentiment_cache = {}

    async def analyze_stablecoin_sentiment(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> Optional[SocialSentiment]:
        """
        Analyze social sentiment for a specific stablecoin

        Args:
            symbol: Stablecoin symbol (USDT, USDC, etc.)
            timeframe: Analysis timeframe ('1h', '6h', '24h')

        Returns:
            SocialSentiment object with aggregated sentiment metrics
        """

        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.sentiment_cache:
                cached_result, timestamp = self.sentiment_cache[cache_key]
                if datetime.utcnow() - timestamp < timedelta(minutes=15):  # 15min cache
                    return cached_result

            # Gather sentiment from multiple platforms
            twitter_sentiment = await self._analyze_twitter_sentiment(symbol, timeframe)
            reddit_sentiment = await self._analyze_reddit_sentiment(symbol, timeframe)

            # Aggregate sentiment scores
            sentiment_scores = [twitter_sentiment, reddit_sentiment]
            valid_scores = [s for s in sentiment_scores if s is not None]

            if not valid_scores:
                return None

            # Weighted aggregation (Twitter gets higher weight due to real-time nature)
            weights = [0.7, 0.3]  # Twitter, Reddit
            weighted_sentiment = sum(score * weight for score, weight in zip(valid_scores, weights))

            # Create aggregated sentiment object
            aggregated_sentiment = SocialSentiment(
                stablecoin_symbol=symbol,
                platform="aggregated",
                sentiment_score=weighted_sentiment,
                mention_count=sum(getattr(s, 'mention_count', 0) for s in valid_scores if hasattr(s, 'mention_count')),
                engagement_score=np.mean([getattr(s, 'engagement_score', 0) for s in valid_scores if hasattr(s, 'engagement_score')]),
                fear_greed_index=self._calculate_fear_greed_index(weighted_sentiment),
                timestamp=datetime.utcnow()
            )

            # Cache result
            self.sentiment_cache[cache_key] = (aggregated_sentiment, datetime.utcnow())

            return aggregated_sentiment

        except Exception as e:
            logger.error(f"Sentiment analysis failed for {symbol}: {e}")
            return None

    async def _analyze_twitter_sentiment(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Analyze Twitter sentiment for stablecoin
        In production, this would use Twitter API v2
        """

        # Simplified sentiment analysis - in production would use:
        # 1. Twitter API v2 to fetch recent tweets
        # 2. Pre-trained sentiment model (BERT, RoBERTa)
        # 3. Crypto-specific sentiment lexicon

        # For MVP, return simulated sentiment based on symbol characteristics
        risk_indicators = {
            "UST": -60,  # Known failed stablecoin
            "USDD": -30,  # Algorithmic, higher risk perception
            "DAI": 10,    # Generally positive sentiment
            "USDC": 20,   # Generally positive sentiment
            "USDT": 0,    # Neutral (mixed sentiment due to reserves questions)
        }

        base_sentiment = risk_indicators.get(symbol, 0)

        # Add some random variation to simulate real sentiment fluctuations
        import random
        sentiment_variation = random.uniform(-15, 15)

        return max(-100, min(100, base_sentiment + sentiment_variation))

    async def _analyze_reddit_sentiment(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Analyze Reddit sentiment for stablecoin
        In production, this would use Reddit API
        """

        # Simplified Reddit sentiment (typically more conservative than Twitter)
        twitter_sentiment = await self._analyze_twitter_sentiment(symbol, timeframe)

        if twitter_sentiment is None:
            return None

        # Reddit sentiment tends to be more conservative/negative
        reddit_sentiment = twitter_sentiment * 0.8 - 5

        return max(-100, min(100, reddit_sentiment))

    def _calculate_fear_greed_index(self, sentiment_score: float) -> float:
        """
        Convert sentiment score to fear/greed index (0-100)
        0 = Extreme Fear, 50 = Neutral, 100 = Extreme Greed
        """

        # Convert sentiment (-100 to +100) to fear/greed (0 to 100)
        fear_greed = (sentiment_score + 100) / 2

        return max(0, min(100, fear_greed))


# Global instances for use across the application
depeg_predictor = DepegPredictor()
sentiment_analyzer = SocialSentimentAnalyzer()