"""
Resilience and Error Handling System
Provides retry logic, circuit breakers, and graceful degradation
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Any, Dict, List
from functools import wraps
import json

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered

class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential"
    FIXED_DELAY = "fixed"
    LINEAR_BACKOFF = "linear"

class CircuitBreaker:
    """Circuit breaker implementation for external service calls"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception: tuple = (Exception,)):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker half-open for {func.__name__}")
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker open for {func.__name__}")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    async def acall(self, func: Callable, *args, **kwargs):
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker half-open for {func.__name__}")
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker open for {func.__name__}")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if self.last_failure_time is None:
            return True
        return datetime.utcnow() >= self.last_failure_time + timedelta(seconds=self.recovery_timeout)

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(self, max_attempts: int = 3, strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                 base_delay: float = 1.0, max_delay: float = 60.0, backoff_multiplier: float = 2.0,
                 retry_exceptions: tuple = (Exception,), stop_exceptions: tuple = ()):
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.retry_exceptions = retry_exceptions
        self.stop_exceptions = stop_exceptions

def with_retry(config: RetryConfig):
    """Decorator for adding retry logic to functions"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except config.stop_exceptions as e:
                    logger.error(f"Stop exception in {func.__name__}: {e}")
                    raise e

                except config.retry_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"All retry attempts failed for {func.__name__}: {e}")
                        break

                    delay = _calculate_delay(config, attempt)
                    logger.warning(f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s")

                    await asyncio.sleep(delay)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)

                except config.stop_exceptions as e:
                    logger.error(f"Stop exception in {func.__name__}: {e}")
                    raise e

                except config.retry_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"All retry attempts failed for {func.__name__}: {e}")
                        break

                    delay = _calculate_delay(config, attempt)
                    logger.warning(f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s")

                    time.sleep(delay)

            raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

def _calculate_delay(config: RetryConfig, attempt: int) -> float:
    """Calculate delay for retry attempt"""
    if config.strategy == RetryStrategy.FIXED_DELAY:
        return config.base_delay
    elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
        return min(config.base_delay * (attempt + 1), config.max_delay)
    elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
        return min(config.base_delay * (config.backoff_multiplier ** attempt), config.max_delay)
    else:
        return config.base_delay

class FallbackManager:
    """Manages fallback strategies when primary services fail"""

    def __init__(self):
        self.fallback_data = {}
        self.last_update = {}

    def set_fallback_data(self, key: str, data: Any):
        """Store fallback data"""
        self.fallback_data[key] = data
        self.last_update[key] = datetime.utcnow()
        logger.info(f"Stored fallback data for {key}")

    def get_fallback_data(self, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
        """Get fallback data if it's fresh enough"""
        if key not in self.fallback_data:
            return None

        age = (datetime.utcnow() - self.last_update[key]).total_seconds()
        if age > max_age_seconds:
            logger.warning(f"Fallback data for {key} is too old ({age}s)")
            return None

        logger.info(f"Using fallback data for {key} (age: {age}s)")
        return self.fallback_data[key]

# Global instances
circuit_breakers: Dict[str, CircuitBreaker] = {}
fallback_manager = FallbackManager()

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker"""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(**kwargs)
    return circuit_breakers[name]

# Custom Exceptions
class ResilienceError(Exception):
    """Base exception for resilience module"""
    pass

class CircuitBreakerOpenError(ResilienceError):
    """Raised when circuit breaker is open"""
    pass

class RetryExhaustedException(ResilienceError):
    """Raised when all retry attempts are exhausted"""
    pass

# Pre-configured retry configurations
API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,
    max_delay=10.0,
    retry_exceptions=(ConnectionError, TimeoutError, Exception),
    stop_exceptions=(ValueError, KeyError)
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=0.5,
    max_delay=5.0,
    retry_exceptions=(ConnectionError, Exception)
)

TELEGRAM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=2.0,
    max_delay=30.0,
    retry_exceptions=(Exception,)
)

# Health monitoring
class HealthStatus:
    """Track service health status"""

    def __init__(self):
        self.services = {}

    def update_service_status(self, service: str, is_healthy: bool, details: str = ""):
        """Update service health status"""
        self.services[service] = {
            "healthy": is_healthy,
            "details": details,
            "last_check": datetime.utcnow(),
        }

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        healthy_services = sum(1 for s in self.services.values() if s["healthy"])
        total_services = len(self.services)

        return {
            "healthy": total_services > 0 and healthy_services == total_services,
            "services": self.services,
            "healthy_count": healthy_services,
            "total_count": total_services,
            "timestamp": datetime.utcnow()
        }

# Global health status
health_status = HealthStatus()

# Monitoring decorators
def monitor_service_health(service_name: str):
    """Decorator to monitor service health"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                health_status.update_service_status(service_name, True, "OK")
                return result
            except Exception as e:
                health_status.update_service_status(service_name, False, str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                health_status.update_service_status(service_name, True, "OK")
                return result
            except Exception as e:
                health_status.update_service_status(service_name, False, str(e))
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator

# Graceful degradation utilities
class DegradationLevel(Enum):
    """Levels of service degradation"""
    NORMAL = "normal"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    EMERGENCY = "emergency"

degradation_level = DegradationLevel.NORMAL

def set_degradation_level(level: DegradationLevel):
    """Set current degradation level"""
    global degradation_level
    degradation_level = level
    logger.warning(f"System degradation level set to: {level.value}")

def get_degradation_level() -> DegradationLevel:
    """Get current degradation level"""
    return degradation_level

def should_skip_non_essential_operations() -> bool:
    """Check if non-essential operations should be skipped"""
    return degradation_level in [DegradationLevel.MINIMAL, DegradationLevel.EMERGENCY]