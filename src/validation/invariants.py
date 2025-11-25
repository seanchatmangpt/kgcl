"""Invariant Properties for Tests

Provides invariant validation that must hold throughout test execution.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Invariant:
    """An invariant that should always hold

    Example:
        inv = Invariant(
            "list_length_non_negative",
            lambda obj: len(obj) >= 0
        )
    """

    name: str
    predicate: Callable[[Any], bool]

    def validate(self, obj: Any) -> bool:
        """Validate object against invariant

        Returns
        -------
            True if invariant holds, False otherwise
        """
        try:
            return self.predicate(obj)
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"Invariant(name={self.name!r})"


class InvariantValidator:
    """Validates invariants throughout test execution

    Tracks invariants and their violations for debugging.

    Example:
        validator = InvariantValidator()
        validator.add("length_positive", lambda x: len(x) > 0)
        validator.add("sorted", lambda x: x == sorted(x))

        my_list = [1, 2, 3]
        validator.validate_all(my_list)  # Checks all invariants
    """

    def __init__(self) -> None:
        self._invariants: dict[str, Invariant] = {}
        self._violations: list[tuple[str, Any]] = []

    def add(self, name: str, predicate: Callable[[Any], bool]) -> None:
        """Add an invariant"""
        self._invariants[name] = Invariant(name, predicate)

    def add_invariant(self, invariant: Invariant) -> None:
        """Add an invariant object"""
        self._invariants[invariant.name] = invariant

    def validate(self, name: str, obj: Any) -> bool:
        """Validate single invariant

        Returns
        -------
            True if invariant holds
        """
        if name not in self._invariants:
            return False

        invariant = self._invariants[name]
        valid = invariant.validate(obj)

        if not valid:
            self._violations.append((name, obj))

        return valid

    def validate_all(self, obj: Any) -> bool:
        """Validate all invariants against object

        Returns
        -------
            True if all invariants hold
        """
        all_valid = True
        for invariant in self._invariants.values():
            if not invariant.validate(obj):
                self._violations.append((invariant.name, obj))
                all_valid = False

        return all_valid

    def violation_count(self) -> int:
        """Get number of violations"""
        return len(self._violations)

    def violations(self) -> list[tuple[str, Any]]:
        """Get all violations"""
        return self._violations.copy()

    def has_violations(self) -> bool:
        """Check if there are violations"""
        return len(self._violations) > 0

    def reset(self) -> None:
        """Clear violations"""
        self._violations.clear()

    def assert_no_violations(self) -> None:
        """Assert no violations occurred

        Raises
        ------
            AssertionError: If there are violations
        """
        if self._violations:
            msg = f"{len(self._violations)} invariant violation(s):\n"
            for name, obj in self._violations:
                msg += f"  - {name}: {obj}\n"
            raise AssertionError(msg)

    def __repr__(self) -> str:
        return (
            f"InvariantValidator(invariants={len(self._invariants)}, "
            f"violations={len(self._violations)})"
        )
