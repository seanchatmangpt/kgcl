"""Snapshot Testing.

Provides snapshot comparison for regression testing.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SnapshotTest:
    """Snapshot test for regression testing.

    Example:
        test = SnapshotTest(
            name="api_response",
            actual={"status": 200, "data": [1, 2, 3]}
        )
        test.matches_snapshot("snapshots/api_response.json")
    """

    name: str
    actual: Any
    expected: Any | None = None
    matched: bool = False

    def matches_snapshot(self, snapshot_path: str, update: bool = False) -> bool:
        """Check if actual matches snapshot.

        Args:
            snapshot_path: Path to snapshot file
            update: If True, update snapshot if different

        Returns
        -------
            True if snapshot matches
        """
        path = Path(snapshot_path)

        # Load expected from file if it exists
        if path.exists():
            with open(path) as f:
                self.expected = json.load(f)
        else:
            self.expected = None

        # Compare
        self.matched = self._compare(self.actual, self.expected)

        # Update snapshot if requested and not matched
        if update and not self.matched:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.actual, f, indent=2)
            self.matched = True

        return self.matched

    def _compare(self, actual: Any, expected: Any) -> bool:
        """Compare actual and expected values."""
        if isinstance(actual, dict) and isinstance(expected, dict):
            if set(actual.keys()) != set(expected.keys()):
                return False
            return all(self._compare(actual[k], expected[k]) for k in actual)
        if isinstance(actual, list) and isinstance(expected, list):
            if len(actual) != len(expected):
                return False
            return all(self._compare(a, e) for a, e in zip(actual, expected))
        return actual == expected

    def diff(self) -> str | None:
        """Get diff between actual and expected."""
        if self.expected is None:
            return f"No snapshot file exists for {self.name}"

        if self.matched:
            return None

        return (
            f"Snapshot mismatch:\n  Expected: {self.expected}\n  Actual: {self.actual}"
        )

    def __repr__(self) -> str:
        return f"SnapshotTest({self.name!r}, matched={self.matched})"
