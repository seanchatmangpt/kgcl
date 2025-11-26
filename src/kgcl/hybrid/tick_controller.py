"""Tick controller for KGC Hybrid Engine.

Orchestrates rule execution phases with extensible hook system.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol

from rdflib import Graph


class TickPhase(Enum):
    """Phases of a tick execution cycle."""

    PRE_TICK = auto()
    APPLY_RULES = auto()
    POST_TICK = auto()


@dataclass(frozen=True)
class TickResult:
    """Result of a tick execution.

    Attributes
    ----------
    tick_number : int
        Sequential tick identifier
    rules_fired : int
        Number of rules that produced changes
    triples_added : int
        Number of triples added to graph
    triples_removed : int
        Number of triples removed from graph
    duration_ms : float
        Execution time in milliseconds
    converged : bool
        Whether fixed point was reached
    metadata : dict[str, Any]
        Additional execution metadata
    """

    tick_number: int
    rules_fired: int
    triples_added: int
    triples_removed: int
    duration_ms: float
    converged: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class TickHook(Protocol):
    """Protocol for tick execution hooks.

    Hooks receive callbacks at each phase of tick execution,
    enabling extensible monitoring and control.
    """

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Execute before tick begins.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        tick_number : int
            Current tick number

        Returns
        -------
        bool
            True to continue execution, False to abort
        """
        ...

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Execute after a rule fires.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        rule : Any
            Rule that fired
        tick_number : int
            Current tick number
        """
        ...

    def on_post_tick(self, engine: Any, result: TickResult) -> None:
        """Execute after tick completes.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        result : TickResult
            Tick execution result
        """
        ...


class TickController:
    """Orchestrates tick-based rule execution.

    Manages tick phases, hook execution, and fixed-point detection.

    Parameters
    ----------
    engine : Any
        Hybrid engine instance to control

    Attributes
    ----------
    _engine : Any
        Engine instance
    _hooks : list[TickHook]
        Registered hooks
    _tick_count : int
        Total ticks executed
    _total_rules_fired : int
        Cumulative rules fired
    """

    def __init__(self, engine: Any) -> None:
        """Initialize tick controller.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        """
        self._engine = engine
        self._hooks: list[TickHook] = []
        self._tick_count: int = 0
        self._total_rules_fired: int = 0

    def register_hook(self, hook: TickHook) -> None:
        """Register a tick hook.

        Parameters
        ----------
        hook : TickHook
            Hook to register
        """
        self._hooks.append(hook)

    def execute_tick(self) -> TickResult:
        """Execute one tick of rule application.

        Orchestrates PRE_TICK, APPLY_RULES, and POST_TICK phases.

        Returns
        -------
        TickResult
            Execution result with statistics

        Raises
        ------
        RuntimeError
            If pre-tick validation fails
        """
        import time

        self._tick_count += 1
        start_time = time.perf_counter()

        # PRE_TICK: Validate state
        for hook in self._hooks:
            if not hook.on_pre_tick(self._engine, self._tick_count):
                msg = f"Pre-tick validation failed at tick {self._tick_count}"
                raise RuntimeError(msg)

        # APPLY_RULES: Fire compiled SPARQL
        initial_size = len(self._engine.graph) if hasattr(self._engine, "graph") else 0
        rules_fired = 0

        if hasattr(self._engine, "rules"):
            for rule in self._engine.rules:
                # Execute rule (assumes rule has execute/apply method)
                if hasattr(rule, "execute"):
                    changes = rule.execute(self._engine.graph)
                    if changes > 0:
                        rules_fired += 1
                        for hook in self._hooks:
                            hook.on_rule_fired(self._engine, rule, self._tick_count)

        final_size = len(self._engine.graph) if hasattr(self._engine, "graph") else 0
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Calculate changes
        triples_added = max(0, final_size - initial_size)
        triples_removed = max(0, initial_size - final_size)
        converged = rules_fired == 0

        result = TickResult(
            tick_number=self._tick_count,
            rules_fired=rules_fired,
            triples_added=triples_added,
            triples_removed=triples_removed,
            duration_ms=duration_ms,
            converged=converged,
        )

        self._total_rules_fired += rules_fired

        # POST_TICK: Record provenance
        for hook in self._hooks:
            hook.on_post_tick(self._engine, result)

        return result

    def should_continue(self, result: TickResult) -> bool:
        """Determine if execution should continue.

        Parameters
        ----------
        result : TickResult
            Latest tick result

        Returns
        -------
        bool
            True if more ticks needed, False if converged
        """
        return not result.converged

    @property
    def tick_count(self) -> int:
        """Total ticks executed.

        Returns
        -------
        int
            Number of ticks
        """
        return self._tick_count

    @property
    def total_rules_fired(self) -> int:
        """Cumulative rules fired across all ticks.

        Returns
        -------
        int
            Total rules fired
        """
        return self._total_rules_fired


@dataclass
class ProvenanceRecord:
    """Record of tick execution provenance.

    Attributes
    ----------
    tick_number : int
        Tick identifier
    rules_fired : int
        Rules that fired
    duration_ms : float
        Execution time
    timestamp : float
        Unix timestamp
    """

    tick_number: int
    rules_fired: int
    duration_ms: float
    timestamp: float


class ProvenanceHook:
    """Records tick execution history and statistics.

    Attributes
    ----------
    _history : list[ProvenanceRecord]
        Tick execution history
    _rule_counts : dict[str, int]
        Rule firing counts by rule ID
    """

    def __init__(self) -> None:
        """Initialize provenance hook."""
        self._history: list[ProvenanceRecord] = []
        self._rule_counts: dict[str, int] = {}

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Validate state before tick.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        tick_number : int
            Current tick number

        Returns
        -------
        bool
            Always True (no validation failures)
        """
        return True

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Record rule firing.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        rule : Any
            Rule that fired
        tick_number : int
            Current tick number
        """
        rule_id = getattr(rule, "id", str(rule))
        self._rule_counts[rule_id] = self._rule_counts.get(rule_id, 0) + 1

    def on_post_tick(self, engine: Any, result: TickResult) -> None:
        """Record tick completion.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        result : TickResult
            Tick execution result
        """
        import time

        record = ProvenanceRecord(
            tick_number=result.tick_number,
            rules_fired=result.rules_fired,
            duration_ms=result.duration_ms,
            timestamp=time.time(),
        )
        self._history.append(record)

    def get_history(self) -> list[ProvenanceRecord]:
        """Retrieve tick history.

        Returns
        -------
        list[ProvenanceRecord]
            Chronological tick records
        """
        return list(self._history)

    def get_rule_counts(self) -> dict[str, int]:
        """Retrieve rule firing counts.

        Returns
        -------
        dict[str, int]
            Rule ID to firing count mapping
        """
        return dict(self._rule_counts)

    def compute_statistics(self) -> dict[str, Any]:
        """Compute execution statistics.

        Returns
        -------
        dict[str, Any]
            Statistics including:
            - total_ticks: Total ticks executed
            - total_rules_fired: Cumulative rules fired
            - avg_duration_ms: Average tick duration
            - avg_rules_per_tick: Average rules fired per tick
            - most_fired_rule: Most frequently fired rule
        """
        if not self._history:
            return {
                "total_ticks": 0,
                "total_rules_fired": 0,
                "avg_duration_ms": 0.0,
                "avg_rules_per_tick": 0.0,
                "most_fired_rule": None,
            }

        total_ticks = len(self._history)
        total_rules = sum(r.rules_fired for r in self._history)
        total_duration = sum(r.duration_ms for r in self._history)

        most_fired = max(self._rule_counts.items(), key=lambda x: x[1], default=(None, 0))

        return {
            "total_ticks": total_ticks,
            "total_rules_fired": total_rules,
            "avg_duration_ms": total_duration / total_ticks,
            "avg_rules_per_tick": total_rules / total_ticks,
            "most_fired_rule": most_fired[0],
            "most_fired_count": most_fired[1],
        }


class DebugHook:
    """Logs tick execution details for debugging.

    Parameters
    ----------
    log_fn : Callable[[str], None] | None
        Logging function (defaults to print)
    verbose : bool
        Enable verbose output
    """

    def __init__(self, log_fn: Callable[[str], None] | None = None, verbose: bool = False) -> None:
        """Initialize debug hook.

        Parameters
        ----------
        log_fn : Callable[[str], None] | None
            Logging function (defaults to print)
        verbose : bool
            Enable verbose output
        """
        self._log_fn = log_fn or print
        self._verbose = verbose

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Log pre-tick state.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        tick_number : int
            Current tick number

        Returns
        -------
        bool
            Always True
        """
        graph_size = len(engine.graph) if hasattr(engine, "graph") else 0
        self._log_fn(f"[TICK {tick_number}] PRE: Graph size = {graph_size}")

        if self._verbose and hasattr(engine, "graph"):
            self._log_fn(f"[TICK {tick_number}] Graph preview:")
            for i, triple in enumerate(engine.graph):
                if i >= 5:  # Limit preview to 5 triples
                    break
                self._log_fn(f"  {triple}")

        return True

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Log rule firing.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        rule : Any
            Rule that fired
        tick_number : int
            Current tick number
        """
        rule_id = getattr(rule, "id", str(rule))
        self._log_fn(f"[TICK {tick_number}] RULE FIRED: {rule_id}")

    def on_post_tick(self, engine: Any, result: TickResult) -> None:
        """Log post-tick results.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        result : TickResult
            Tick execution result
        """
        self._log_fn(
            f"[TICK {result.tick_number}] POST: "
            f"rules_fired={result.rules_fired}, "
            f"added={result.triples_added}, "
            f"removed={result.triples_removed}, "
            f"duration={result.duration_ms:.2f}ms, "
            f"converged={result.converged}"
        )
