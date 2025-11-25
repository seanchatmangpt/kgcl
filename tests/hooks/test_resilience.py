"""Tests for resilience module (Circuit Breaker)."""

import pytest
import time
from kgcl.hooks.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerError
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold_for_recovery == 2
        assert config.timeout_seconds == 60.0
        assert config.name == "circuit_breaker"

    def test_custom_config(self):
        """Test custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold_for_recovery=1,
            timeout_seconds=30.0,
            name="test_breaker"
        )
        assert config.failure_threshold == 3
        assert config.success_threshold_for_recovery == 1
        assert config.timeout_seconds == 30.0
        assert config.name == "test_breaker"


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initial_state(self):
        """Test initial circuit breaker state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    def test_successful_call(self):
        """Test successful function call."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)

        def successful_func():
            return "success"

        result = breaker.call(successful_func)
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    def test_successful_call_with_args(self):
        """Test successful call with arguments."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)

        def add(a, b):
            return a + b

        result = breaker.call(add, 2, 3)
        assert result == 5

    def test_successful_call_with_kwargs(self):
        """Test successful call with keyword arguments."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}"

        result = breaker.call(greet, name="Alice", greeting="Hi")
        assert result == "Hi, Alice"

    def test_failed_call_increments_counter(self):
        """Test that failed call increments failure counter."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        def failing_func():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            breaker.call(failing_func)

        assert breaker.failure_count == 1
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        def failing_func():
            raise RuntimeError("Test error")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        assert breaker.get_state() == CircuitState.OPEN

    def test_open_circuit_raises_breaker_error(self):
        """Test that open circuit raises CircuitBreakerError."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(config)

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)

        assert breaker.get_state() == CircuitState.OPEN

        # Subsequent calls should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError, match="is OPEN"):
            breaker.call(lambda: "test")

    def test_half_open_after_timeout(self):
        """Test transition to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.1  # Short timeout for testing
        )
        breaker = CircuitBreaker(config)

        def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Next call should transition to HALF_OPEN
        def successful_func():
            return "success"

        result = breaker.call(successful_func)
        assert result == "success"
        # After first success in HALF_OPEN, still in HALF_OPEN
        # (needs success_threshold_for_recovery successes)

    def test_recovery_from_half_open(self):
        """Test recovery from HALF_OPEN to CLOSED."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold_for_recovery=2,
            timeout_seconds=0.1
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        with pytest.raises(ZeroDivisionError):
            breaker.call(lambda: 1/0)

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Succeed twice to recover
        for _ in range(2):
            result = breaker.call(lambda: "success")
            assert result == "success"

        # Should be CLOSED now
        assert breaker.get_state() == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        """Test that failure in HALF_OPEN reopens circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.1
        )
        breaker = CircuitBreaker(config)

        # Open the circuit
        with pytest.raises(ZeroDivisionError):
            breaker.call(lambda: 1/0)

        # Wait for timeout
        time.sleep(0.15)

        # Fail in HALF_OPEN
        with pytest.raises(ZeroDivisionError):
            breaker.call(lambda: 1/0)

        # Should be OPEN again
        assert breaker.get_state() == CircuitState.OPEN

    def test_reset(self):
        """Test manual reset of circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(config)

        # Open the circuit
        with pytest.raises(ZeroDivisionError):
            breaker.call(lambda: 1/0)

        assert breaker.get_state() == CircuitState.OPEN

        # Reset
        breaker.reset()
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    def test_get_stats(self):
        """Test getting circuit breaker statistics."""
        config = CircuitBreakerConfig(
            name="test_breaker",
            failure_threshold=5
        )
        breaker = CircuitBreaker(config)

        stats = breaker.get_stats()
        assert stats['state'] == CircuitState.CLOSED.value
        assert stats['failure_count'] == 0
        assert stats['success_count'] == 0
        assert stats['config']['name'] == "test_breaker"
        assert stats['config']['failure_threshold'] == 5

    def test_decorator_usage(self):
        """Test using circuit breaker as decorator."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)

        @breaker
        def my_function(x):
            return x * 2

        result = my_function(5)
        assert result == 10

    def test_decorator_with_failures(self):
        """Test decorator with failing function."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        @breaker
        def failing_function():
            raise ValueError("Test error")

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        assert breaker.get_state() == CircuitState.OPEN

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_function()

    def test_success_resets_failure_count(self):
        """Test that success resets failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        # Fail twice
        for _ in range(2):
            with pytest.raises(ZeroDivisionError):
                breaker.call(lambda: 1/0)

        assert breaker.failure_count == 2

        # Succeed once
        breaker.call(lambda: "success")

        # Failure count should be reset
        assert breaker.failure_count == 0
        assert breaker.get_state() == CircuitState.CLOSED
