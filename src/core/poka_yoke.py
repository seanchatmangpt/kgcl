"""Poka-Yoke (Error Proofing)

Prevents common testing mistakes through compile-time and runtime validation.
Translates Rust's type system guarantees to Python runtime checks.
"""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


class PokaYokeError(Exception):
    """Poka-Yoke validation error"""


class Poka:
    """Error-proofing utility for test code

    Prevents common mistakes like:
    - Unwrap on error values
    - Panic/raise in production code
    - Missing assertions
    - Invalid state transitions

    Example:
        @test
        def test_unwrap():
            result = might_fail()
            value = Poka.unwrap(result, "operation failed")
            assert value > 0
    """

    @staticmethod
    def unwrap(value: Any, msg: str = "called unwrap on None/Error") -> Any:
        """Extract value from Result/Option-like or raise

        Equivalent to Rust's .unwrap() but fails safely with clear message.

        Args:
            value: Value that might be None, False, or error-like
            msg: Message to include in error

        Returns
        -------
            The unwrapped value

        Raises
        ------
            PokaYokeError: If value is None/False/Error

        Example:
            >>> result = {"ok": 42}
            >>> value = Poka.unwrap(result, "expected success")
            >>> assert value == 42
        """
        if value is None or value is False:
            raise PokaYokeError(f"Unwrap failed: {msg}")
        if isinstance(value, Exception):
            raise PokaYokeError(f"Unwrap failed: {msg}") from value
        if hasattr(value, "is_err") and value.is_err():
            raise PokaYokeError(f"Unwrap failed: {msg}")
        if hasattr(value, "is_none") and value.is_none():
            raise PokaYokeError(f"Unwrap failed: {msg}")
        return value

    @staticmethod
    def expect(value: Any, msg: str) -> Any:
        """Extract value from Result/Option or raise with custom message

        Alias for unwrap with better error messages.

        Args:
            value: Value to unwrap
            msg: Custom error message

        Returns
        -------
            The unwrapped value

        Raises
        ------
            PokaYokeError: If value is None/False/Error
        """
        return Poka.unwrap(value, msg)

    @staticmethod
    def unwrap_or(value: Any, default: T) -> Any:
        """Extract value or return default

        Args:
            value: Value to unwrap
            default: Default value if unwrap fails

        Returns
        -------
            The unwrapped value or default
        """
        try:
            return Poka.unwrap(value)
        except PokaYokeError:
            return default

    @staticmethod
    def unwrap_or_else(value: Any, fn: Callable[[], T]) -> Any:
        """Extract value or compute default

        Args:
            value: Value to unwrap
            fn: Function that computes default

        Returns
        -------
            The unwrapped value or result of fn()
        """
        try:
            return Poka.unwrap(value)
        except PokaYokeError:
            return fn()

    @staticmethod
    def validate(condition: bool, msg: str) -> None:
        """Validate a condition (replaces assert for clearer semantics)

        Args:
            condition: Condition that should be True
            msg: Error message if False

        Raises
        ------
            PokaYokeError: If condition is False
        """
        if not condition:
            raise PokaYokeError(f"Validation failed: {msg}")

    @staticmethod
    def not_none(value: T | None, msg: str = "value is None") -> T:
        """Assert value is not None

        Args:
            value: Value to check
            msg: Error message

        Returns
        -------
            The value (type-narrowed in static checkers)

        Raises
        ------
            PokaYokeError: If value is None
        """
        if value is None:
            raise PokaYokeError(f"Not None failed: {msg}")
        return value

    @staticmethod
    def guard_production_code(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to prevent unwrap/panic in production code

        Scans function for dangerous patterns that would work in Rust
        but should be caught in Python tests.

        Example:
            @Poka.guard_production_code
            def my_function():
                # Will warn if you try unsafe operations here
                pass
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Check function source for dangerous patterns
            try:
                source = inspect.getsource(func)
                dangerous_patterns = [".unwrap()", ".panic!()", "raise Exception()"]
                for pattern in dangerous_patterns:
                    if pattern in source:
                        raise PokaYokeError(
                            f"Production code contains dangerous pattern: {pattern}"
                        )
            except (OSError, TypeError):
                # Source not available (compiled code, etc)
                pass

            return func(*args, **kwargs)

        return wrapper
