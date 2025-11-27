"""TRUE Hybrid KGC Engine - PyOxigraph + EYE Reasoner.

This module implements the RESEARCH-POC.md architecture:
- PyOxigraph = Matter (Inert State Storage in Rust)
- EYE Reasoner = Physics (External Force via subprocess)
- Python = Time (Tick Controller/Orchestrator)

Philosophy
----------
Hard Separation:
- PyOxigraph is purely a container for facts. It has no reasoning capabilities.
- EYE is a dedicated inference engine. It accepts Matter + Rules and outputs New Matter.
- Python creates the Epochs (Ticks) and orchestrates the feedback loop.

Architecture
------------
1. State ($T_0$): Facts stored in PyOxigraph
2. Logic Application: Python exports State + Rules → EYE
3. Deduction: EYE returns the Implication (The Delta)
4. Evolution ($T_1$): Python inserts Delta → PyOxigraph

This visualizes Logic as a Force applied to State as Mass.

Prerequisites
-------------
- pyoxigraph: pip install pyoxigraph
- eye: Euler reasoner installed and in system PATH

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>>
>>> # Create engine with in-memory store
>>> engine = HybridEngine()
>>>
>>> # Load initial topology
>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
...
... <urn:task:Start> a yawl:Task ;
...     kgc:status "Completed" ;
...     yawl:flowsInto <urn:flow:1> .
...
... <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
... <urn:task:Next> a yawl:Task .
... '''
>>> engine.load_data(topology)
>>>
>>> # Apply physics (one tick)
>>> result = engine.apply_physics()
>>> result.tick_number
1
>>> result.delta > 0  # New triples were inferred
True
>>>
>>> # Run to completion
>>> results = engine.run_to_completion(max_ticks=10)
>>> len(results)
2
>>> all(r.delta >= 0 for r in results)
True
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pyoxigraph as ox

from kgcl.hybrid.adapters.eye_adapter import EYEAdapter
from kgcl.hybrid.adapters.oxigraph_adapter import OxigraphAdapter
from kgcl.hybrid.adapters.wcp43_rules_adapter import WCP43RulesAdapter
from kgcl.hybrid.application.convergence_runner import ConvergenceRunner
from kgcl.hybrid.application.status_inspector import StatusInspector
from kgcl.hybrid.application.tick_executor import TickExecutor
from kgcl.hybrid.domain.exceptions import ConvergenceError
from kgcl.hybrid.domain.physics_result import PhysicsResult

# Backward compatibility alias: N3_PHYSICS -> WCP43_COMPLETE_PHYSICS
from kgcl.hybrid.wcp43_physics import WCP43_COMPLETE_PHYSICS as N3_PHYSICS

if TYPE_CHECKING:
    from kgcl.hybrid.knowledge_hooks import HookExecutor, HookRegistry

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["HybridEngine", "PhysicsResult", "N3_PHYSICS"]


class HybridEngine:
    """Hybrid KGC Engine with PyOxigraph storage and EYE reasoning.

    This engine implements the Hard Separation principle:
    - PyOxigraph stores the Inert State (Matter)
    - EYE reasoner applies the Physics (Force)
    - Python orchestrates the Time (Ticks)

    Parameters
    ----------
    store_path : str | None, optional
        Path for persistent storage. If None, uses in-memory store.
    hook_registry : HookRegistry | None, optional
        Hook registry for automatic hook execution on data changes.

    Attributes
    ----------
    store : ox.Store
        PyOxigraph triple store (Rust-based).
    tick_count : int
        Number of ticks executed.

    Examples
    --------
    >>> # In-memory engine
    >>> engine = HybridEngine()
    >>> engine.store
    <pyoxigraph.Store object at ...>
    >>>
    >>> # Persistent engine
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     engine = HybridEngine(store_path=tmpdir)
    ...     # Engine will persist to disk
    """

    def __init__(self, store_path: str | None = None, hook_registry: HookRegistry | None = None) -> None:
        """Initialize the hybrid engine with PyOxigraph store.

        Parameters
        ----------
        store_path : str | None, optional
            Path for persistent storage. If None, uses in-memory store.
        hook_registry : HookRegistry | None, optional
            Hook registry for automatic hook execution on data changes.
        """
        # Initialize adapters
        self._store_adapter = OxigraphAdapter(store_path)
        self._reasoner_adapter = EYEAdapter()
        self._rules_adapter = WCP43RulesAdapter()

        # Initialize application services
        self._executor = TickExecutor(self._store_adapter, self._reasoner_adapter, self._rules_adapter)
        self._runner = ConvergenceRunner(self._executor)
        self._inspector = StatusInspector(self._store_adapter)

        # State
        self.tick_count = 0

        # Hook integration (reactive event-driven architecture)
        self._hook_registry = hook_registry
        self._hook_executor: HookExecutor | None = None
        if hook_registry:
            from kgcl.hybrid.knowledge_hooks import HookExecutor

            self._hook_executor = HookExecutor(hook_registry, self)
            logger.info("Hook executor initialized")

        logger.info(f"HybridEngine initialized (persistent={store_path is not None})")

    @property
    def store(self) -> ox.Store:
        """Get the underlying pyoxigraph Store.

        Returns
        -------
        ox.Store
            The underlying PyOxigraph store.
        """
        return self._store_adapter.raw_store

    def load_data(self, turtle_data: str, *, trigger_hooks: bool = True) -> None:
        """Ingest initial state from Turtle data.

        Parameters
        ----------
        turtle_data : str
            RDF data in Turtle format.
        trigger_hooks : bool, optional
            Whether to execute ON_CHANGE hooks after loading.

        Raises
        ------
        ValueError
            If a hook with REJECT action fires.
        """
        self._store_adapter.load_turtle(turtle_data)
        triple_count = self._store_adapter.triple_count()
        logger.info(f"Loaded {triple_count} triples into store")

        # Auto-trigger ON_CHANGE hooks
        if trigger_hooks and self._hook_executor:
            from kgcl.hybrid.knowledge_hooks import HookPhase

            self._hook_executor.load_hooks_to_graph()
            self._hook_executor.execute_phase(HookPhase.ON_CHANGE)
            rollback, reason = self._hook_executor.check_rollback_requested()
            if rollback:
                logger.warning(f"Hook rejected data load: {reason}")
                raise ValueError(f"Hook rejected data: {reason}")

    def apply_physics(self) -> PhysicsResult:
        """Execute one tick: Export → Reason → Ingest.

        Returns
        -------
        PhysicsResult
            Result of physics application with timing and delta metrics.

        Raises
        ------
        FileNotFoundError
            If EYE reasoner is not found in system PATH.
        """
        self.tick_count += 1
        return self._executor.execute_tick(self.tick_count)

    def inspect(self) -> dict[str, str]:
        """Query current task statuses (returning highest-priority status).

        Returns
        -------
        dict[str, str]
            Mapping of task IRI to highest-priority status string.
        """
        return self._inspector.get_task_statuses()

    def run_to_completion(self, max_ticks: int = 100) -> list[PhysicsResult]:
        """Execute ticks until fixed point or maximum ticks reached.

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
        RuntimeError
            If maximum ticks reached without convergence.
        """
        # Reset runner tick count to sync with engine tick count
        self._runner.tick_count = self.tick_count

        try:
            results = self._runner.run(max_ticks=max_ticks)
            # Sync tick count back
            self.tick_count = self._runner.tick_count
            return results
        except ConvergenceError as e:
            self.tick_count = self._runner.tick_count
            raise RuntimeError(
                f"System did not converge after {e.max_ticks} ticks. "
                f"Consider increasing max_ticks or reviewing physics rules."
            ) from e

    def _dump_state(self) -> str:
        """Snapshot the current reality as Turtle.

        Returns
        -------
        str
            Current graph state serialized.
        """
        return self._store_adapter.dump_trig()
