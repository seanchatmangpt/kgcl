"""ConvergenceRunner - Run physics to completion (fixed point).

This module implements the run-to-completion logic that repeatedly
applies physics until the system converges (delta=0).

Examples
--------
>>> from kgcl.hybrid.application import TickExecutor, ConvergenceRunner
>>> # runner = ConvergenceRunner(executor)
>>> # results = runner.run(max_ticks=100)
"""

from __future__ import annotations

import logging

from kgcl.hybrid.application.tick_executor import TickExecutor
from kgcl.hybrid.domain.exceptions import ConvergenceError
from kgcl.hybrid.domain.physics_result import PhysicsResult

logger = logging.getLogger(__name__)


class ConvergenceRunner:
    """Run physics to completion (fixed point).

    Repeatedly executes ticks until the system converges (delta=0)
    or the maximum tick count is reached.

    Parameters
    ----------
    executor : TickExecutor
        The tick executor for applying physics.

    Attributes
    ----------
    tick_count : int
        Total ticks executed across all runs.

    Examples
    --------
    >>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
    >>> from kgcl.hybrid.application import TickExecutor, ConvergenceRunner
    >>> store = OxigraphAdapter()
    >>> reasoner = EYEAdapter(skip_availability_check=True)
    >>> rules = WCP43RulesAdapter()
    >>> executor = TickExecutor(store, reasoner, rules)
    >>> runner = ConvergenceRunner(executor)
    >>> runner.tick_count
    0
    """

    def __init__(self, executor: TickExecutor) -> None:
        """Initialize ConvergenceRunner.

        Parameters
        ----------
        executor : TickExecutor
            The tick executor.
        """
        self._executor = executor
        self.tick_count = 0
        logger.info("ConvergenceRunner initialized")

    def run(self, max_ticks: int = 100) -> list[PhysicsResult]:
        """Execute ticks until fixed point or maximum reached.

        Parameters
        ----------
        max_ticks : int, optional
            Maximum number of ticks to execute, by default 100.

        Returns
        -------
        list[PhysicsResult]
            Results from each tick executed.

        Raises
        ------
        ConvergenceError
            If maximum ticks reached without convergence.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
        >>> from kgcl.hybrid.application import TickExecutor, ConvergenceRunner
        >>> store = OxigraphAdapter()
        >>> _ = store.load_turtle('''
        ...     @prefix kgc: <https://kgc.org/ns/> .
        ...     @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        ...     <urn:task:A> kgc:status "Completed" ;
        ...         yawl:flowsInto <urn:flow:1> .
        ...     <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        ...     <urn:task:B> a yawl:Task .
        ... ''')
        >>> reasoner = EYEAdapter()
        >>> if reasoner.is_available():
        ...     rules = WCP43RulesAdapter()
        ...     executor = TickExecutor(store, reasoner, rules)
        ...     runner = ConvergenceRunner(executor)
        ...     results = runner.run(max_ticks=10)
        ...     len(results) > 0
        True
        """
        results: list[PhysicsResult] = []

        logger.info(f"Starting run_to_completion (max_ticks={max_ticks})")

        for _ in range(max_ticks):
            self.tick_count += 1
            result = self._executor.execute_tick(self.tick_count)
            results.append(result)

            if result.converged:
                logger.info(f"Converged at tick {result.tick_number} (delta=0)")
                break
        else:
            final_delta = results[-1].delta if results else 0
            logger.warning(f"Max ticks ({max_ticks}) reached. Final delta: {final_delta}")
            raise ConvergenceError(max_ticks=max_ticks, final_delta=final_delta)

        total_duration = sum(r.duration_ms for r in results)
        total_delta = sum(r.delta for r in results)
        logger.info(f"Completed {len(results)} ticks in {total_duration:.2f}ms, total_delta={total_delta}")

        return results

    def run_single_tick(self) -> PhysicsResult:
        """Execute a single tick.

        Convenience method for executing one tick without convergence checking.

        Returns
        -------
        PhysicsResult
            Result from the tick.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
        >>> from kgcl.hybrid.application import TickExecutor, ConvergenceRunner
        >>> store = OxigraphAdapter()
        >>> reasoner = EYEAdapter(skip_availability_check=True)
        >>> rules = WCP43RulesAdapter()
        >>> executor = TickExecutor(store, reasoner, rules)
        >>> runner = ConvergenceRunner(executor)
        >>> # result = runner.run_single_tick()
        """
        self.tick_count += 1
        return self._executor.execute_tick(self.tick_count)

    def reset_tick_count(self) -> None:
        """Reset the tick counter to zero.

        Useful for restarting execution sequences.

        Examples
        --------
        >>> from kgcl.hybrid.adapters import OxigraphAdapter, EYEAdapter, WCP43RulesAdapter
        >>> from kgcl.hybrid.application import TickExecutor, ConvergenceRunner
        >>> store = OxigraphAdapter()
        >>> reasoner = EYEAdapter(skip_availability_check=True)
        >>> rules = WCP43RulesAdapter()
        >>> executor = TickExecutor(store, reasoner, rules)
        >>> runner = ConvergenceRunner(executor)
        >>> runner.tick_count = 5
        >>> runner.reset_tick_count()
        >>> runner.tick_count
        0
        """
        self.tick_count = 0
        logger.info("Tick count reset to 0")
