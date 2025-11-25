"""Circuit Breaker - Prevent cascading failures.

Implements the circuit breaker pattern to prevent cascading failures
in distributed systems by failing fast when a service is unhealthy.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Callable, TypeVar, Optional
import time
import logging
from functools import wraps


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests pass through
    OPEN = "open"          # Fail fast - requests immediately fail
    HALF_OPEN = "half_open"  # Testing recovery - limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold_for_recovery: int = 2  # Successes needed to close from half-open
    timeout_seconds: float = 60.0  # Time before attempting recovery
    name: str = "circuit_breaker"


T = TypeVar('T')


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Prevent cascading failures with circuit breaker pattern.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, no requests allowed (after threshold failures)
    - HALF_OPEN: Testing if service recovered (after timeout)
    """

    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float = 0
        self._logger = logging.getLogger(__name__)

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from func
        """
        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.timeout_seconds:
                self._logger.info(f"[{self.config.name}] Transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.config.name}' is OPEN"
                )

        # Attempt the call
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self._logger.info(
                f"[{self.config.name}] Success in HALF_OPEN "
                f"({self.success_count}/{self.config.success_threshold_for_recovery})"
            )

            if self.success_count >= self.config.success_threshold_for_recovery:
                self._logger.info(f"[{self.config.name}] Transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.last_failure_time = time.time()
        self.failure_count += 1

        self._logger.warning(
            f"[{self.config.name}] Failure count: "
            f"{self.failure_count}/{self.config.failure_threshold}"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately opens circuit
            self._logger.warning(f"[{self.config.name}] Failure in HALF_OPEN, opening circuit")
            self.state = CircuitState.OPEN
            self.failure_count = 0
        elif self.failure_count >= self.config.failure_threshold:
            self._logger.error(f"[{self.config.name}] Threshold exceeded, opening circuit")
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self._logger.info(f"[{self.config.name}] Manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with current stats
        """
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'config': {
                'name': self.config.name,
                'failure_threshold': self.config.failure_threshold,
                'success_threshold': self.config.success_threshold_for_recovery,
                'timeout_seconds': self.config.timeout_seconds,
            }
        }

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator usage for circuit breaker.

        Example:
            breaker = CircuitBreaker(config)

            @breaker
            def my_function():
                # ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper
