"""Circuit Breaker - Research Mode (Pass-through).

Simplified for research: no circuit logic, direct execution.
Production systems should use full circuit breaker pattern.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, TypeVar


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Fail fast (not used in research mode)
    HALF_OPEN = "half_open"  # Testing recovery (not used in research mode)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration (research: ignored)."""

    failure_threshold: int = 5
    success_threshold_for_recovery: int = 2
    timeout_seconds: float = 60.0
    name: str = "circuit_breaker"


T = TypeVar("T")


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open (never in research mode)."""

    def __init__(self, circuit_name: str, state: CircuitState) -> None:
        self.circuit_name = circuit_name
        self.state = state
        super().__init__(f"Circuit breaker '{circuit_name}' is {state.value}")


class CircuitBreaker:
    """Pass-through circuit breaker for research.

    In production, this would track failures and open the circuit.
    For research, we always pass through directly.
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self.config = config
        self.state = CircuitState.CLOSED  # Always closed in research mode
        self.failure_count = 0
        self.success_count = 0

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function directly (no circuit logic for research)."""
        return func(*args, **kwargs)

    def reset(self) -> None:
        """Reset (no-op for research)."""
        self.failure_count = 0
        self.success_count = 0

    def get_state(self) -> CircuitState:
        """Always returns CLOSED for research."""
        return CircuitState.CLOSED

    def get_stats(self) -> dict[str, Any]:
        """Get stats (minimal for research)."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "config": {"name": self.config.name},
        }

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator: pass-through for research."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        return wrapper
