"""Assertion Helpers for Chicago TDD.

Provides assertion utilities following Chicago TDD principles.
Uses callable predicates for flexible, composable assertions.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


class AssertionError(Exception):
    """Chicago TDD Assertion Error - raised when assertions fail.

    Attributes
    ----------
    assertion_type : str
        Type of assertion (eq, success, error, range, etc.)
    expected : Any, optional
        Expected value
    actual : Any, optional
        Actual value
    """

    def __init__(self, message: str, assertion_type: str = "generic", expected: Any = None, actual: Any = None) -> None:
        """Initialize AssertionError.

        Parameters
        ----------
        message : str
            Error message
        assertion_type : str
            Type of assertion
        expected : Any, optional
            Expected value
        actual : Any, optional
            Actual value
        """
        self.assertion_type = assertion_type
        self.expected = expected
        self.actual = actual
        super().__init__(message)


def assert_success(result: Any, msg: str | None = None) -> None:
    """Assert that a result is successful (truthy or Result-like with is_ok method).

    Args:
        result: The result to check
        msg: Optional custom message

    Raises
    ------
        AssertionError: If result is not successful
    """
    is_ok = False
    if hasattr(result, "is_ok"):
        # Support Result-like types
        is_ok = result.is_ok()
    elif hasattr(result, "is_err"):
        is_ok = not result.is_err()
    else:
        is_ok = bool(result)

    if not is_ok:
        error_msg = msg or f"Expected success, but got failure: {result}"
        raise AssertionError(error_msg)


def assert_error(result: Any, msg: str | None = None) -> None:
    """Assert that a result is an error.

    Args:
        result: The result to check
        msg: Optional custom message

    Raises
    ------
        AssertionError: If result is not an error
    """
    is_err = False
    if hasattr(result, "is_err"):
        is_err = result.is_err()
    elif hasattr(result, "is_ok"):
        is_err = not result.is_ok()
    else:
        is_err = not bool(result)

    if not is_err:
        error_msg = msg or f"Expected error, but got success: {result}"
        raise AssertionError(error_msg)


def assert_eq_with_msg(actual: T, expected: T, msg: str) -> None:
    """Assert that two values are equal with a custom message.

    Args:
        actual: The actual value
        expected: The expected value
        msg: Custom message to display on failure

    Raises
    ------
        AssertionError: If values are not equal
    """
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected!r}, got {actual!r}")


def assert_in_range(value: float, min_val: float, max_val: float, msg: str) -> None:
    """Assert that a value is within a range [min, max].

    Args:
        value: The value to check
        min_val: Minimum bound (inclusive)
        max_val: Maximum bound (inclusive)
        msg: Custom message to display on failure

    Raises
    ------
        AssertionError: If value is not in range
    """
    if not (min_val <= value <= max_val):
        raise AssertionError(f"{msg}: value {value!r} not in range [{min_val}, {max_val}]")


def assert_that(value: T, predicate: Callable[[T], bool], msg: str | None = None) -> None:
    """Assert that a value satisfies a predicate.

    Args:
        value: The value to check
        predicate: A callable that returns True if the value is valid
        msg: Optional custom message

    Raises
    ------
        AssertionError: If predicate returns False

    Example:
        >>> assert_that(42, lambda v: v > 0)  # Passes
        >>> assert_that(-1, lambda v: v > 0)  # Raises AssertionError
    """
    if not predicate(value):
        error_msg = msg or f"Assertion failed for value {value!r} with predicate {predicate}"
        raise AssertionError(error_msg)


@dataclass
class AssertionBuilder[T]:
    """Builder pattern for composable assertions.

    Allows chaining multiple assertions together for cleaner test code.

    Example:
        >>> (AssertionBuilder(42).assert_greater_than(0).assert_less_than(100).assert_that(lambda v: v % 2 == 0))
    """

    value: T

    def assert_that(self, predicate: Callable[[T], bool], msg: str | None = None) -> "AssertionBuilder[T]":
        """Chain assertion using a predicate."""
        assert_that(self.value, predicate, msg)
        return self

    def assert_equal(self, expected: T, msg: str | None = None) -> "AssertionBuilder[T]":
        """Chain equality assertion."""
        if self.value != expected:
            error_msg = msg or f"Expected {expected!r}, got {self.value!r}"
            raise AssertionError(error_msg)
        return self

    def assert_not_equal(self, unexpected: T, msg: str | None = None) -> "AssertionBuilder[T]":
        """Chain inequality assertion."""
        if self.value == unexpected:
            error_msg = msg or f"Expected not equal to {unexpected!r}"
            raise AssertionError(error_msg)
        return self

    def assert_true(self, msg: str | None = None) -> "AssertionBuilder[T]":
        """Assert value is truthy."""
        if not self.value:
            error_msg = msg or f"Expected truthy value, got {self.value!r}"
            raise AssertionError(error_msg)
        return self

    def assert_false(self, msg: str | None = None) -> "AssertionBuilder[T]":
        """Assert value is falsy."""
        if self.value:
            error_msg = msg or f"Expected falsy value, got {self.value!r}"
            raise AssertionError(error_msg)
        return self

    def get(self) -> T:
        """Get the wrapped value after all assertions pass."""
        return self.value
