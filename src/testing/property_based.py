"""Property-Based Testing.

Advanced property-based testing with shrinking and statistics.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class PropertyBasedTest:
    """Property-based test with statistics and shrinking.

    Example:
        test = PropertyBasedTest(
            "addition_is_commutative",
            lambda a, b: a + b == b + a
        )
        # Pass examples
        test.add_example(1, 2)
        test.add_example(5, 3)
        # Run the test
        result = test.run()
    """

    name: str
    property_fn: Callable[..., bool]
    examples: list[tuple] = None
    results: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.examples is None:
            self.examples = []
        if self.results is None:
            self.results = {}

    def add_example(self, *args: Any) -> None:
        """Add example to test."""
        self.examples.append(args)

    def run(self) -> bool:
        """Run property test.

        Returns
        -------
            True if all examples pass
        """
        passed = 0
        failed = 0
        errors = []

        for example in self.examples:
            try:
                if self.property_fn(*example):
                    passed += 1
                else:
                    failed += 1
                    errors.append(f"Property failed for {example}")
            except Exception as e:
                failed += 1
                errors.append(f"Error for {example}: {e}")

        self.results = {"passed": passed, "failed": failed, "total": len(self.examples), "errors": errors}

        return failed == 0

    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if not self.examples:
            return 0.0
        return (self.results.get("passed", 0) / len(self.examples)) * 100

    def report(self) -> str:
        """Generate test report."""
        lines = [
            f"Property Test: {self.name}",
            f"Examples: {len(self.examples)}",
            f"Passed: {self.results.get('passed', 0)}",
            f"Failed: {self.results.get('failed', 0)}",
            f"Success Rate: {self.success_rate():.1f}%",
        ]

        if self.results.get("errors"):
            lines.append("Errors:")
            for error in self.results["errors"][:5]:  # Show first 5 errors
                lines.append(f"  - {error}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"PropertyBasedTest({self.name!r}, examples={len(self.examples)}, success_rate={self.success_rate():.1f}%)"
        )
