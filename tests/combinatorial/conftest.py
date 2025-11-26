"""Conftest for combinatorial tests.

Provides fixtures and utilities for async hook execution testing.
"""

import asyncio
from typing import Any

import pytest

from kgcl.hooks.conditions import ConditionResult
from kgcl.hooks.core import Hook, HookExecutor, HookReceipt, HookRegistry


def run_async(coro: Any) -> Any:
    """Run async coroutine synchronously.

    Parameters
    ----------
    coro : Coroutine
        Async coroutine to run

    Returns
    -------
    Any
        Result of the coroutine
    """
    # Python 3.12+ deprecates get_event_loop() without running loop
    # Use asyncio.run() for cleaner handling
    return asyncio.run(coro)


class SyncHookExecutor:
    """Synchronous wrapper for HookExecutor.

    Provides sync execute() method for testing.
    """

    def __init__(self) -> None:
        """Initialize executor."""
        self._executor = HookExecutor()

    def execute(self, hook: Hook, context: dict[str, Any]) -> HookReceipt:
        """Execute hook synchronously.

        Parameters
        ----------
        hook : Hook
            Hook to execute
        context : dict[str, Any]
            Execution context

        Returns
        -------
        HookReceipt
            Execution receipt
        """
        return run_async(self._executor.execute(hook, context))


class SyncConditionEvaluator:
    """Synchronous wrapper for condition evaluation."""

    @staticmethod
    def evaluate(condition: Any, context: dict[str, Any]) -> ConditionResult:
        """Evaluate condition synchronously.

        Parameters
        ----------
        condition : Condition
            Condition to evaluate
        context : dict[str, Any]
            Evaluation context

        Returns
        -------
        ConditionResult
            Evaluation result
        """
        return run_async(condition.evaluate(context))


class SyncHookRegistry:
    """Synchronous wrapper for HookRegistry with execute_all support.

    Provides sync execute_all() method for testing.
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._registry = HookRegistry()
        self._executor = SyncHookExecutor()

    def register(self, hook: Hook) -> None:
        """Register hook.

        Parameters
        ----------
        hook : Hook
            Hook to register
        """
        self._registry.register(hook)

    def unregister(self, name: str) -> None:
        """Unregister hook by name.

        Parameters
        ----------
        name : str
            Hook name
        """
        self._registry.unregister(name)

    def get(self, name: str) -> Hook | None:
        """Get hook by name.

        Parameters
        ----------
        name : str
            Hook name

        Returns
        -------
        Hook | None
            Hook if found
        """
        return self._registry.get(name)

    def get_all(self) -> list[Hook]:
        """Get all hooks.

        Returns
        -------
        list[Hook]
            All registered hooks
        """
        return self._registry.get_all()

    def execute_all(self, context: dict[str, Any]) -> list[HookReceipt]:
        """Execute all hooks synchronously.

        Parameters
        ----------
        context : dict[str, Any]
            Execution context

        Returns
        -------
        list[HookReceipt]
            List of execution receipts
        """
        receipts = []
        for hook in self._registry.get_all_sorted():
            if hook.enabled:
                receipt = self._executor.execute(hook, context)
                receipts.append(receipt)
        return receipts


@pytest.fixture
def sync_executor() -> SyncHookExecutor:
    """Create sync hook executor."""
    return SyncHookExecutor()


@pytest.fixture
def sync_evaluator() -> SyncConditionEvaluator:
    """Create sync condition evaluator."""
    return SyncConditionEvaluator()


@pytest.fixture
def sync_registry() -> SyncHookRegistry:
    """Create sync hook registry."""
    return SyncHookRegistry()
