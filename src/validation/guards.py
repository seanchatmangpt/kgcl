"""Guard Types for Validated Values

Provides wrapper types that enforce validation at runtime.
Similar to Rust's type-level validation compiled away in Python.
"""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Guard(Generic[T]):
    """Type guard for runtime validation

    Similar to Rust's type-level guarantees, but with runtime checks.

    Example:
        # Create a guard that ensures values are positive
        positive = Guard.validated(42, lambda x: x > 0)

        # This would fail
        try:
            negative = Guard.validated(-1, lambda x: x > 0)
        except ValueError:
            print("Value failed validation")
    """

    def __init__(self, value: T, validator: Callable[[T], bool]) -> None:
        self._value = value
        self._validator = validator
        if not validator(value):
            raise ValueError(f"Value {value!r} failed validation")

    @staticmethod
    def validated(value: T, validator: Callable[[T], bool]) -> "Guard[T]":
        """Create a validated guard

        Args:
            value: Value to wrap
            validator: Predicate that must return True

        Returns
        -------
            Guard wrapping the value

        Raises
        ------
            ValueError: If validation fails
        """
        return Guard(value, validator)

    def get(self) -> T:
        """Get the wrapped value (guaranteed to be valid)"""
        return self._value

    def map(self, f: Callable[[T], Any]) -> Any:
        """Transform the value"""
        return f(self._value)

    def __repr__(self) -> str:
        return f"Guard({self._value!r})"


class ValidatedValue(Generic[T]):
    """Wrapper for validated values with lazy evaluation

    Example:
        val = ValidatedValue(
            value=42,
            validators=[
                ("positive", lambda x: x > 0),
                ("under_100", lambda x: x < 100),
            ]
        )
        if val.is_valid():
            print(val.get())
    """

    def __init__(
        self, value: T, validators: list[tuple[str, Callable[[T], bool]]] | None = None
    ) -> None:
        self._value = value
        self._validators = validators or []
        self._validation_cache: bool | None = None
        self._failures: list[str] = []

    def add_validator(self, name: str, validator: Callable[[T], bool]) -> "ValidatedValue[T]":
        """Add validator"""
        self._validators.append((name, validator))
        self._validation_cache = None  # Invalidate cache
        return self

    def is_valid(self) -> bool:
        """Check if value is valid (with caching)"""
        if self._validation_cache is not None:
            return self._validation_cache

        self._failures = []
        for name, validator in self._validators:
            try:
                if not validator(self._value):
                    self._failures.append(name)
            except Exception as e:
                self._failures.append(f"{name} (error: {e})")

        self._validation_cache = len(self._failures) == 0
        return self._validation_cache

    def get(self) -> T:
        """Get value if valid

        Returns
        -------
            The value

        Raises
        ------
            ValueError: If value is not valid
        """
        if not self.is_valid():
            raise ValueError(
                f"Value {self._value!r} failed validators: {', '.join(self._failures)}"
            )
        return self._value

    def get_or(self, default: T) -> T:
        """Get value or return default"""
        return self._value if self.is_valid() else default

    def failures(self) -> list[str]:
        """Get list of failed validators"""
        return self._failures.copy()

    def failure_count(self) -> int:
        """Get number of failed validators"""
        return len(self._failures)

    def __repr__(self) -> str:
        return f"ValidatedValue({self._value!r}, valid={self.is_valid()})"
