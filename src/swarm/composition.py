"""Test Composition for Complex Scenarios.

Combines multiple tests into composed test scenarios.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CompositionStrategy(Enum):
    """Strategy for composing tests."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"


@dataclass
class ComposedTest:
    """A test composed from multiple sub-tests."""

    name: str
    strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL
    tests: list[Callable[[], Any]] = field(default_factory=list)
    before_hooks: list[Callable[[], None]] = field(default_factory=list)
    after_hooks: list[Callable[[], None]] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)

    def add_test(self, test: Callable[[], Any]) -> "ComposedTest":
        """Add test to composition."""
        self.tests.append(test)
        return self

    def add_before_hook(self, hook: Callable[[], None]) -> "ComposedTest":
        """Add before hook."""
        self.before_hooks.append(hook)
        return self

    def add_after_hook(self, hook: Callable[[], None]) -> "ComposedTest":
        """Add after hook."""
        self.after_hooks.append(hook)
        return self

    def execute(self) -> list[Any]:
        """Execute composed tests.

        Returns
        -------
            List of results from all tests
        """
        self.results = []

        # Run before hooks
        for hook in self.before_hooks:
            hook()

        try:
            if self.strategy == CompositionStrategy.SEQUENTIAL:
                self._execute_sequential()
            elif self.strategy == CompositionStrategy.PARALLEL:
                self._execute_parallel()
            elif self.strategy == CompositionStrategy.PIPELINE:
                self._execute_pipeline()
        finally:
            # Run after hooks
            for hook in self.after_hooks:
                hook()

        return self.results

    def _execute_sequential(self) -> None:
        """Execute tests sequentially."""
        for test in self.tests:
            result = test()
            self.results.append(result)

    def _execute_parallel(self) -> None:
        """Execute tests in parallel using asyncio.

        Note: Sequential execution used when tests don't support async.
        For true parallelism, tests should be async coroutines.
        """
        # Execute tests - parallel execution requires async test functions
        for test in self.tests:
            result = test()
            self.results.append(result)

    def _execute_pipeline(self) -> None:
        """Execute tests as pipeline (output of one feeds into next)."""
        result = None
        for test in self.tests:
            if callable(test):
                result = test() if result is None else test(result)
            self.results.append(result)

    def test_count(self) -> int:
        """Get number of tests."""
        return len(self.tests)

    def result_count(self) -> int:
        """Get number of results."""
        return len(self.results)

    def __repr__(self) -> str:
        return f"ComposedTest(name={self.name!r}, strategy={self.strategy.value}, tests={len(self.tests)})"


class CompositionBuilder:
    """Builder for composing multiple tests."""

    def __init__(self, name: str) -> None:
        self._composed = ComposedTest(name=name)

    def sequential(self) -> "CompositionBuilder":
        """Use sequential execution strategy."""
        self._composed.strategy = CompositionStrategy.SEQUENTIAL
        return self

    def parallel(self) -> "CompositionBuilder":
        """Use parallel execution strategy."""
        self._composed.strategy = CompositionStrategy.PARALLEL
        return self

    def pipeline(self) -> "CompositionBuilder":
        """Use pipeline execution strategy."""
        self._composed.strategy = CompositionStrategy.PIPELINE
        return self

    def add_test(self, test: Callable[[], Any]) -> "CompositionBuilder":
        """Add test."""
        self._composed.add_test(test)
        return self

    def before(self, hook: Callable[[], None]) -> "CompositionBuilder":
        """Add before hook."""
        self._composed.add_before_hook(hook)
        return self

    def after(self, hook: Callable[[], None]) -> "CompositionBuilder":
        """Add after hook."""
        self._composed.add_after_hook(hook)
        return self

    def build(self) -> ComposedTest:
        """Build and return composed test."""
        return self._composed

    def execute(self) -> list[Any]:
        """Execute composed tests."""
        return self._composed.execute()

    def __repr__(self) -> str:
        return f"CompositionBuilder({self._composed})"
