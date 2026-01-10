"""
Health Check and Monitoring System
Provides HTTP endpoints for system health, metrics, and status monitoring
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from core.database import DatabaseManager, get_db_session
from core.db_models import AlertHistory, StablecoinPrice, SystemMetric, User
from core.prices import test_api_connection
from core.resilience import get_degradation_level, health_status

logger = logging.getLogger(__name__)

# Prometheus Metrics
request_counter = Counter(
    "depeg_requests_total", "Total requests", ["endpoint", "status"]
)
response_time = Histogram("depeg_response_time_seconds", "Response time", ["endpoint"])
active_users = Gauge("depeg_active_users", "Number of active users")
alerts_sent = Counter(
    "depeg_alerts_sent_total", "Total alerts sent", ["symbol", "tier"]
)
price_checks = Counter("depeg_price_checks_total", "Total price checks", ["status"])
system_health = Gauge(
    "depeg_system_health", "System health status (1=healthy, 0=unhealthy)"
)


class HealthChecker:
    """Performs comprehensive health checks"""

    @staticmethod
    async def check_database() -> Dict[str, Any]:
        """Check database connectivity and performance"""
        start_time = time.time()

        try:
            # Test basic connectivity
            is_connected = DatabaseManager.test_connection()

            # Test query performance
            with get_db_session() as session:
                user_count = session.query(User).count()

            response_time = time.time() - start_time

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "response_time_ms": round(response_time * 1000, 2),
                "user_count": user_count if is_connected else None,
                "details": (
                    "Database operational"
                    if is_connected
                    else "Database connection failed"
                ),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e),
                "details": "Database check failed",
            }

    @staticmethod
    async def check_api_services() -> Dict[str, Any]:
        """Check external API services"""
        start_time = time.time()

        try:
            # Test CoinGecko API
            is_api_healthy = await test_api_connection()
            response_time = time.time() - start_time

            return {
                "status": "healthy" if is_api_healthy else "unhealthy",
                "coingecko_api": is_api_healthy,
                "response_time_ms": round(response_time * 1000, 2),
                "details": (
                    "API services operational"
                    if is_api_healthy
                    else "API services degraded"
                ),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "coingecko_api": False,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "error": str(e),
                "details": "API health check failed",
            }

    @staticmethod
    def check_system_resources() -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Determine health based on resource usage
            is_healthy = cpu_percent < 80 and memory.percent < 85 and disk.percent < 90

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "details": (
                    "System resources optimal"
                    if is_healthy
                    else "High resource usage detected"
                ),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Resource check failed",
            }

    @staticmethod
    async def get_comprehensive_health() -> Dict[str, Any]:
        """Get comprehensive system health status"""
        checks = await asyncio.gather(
            HealthChecker.check_database(),
            HealthChecker.check_api_services(),
            return_exceptions=True,
        )

        db_health, api_health = checks[0], checks[1]
        resource_health = HealthChecker.check_system_resources()

        # Handle any exceptions
        if isinstance(db_health, Exception):
            db_health = {"status": "unhealthy", "error": str(db_health)}
        if isinstance(api_health, Exception):
            api_health = {"status": "unhealthy", "error": str(api_health)}

        # Overall health determination
        all_healthy = all(
            check["status"] == "healthy"
            for check in [db_health, api_health, resource_health]
        )

        # Get degradation level
        degradation = get_degradation_level()

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "degradation_level": degradation.value,
            "checks": {
                "database": db_health,
                "api_services": api_health,
                "system_resources": resource_health,
                "circuit_breakers": health_status.get_overall_health(),
            },
            "uptime_seconds": time.time() - start_time_global,
        }


class MetricsCollector:
    """Collects and aggregates system metrics"""

    @staticmethod
    async def collect_user_metrics() -> Dict[str, Any]:
        """Collect user-related metrics"""
        try:
            with get_db_session() as session:
                # Basic counts
                total_users = session.query(User).count()
                active_users_count = (
                    session.query(User)
                    .filter(
                        User.last_active
                        >= datetime.now(timezone.utc) - timedelta(days=30)
                    )
                    .count()
                )

                # Tier distribution
                from core.db_models import UserTier

                free_users = (
                    session.query(User).filter(User.tier == UserTier.FREE).count()
                )
                premium_users = (
                    session.query(User).filter(User.tier == UserTier.PREMIUM).count()
                )
                enterprise_users = (
                    session.query(User).filter(User.tier == UserTier.ENTERPRISE).count()
                )

                # Update Prometheus metrics
                active_users.set(active_users_count)

                return {
                    "total_users": total_users,
                    "active_users": active_users_count,
                    "tier_distribution": {
                        "free": free_users,
                        "premium": premium_users,
                        "enterprise": enterprise_users,
                    },
                }

        except Exception as e:
            logger.error(f"Failed to collect user metrics: {e}")
            return {"error": str(e)}

    @staticmethod
    async def collect_alert_metrics() -> Dict[str, Any]:
        """Collect alert-related metrics"""
        try:
            with get_db_session() as session:
                now = datetime.now(timezone.utc)
                last_24h = now - timedelta(hours=24)
                last_7d = now - timedelta(days=7)

                # Alert counts
                alerts_24h = (
                    session.query(AlertHistory)
                    .filter(AlertHistory.created_at >= last_24h)
                    .count()
                )

                alerts_7d = (
                    session.query(AlertHistory)
                    .filter(AlertHistory.created_at >= last_7d)
                    .count()
                )

                # Alert by status
                from core.db_models import AlertStatus

                sent_alerts = (
                    session.query(AlertHistory)
                    .filter(
                        AlertHistory.alert_status == AlertStatus.SENT,
                        AlertHistory.created_at >= last_24h,
                    )
                    .count()
                )

                failed_alerts = (
                    session.query(AlertHistory)
                    .filter(
                        AlertHistory.alert_status == AlertStatus.FAILED,
                        AlertHistory.created_at >= last_24h,
                    )
                    .count()
                )

                return {
                    "alerts_24h": alerts_24h,
                    "alerts_7d": alerts_7d,
                    "success_rate_24h": (sent_alerts / max(alerts_24h, 1)) * 100,
                    "failed_alerts_24h": failed_alerts,
                }

        except Exception as e:
            logger.error(f"Failed to collect alert metrics: {e}")
            return {"error": str(e)}

    @staticmethod
    async def collect_price_metrics() -> Dict[str, Any]:
        """Collect price monitoring metrics"""
        try:
            with get_db_session() as session:
                now = datetime.now(timezone.utc)
                last_24h = now - timedelta(hours=24)

                # Price check counts
                price_checks_24h = (
                    session.query(StablecoinPrice)
                    .filter(StablecoinPrice.timestamp >= last_24h)
                    .count()
                )

                # Depeg events
                depeg_events = (
                    session.query(StablecoinPrice)
                    .filter(
                        StablecoinPrice.timestamp >= last_24h,
                        StablecoinPrice.status.in_(["depeg", "critical"]),
                    )
                    .count()
                )

                return {
                    "price_checks_24h": price_checks_24h,
                    "depeg_events_24h": depeg_events,
                    "check_frequency_minutes": 1440 / max(price_checks_24h, 1),
                }

        except Exception as e:
            logger.error(f"Failed to collect price metrics: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_all_metrics() -> Dict[str, Any]:
        """Get all system metrics"""
        metrics = await asyncio.gather(
            MetricsCollector.collect_user_metrics(),
            MetricsCollector.collect_alert_metrics(),
            MetricsCollector.collect_price_metrics(),
            return_exceptions=True,
        )

        user_metrics, alert_metrics, price_metrics = metrics

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "users": (
                user_metrics
                if not isinstance(user_metrics, Exception)
                else {"error": str(user_metrics)}
            ),
            "alerts": (
                alert_metrics
                if not isinstance(alert_metrics, Exception)
                else {"error": str(alert_metrics)}
            ),
            "prices": (
                price_metrics
                if not isinstance(price_metrics, Exception)
                else {"error": str(price_metrics)}
            ),
        }


# HTTP Endpoint Functions (for integration with web framework)
async def health_endpoint() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return await HealthChecker.get_comprehensive_health()


async def metrics_endpoint() -> str:
    """Prometheus metrics endpoint"""
    # Update system health metric
    health = await HealthChecker.get_comprehensive_health()
    system_health.set(1 if health["status"] == "healthy" else 0)

    return generate_latest()


async def status_endpoint() -> Dict[str, Any]:
    """Detailed system status endpoint"""
    health = await HealthChecker.get_comprehensive_health()
    metrics = await MetricsCollector.get_all_metrics()

    return {
        "health": health,
        "metrics": metrics,
        "version": "2.0.0",
        "environment": "production",
    }


async def ready_endpoint() -> Dict[str, Any]:
    """Kubernetes readiness probe"""
    health = await HealthChecker.get_comprehensive_health()
    return {"ready": health["status"] == "healthy", "timestamp": health["timestamp"]}


async def live_endpoint() -> Dict[str, Any]:
    """Kubernetes liveness probe"""
    # Simple liveness check - just return if the process is running
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": time.time() - start_time_global,
    }


# System startup tracking
start_time_global = time.time()


# Monitoring utility functions
def record_system_metric(
    metric_name: str, value: float, unit: str = "count", tags: Dict = None
):
    """Record a system metric to the database"""
    try:
        with get_db_session() as session:
            metric = SystemMetric(
                metric_name=metric_name,
                metric_value=value,
                metric_unit=unit,
                tags=tags or {},
            )
            session.add(metric)
            session.commit()
    except Exception as e:
        logger.error(f"Failed to record metric {metric_name}: {e}")


def update_prometheus_metrics():
    """Update Prometheus metrics with current values"""
    try:
        # This function can be called periodically to update gauges
        # Implementation depends on your specific metrics needs
        pass
    except Exception as e:
        logger.error(f"Failed to update Prometheus metrics: {e}")


class PerformanceMonitor:
    """Monitor performance of key operations"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time

            # Record to Prometheus
            response_time.labels(endpoint=self.operation_name).observe(duration)

            # Record to database
            record_system_metric(f"{self.operation_name}_duration", duration, "seconds")

            # Log if slow
            if duration > 5.0:  # 5 second threshold
                logger.warning(
                    f"Slow operation detected: {self.operation_name} took {duration:.2f}s"
                )


# Usage example:
# with PerformanceMonitor("price_check"):
#     await check_all_pegs()


def setup_monitoring():
    """Initialize monitoring system"""
    logger.info("Setting up monitoring system...")

    # Record startup metric
    record_system_metric("system_startup", 1, "event")

    logger.info("Monitoring system initialized")


if __name__ == "__main__":
    # Test monitoring functions
    import asyncio

    async def test_monitoring():
        print("Testing health checks...")
        health = await health_endpoint()
        print(f"Health: {health['status']}")

        print("\nTesting metrics...")
        metrics = await MetricsCollector.get_all_metrics()
        print(f"User metrics: {metrics.get('users', {})}")

        print("\nMonitoring test complete!")

    asyncio.run(test_monitoring())
