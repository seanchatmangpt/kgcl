"""Fail-Fast Validation.

Provides early failure detection for test scenarios.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationFailure:
    """Represents a validation failure."""

    check_name: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"ValidationFailure(check={self.check_name!r}, reason={self.reason!r})"


class FailFastValidator:
    """Fail-fast validator for early error detection.

    Collects validation failures and can throw immediately or collect for later review.

    Example:
        @test
        def test_with_fail_fast():
            validator = FailFastValidator()
            validator.check_that("x > 0", lambda: x > 0)
            validator.check_that("y > 0", lambda: y > 0)
            validator.assert_all_pass()
    """

    def __init__(self, fail_fast: bool = False) -> None:
        self._fail_fast = fail_fast
        self._failures: list[ValidationFailure] = []

    def check_that(
        self,
        check_name: str,
        condition: Callable[[], bool],
        context: dict | None = None,
    ) -> bool:
        """Check a condition.

        Args:
            check_name: Name of the check
            condition: Callable that returns True if check passes
            context: Optional context data

        Returns
        -------
            True if check passed, False otherwise

        Raises
        ------
            AssertionError: If fail_fast=True and check fails
        """
        if not condition():
            failure = ValidationFailure(
                check_name=check_name,
                reason=f"Check '{check_name}' failed",
                context=context or {},
            )
            self._failures.append(failure)

            if self._fail_fast:
                raise AssertionError(str(failure))
            return False
        return True

    def check_equal(self, check_name: str, actual: Any, expected: Any) -> bool:
        """Check equality."""
        return self.check_that(
            check_name,
            lambda: actual == expected,
            context={"actual": actual, "expected": expected},
        )

    def check_true(self, check_name: str, value: bool) -> bool:
        """Check boolean is True."""
        return self.check_that(check_name, lambda: value)

    def check_false(self, check_name: str, value: bool) -> bool:
        """Check boolean is False."""
        return self.check_that(check_name, lambda: not value)

    def has_failures(self) -> bool:
        """Check if any failures occurred."""
        return len(self._failures) > 0

    def failure_count(self) -> int:
        """Get count of failures."""
        return len(self._failures)

    def failures(self) -> list[ValidationFailure]:
        """Get all failures."""
        return self._failures.copy()

    def assert_all_pass(self) -> None:
        """Assert that all checks passed.

        Raises
        ------
            AssertionError: If any checks failed
        """
        if self._failures:
            msg = f"{len(self._failures)} validation(s) failed:\n"
            for failure in self._failures:
                msg += f"  - {failure}\n"
            raise AssertionError(msg)

    def reset(self) -> None:
        """Reset failures list."""
        self._failures.clear()

    def __repr__(self) -> str:
        return f"FailFastValidator(failures={len(self._failures)}, fail_fast={self._fail_fast})"
