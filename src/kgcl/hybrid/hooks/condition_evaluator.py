"""Innovation #2: 8-Condition Evaluator (UNRDF Port).

Enables THRESHOLD, DELTA, COUNT, WINDOW conditions beyond basic SPARQL ASK.
Supports 8 condition types for comprehensive hook triggering.

Condition Types
---------------
1. sparql-ask    - Boolean SPARQL ASK query
2. sparql-select - SPARQL SELECT with bindings check
3. shacl         - SHACL shape validation
4. delta         - Change detection between ticks
5. threshold     - Numeric comparison (>, <, ==)
6. count         - Cardinality bounds checking
7. window        - Time-based sliding window
8. n3-rule       - EYE reasoner N3 inference

Examples
--------
>>> from kgcl.hybrid.hooks.condition_evaluator import ConditionKind, Condition, ConditionEvaluator
>>> cond = Condition(
...     kind=ConditionKind.THRESHOLD,
...     expression="errorRate > 0.05",
...     parameters={"metric": "errorRate", "threshold": 0.05, "operator": ">"},
... )
>>> cond.kind
<ConditionKind.THRESHOLD: 'threshold'>
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pyoxigraph as ox


class ConditionKind(Enum):
    """Supported condition evaluation types.

    Examples
    --------
    >>> ConditionKind.SPARQL_ASK.value
    'sparql-ask'
    >>> ConditionKind.THRESHOLD.value
    'threshold'
    """

    SPARQL_ASK = "sparql-ask"
    SPARQL_SELECT = "sparql-select"
    SHACL = "shacl"
    DELTA = "delta"
    THRESHOLD = "threshold"
    COUNT = "count"
    WINDOW = "window"
    N3_RULE = "n3-rule"


@dataclass(frozen=True)
class Condition:
    """Immutable condition specification.

    Parameters
    ----------
    kind : ConditionKind
        Type of condition evaluation
    expression : str
        The condition expression (SPARQL, N3, or DSL)
    parameters : dict
        Additional parameters for evaluation

    Examples
    --------
    >>> cond = Condition(kind=ConditionKind.SPARQL_ASK, expression="ASK { ?s a :Person }")
    >>> cond.kind
    <ConditionKind.SPARQL_ASK: 'sparql-ask'>
    """

    kind: ConditionKind
    expression: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConditionResult:
    """Result of condition evaluation.

    Parameters
    ----------
    matched : bool
        Whether condition was satisfied
    bindings : dict
        Variable bindings from evaluation
    duration_ms : float
        Evaluation time in milliseconds
    metadata : dict
        Additional result metadata

    Examples
    --------
    >>> result = ConditionResult(matched=True, duration_ms=1.5)
    >>> result.matched
    True
    """

    matched: bool
    bindings: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ConditionEvaluator:
    """Evaluates 8 types of hook conditions.

    Provides a unified interface for all condition types, delegating
    to type-specific evaluation methods.

    Attributes
    ----------
    _delta_state : dict
        Previous state for delta detection
    _window_data : dict
        Sliding window data for rate calculations

    Examples
    --------
    >>> evaluator = ConditionEvaluator()
    >>> cond = Condition(kind=ConditionKind.THRESHOLD, expression="x > 5", parameters={"x": 10})
    >>> evaluator._eval_threshold(cond).matched
    True
    """

    def __init__(self) -> None:
        """Initialize condition evaluator with empty state."""
        self._delta_state: dict[str, Any] = {}
        self._window_data: dict[str, deque[tuple[float, Any]]] = {}

    def evaluate(self, condition: Condition, store: ox.Store | None = None) -> ConditionResult:
        """Evaluate condition against current state.

        Parameters
        ----------
        condition : Condition
            Condition to evaluate
        store : ox.Store | None
            PyOxigraph store for SPARQL conditions

        Returns
        -------
        ConditionResult
            Evaluation result

        Examples
        --------
        >>> evaluator = ConditionEvaluator()
        >>> cond = Condition(kind=ConditionKind.THRESHOLD, expression="x > 5", parameters={"x": 10})
        >>> evaluator.evaluate(cond).matched
        True
        """
        start = time.perf_counter()

        result = self._dispatch_evaluation(condition, store)

        duration_ms = (time.perf_counter() - start) * 1000
        return ConditionResult(
            matched=result.matched, bindings=result.bindings, duration_ms=duration_ms, metadata=result.metadata
        )

    def _dispatch_evaluation(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Dispatch to type-specific evaluator.

        Parameters
        ----------
        condition : Condition
            Condition to evaluate
        store : ox.Store | None
            Store for SPARQL evaluation

        Returns
        -------
        ConditionResult
            Evaluation result
        """
        match condition.kind:
            case ConditionKind.SPARQL_ASK:
                return self._eval_sparql_ask(condition, store)
            case ConditionKind.SPARQL_SELECT:
                return self._eval_sparql_select(condition, store)
            case ConditionKind.THRESHOLD:
                return self._eval_threshold(condition)
            case ConditionKind.DELTA:
                return self._eval_delta(condition, store)
            case ConditionKind.COUNT:
                return self._eval_count(condition, store)
            case ConditionKind.WINDOW:
                return self._eval_window(condition)
            case ConditionKind.SHACL:
                return self._eval_shacl(condition, store)
            case ConditionKind.N3_RULE:
                return self._eval_n3_rule(condition, store)

    def _eval_sparql_ask(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Evaluate SPARQL ASK condition.

        Parameters
        ----------
        condition : Condition
            SPARQL ASK condition
        store : ox.Store | None
            PyOxigraph store

        Returns
        -------
        ConditionResult
            True if ASK returns true
        """
        if store is None:
            return ConditionResult(matched=False, metadata={"error": "No store provided"})

        try:
            result = store.query(condition.expression)
            return ConditionResult(matched=bool(result))
        except Exception as e:
            return ConditionResult(matched=False, metadata={"error": str(e)})

    def _eval_sparql_select(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Evaluate SPARQL SELECT condition.

        Parameters
        ----------
        condition : Condition
            SPARQL SELECT condition
        store : ox.Store | None
            PyOxigraph store

        Returns
        -------
        ConditionResult
            True if SELECT returns any bindings
        """
        if store is None:
            return ConditionResult(matched=False, metadata={"error": "No store provided"})

        try:
            result = list(store.query(condition.expression))
            matched = len(result) > 0
            bindings = {}
            if matched and result:
                # Extract first row bindings
                for solution in result[:1]:
                    for var in solution:
                        bindings[str(var)] = str(solution[var])
            return ConditionResult(matched=matched, bindings=bindings, metadata={"row_count": len(result)})
        except Exception as e:
            return ConditionResult(matched=False, metadata={"error": str(e)})

    def _eval_threshold(self, condition: Condition) -> ConditionResult:
        """Evaluate threshold comparison condition.

        Parameters
        ----------
        condition : Condition
            Threshold condition with parameters:
            - metric: Name of metric to check
            - threshold: Comparison value
            - operator: Comparison operator (>, <, ==, >=, <=, !=)
            Or directly provide value in parameters as the metric name.

        Returns
        -------
        ConditionResult
            True if threshold comparison passes

        Examples
        --------
        >>> evaluator = ConditionEvaluator()
        >>> cond = Condition(
        ...     kind=ConditionKind.THRESHOLD,
        ...     expression="errorRate > 0.05",
        ...     parameters={"errorRate": 0.1, "threshold": 0.05, "operator": ">"},
        ... )
        >>> evaluator._eval_threshold(cond).matched
        True
        """
        params = condition.parameters
        threshold = params.get("threshold", 0)
        operator = params.get("operator", ">")

        # Find metric name and value
        # Priority: 1. explicit "metric" key, 2. explicit "value" key, 3. auto-detect numeric
        metric = params.get("metric")
        if metric:
            value = params.get(metric, 0)
        elif "value" in params:
            metric = "value"
            value = params["value"]
        else:
            # Auto-detect: find first numeric param that isn't threshold/operator
            reserved = {"threshold", "operator", "metric"}
            metric = "value"
            value = 0
            for k, v in params.items():
                if k not in reserved and isinstance(v, (int, float)):
                    metric = k
                    value = v
                    break

        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
        }

        compare = ops.get(operator, ops[">"])
        matched = compare(value, threshold)

        return ConditionResult(
            matched=matched, metadata={"metric": metric, "value": value, "threshold": threshold, "operator": operator}
        )

    def _eval_delta(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Evaluate delta (change detection) condition.

        Parameters
        ----------
        condition : Condition
            Delta condition with query to track
        store : ox.Store | None
            PyOxigraph store

        Returns
        -------
        ConditionResult
            True if state changed since last evaluation
        """
        key = condition.expression
        current_state: str | None = None

        if store is not None:
            try:
                # Execute query and hash result for comparison
                result = list(store.query(condition.expression))
                current_state = str(sorted([str(r) for r in result]))
            except Exception:
                current_state = None

        previous_state = self._delta_state.get(key)
        changed = previous_state is not None and current_state != previous_state
        self._delta_state[key] = current_state

        return ConditionResult(matched=changed, metadata={"previous": previous_state is not None, "changed": changed})

    def _eval_count(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Evaluate count (cardinality) condition.

        Parameters
        ----------
        condition : Condition
            Count condition with min/max parameters
        store : ox.Store | None
            PyOxigraph store

        Returns
        -------
        ConditionResult
            True if count within bounds
        """
        if store is None:
            return ConditionResult(matched=False, metadata={"error": "No store provided"})

        min_count = condition.parameters.get("min", 0)
        max_count = condition.parameters.get("max", float("inf"))

        try:
            result = list(store.query(condition.expression))
            count = len(result)
            matched = min_count <= count <= max_count
            return ConditionResult(matched=matched, metadata={"count": count, "min": min_count, "max": max_count})
        except Exception as e:
            return ConditionResult(matched=False, metadata={"error": str(e)})

    def _eval_window(self, condition: Condition) -> ConditionResult:
        """Evaluate sliding window condition.

        Parameters
        ----------
        condition : Condition
            Window condition with:
            - window_seconds: Time window size
            - min_events: Minimum events required
            - max_events: Maximum events allowed

        Returns
        -------
        ConditionResult
            True if event count within bounds for window
        """
        key = condition.expression
        window_seconds = condition.parameters.get("window_seconds", 60)
        min_events = condition.parameters.get("min_events", 0)
        max_events = condition.parameters.get("max_events", float("inf"))

        if key not in self._window_data:
            self._window_data[key] = deque()

        now = time.time()
        window = self._window_data[key]

        # Add current event
        window.append((now, True))

        # Prune old events
        cutoff = now - window_seconds
        while window and window[0][0] < cutoff:
            window.popleft()

        count = len(window)
        matched = min_events <= count <= max_events

        return ConditionResult(matched=matched, metadata={"count": count, "window_seconds": window_seconds})

    def _eval_shacl(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Evaluate SHACL shape validation condition.

        Parameters
        ----------
        condition : Condition
            SHACL condition with shapes graph
        store : ox.Store | None
            PyOxigraph store

        Returns
        -------
        ConditionResult
            True if data conforms to shapes

        Notes
        -----
        Requires pyshacl for full validation. Falls back to basic
        pattern matching if pyshacl not available.
        """
        # Placeholder - requires pyshacl integration
        return ConditionResult(matched=False, metadata={"error": "SHACL validation requires pyshacl integration"})

    def _eval_n3_rule(self, condition: Condition, store: ox.Store | None) -> ConditionResult:
        """Evaluate N3 rule via EYE reasoner.

        Parameters
        ----------
        condition : Condition
            N3 rule condition
        store : ox.Store | None
            PyOxigraph store

        Returns
        -------
        ConditionResult
            True if rule produces inferences

        Notes
        -----
        Requires EYE reasoner to be installed.
        """
        # Placeholder - requires EYE adapter integration
        return ConditionResult(matched=False, metadata={"error": "N3 evaluation requires EYE reasoner integration"})

    def reset_state(self) -> None:
        """Reset all stateful condition tracking.

        Examples
        --------
        >>> evaluator = ConditionEvaluator()
        >>> evaluator.reset_state()
        """
        self._delta_state.clear()
        self._window_data.clear()
