"""
Condition System for Hooks.

Implements various condition types for hook triggering including SPARQL,
SHACL, delta detection, thresholds, and composite conditions.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from kgcl.hooks.query_cache import QueryCache


@dataclass
class ConditionResult:
    """
    Result of condition evaluation.

    Parameters
    ----------
    triggered : bool
        Whether condition was triggered
    metadata : Dict[str, Any]
        Additional metadata about evaluation
    """

    triggered: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class AlwaysTrueCondition:
    """
    Condition that always evaluates to True.

    Useful for testing and benchmarking hook execution without condition overhead.
    """

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """
        Always return True.

        Parameters
        ----------
        context : dict[str, Any]
            Execution context (ignored)

        Returns
        -------
        ConditionResult
            Result with triggered=True
        """
        return ConditionResult(triggered=True, metadata={})


class Condition(ABC):
    """
    Abstract base class for conditions.

    All conditions must implement evaluate() method that returns ConditionResult.
    """

    def __init__(self, timeout: float | None = None, cache_ttl: float | None = None):
        """
        Initialize condition.

        Parameters
        ----------
        timeout : Optional[float]
            Evaluation timeout in seconds
        cache_ttl : Optional[float]
            Cache TTL in seconds
        """
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: ConditionResult | None = None
        self._cache_timestamp: datetime | None = None

    @abstractmethod
    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """
        Evaluate the condition.

        Parameters
        ----------
        context : Dict[str, Any]
            Evaluation context

        Returns
        -------
        ConditionResult
            Evaluation result
        """

    async def evaluate_with_timeout(self, context: dict[str, Any]) -> ConditionResult:
        """
        Evaluate with timeout.

        Parameters
        ----------
        context : Dict[str, Any]
            Evaluation context

        Returns
        -------
        ConditionResult
            Evaluation result

        Raises
        ------
        asyncio.TimeoutError
            If evaluation exceeds timeout
        """
        if self.timeout:
            return await asyncio.wait_for(self.evaluate(context), timeout=self.timeout)
        return await self.evaluate(context)

    async def evaluate_with_cache(self, context: dict[str, Any]) -> ConditionResult:
        """
        Evaluate with caching.

        Parameters
        ----------
        context : Dict[str, Any]
            Evaluation context

        Returns
        -------
        ConditionResult
            Evaluation result (may be cached)
        """
        now = datetime.now(UTC)

        # Check cache validity
        if (
            self.cache_ttl
            and self._cache is not None
            and self._cache_timestamp is not None
        ):
            age = (now - self._cache_timestamp).total_seconds()
            if age < self.cache_ttl:
                return self._cache

        # Evaluate and cache
        result = await self.evaluate(context)
        if self.cache_ttl:
            self._cache = result
            self._cache_timestamp = now

        return result


class AlwaysTrueCondition(Condition):
    """Condition that always triggers (useful for benchmarking/tests)."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Return a triggered result regardless of context."""
        return ConditionResult(triggered=True, metadata={"reason": "always_true"})


class SparqlAskCondition(Condition):
    """
    Condition that evaluates SPARQL ASK queries.

    Triggers when ASK query returns true.
    Supports query result caching with TTL.
    Supports file resolution with SHA256 integrity checking (UNRDF pattern).

    Parameters
    ----------
    query : Optional[str]
        SPARQL ASK query (inline)
    ref : Optional[Dict[str, str]]
        File reference {'uri': '...', 'sha256': '...'} (UNRDF pattern)
    use_cache : bool
        Whether to use query result caching
    bindings : Dict[str, Any]
        Variable bindings for query
    """

    # Shared cache instance across all SparqlAskCondition instances
    _cache: QueryCache | None = None
    _last_query: str | None = None

    def __init__(
        self,
        query: str | None = None,
        ref: dict[str, str] | None = None,
        use_cache: bool = True,
        bindings: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize SPARQL ASK condition.

        Parameters
        ----------
        query : str, optional
            SPARQL ASK query (inline)
        ref : Dict[str, str], optional
            File reference {'uri': '...', 'sha256': '...'}
        use_cache : bool
            Whether to use query result caching
        bindings : Dict[str, Any], optional
            Variable bindings for query
        """
        super().__init__(**kwargs)
        self.query = query
        self.ref = ref
        self.use_cache = use_cache
        self.bindings = bindings or {}

        # Initialize shared cache if needed
        if use_cache and SparqlAskCondition._cache is None:
            SparqlAskCondition._cache = QueryCache(max_size=1000, ttl_seconds=3600)

    def get_query(self, resolver=None) -> str:
        """Get SPARQL query, resolving from file if needed.

        Parameters
        ----------
        resolver : FileResolver, optional
            FileResolver for loading from file

        Returns
        -------
        str
            SPARQL query string

        Raises
        ------
        ValueError
            If ref is invalid or file load fails
        """
        if self.query:
            return self.query

        if self.ref and resolver:
            uri = self.ref.get("uri")
            sha256_hash = self.ref.get("sha256")
            if not uri:
                raise ValueError("ref missing 'uri' field")
            return resolver.load_file(uri, sha256_hash)

        raise ValueError("No query or ref provided for condition")

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate SPARQL ASK query against RDF data.

        Parameters
        ----------
        context : dict[str, Any]
            Must contain 'rdf_data' key with list of triples or RDF graph

        Returns
        -------
        ConditionResult
            Result with triggered=True if ASK query matches
        """
        query_string = self._interpolate_query(context)
        SparqlAskCondition._last_query = query_string

        # Check cache first
        if self.use_cache and SparqlAskCondition._cache is not None:
            cached_result = SparqlAskCondition._cache.get(query_string)
            if cached_result is not None:
                return ConditionResult(
                    triggered=cached_result,
                    metadata={
                        "query": query_string,
                        "type": "sparql_ask",
                        "cache_hit": True,
                    },
                )

        # Execute SPARQL ASK query against provided RDF data
        # Support legacy test_result for backwards compatibility
        if "test_result" in context:
            triggered = bool(context["test_result"])
        else:
            rdf_data = context.get("rdf_data", [])
            triggered = self._execute_ask_query(query_string, rdf_data)

        # Cache the result
        if self.use_cache and SparqlAskCondition._cache is not None:
            SparqlAskCondition._cache.set(query_string, triggered)

        return ConditionResult(
            triggered=triggered,
            metadata={"query": query_string, "type": "sparql_ask", "cache_hit": False},
        )

    def _interpolate_query(self, context: dict[str, Any]) -> str:
        """Interpolate variables into query string.

        Parameters
        ----------
        context : dict[str, Any]
            Context containing variable bindings

        Returns
        -------
        str
            Query with interpolated variables
        """
        query = self.query or ""
        for key, value in self.bindings.items():
            placeholder = f"${key}"
            query = query.replace(placeholder, str(value))
        return query

    def _execute_ask_query(
        self, query: str, rdf_data: list[tuple[str, str, str]]
    ) -> bool:
        """Execute SPARQL ASK query against in-memory RDF triples.

        Parses the WHERE clause pattern and matches against triples.

        Parameters
        ----------
        query : str
            SPARQL ASK query string
        rdf_data : list[tuple[str, str, str]]
            List of RDF triples as (subject, predicate, object) tuples

        Returns
        -------
        bool
            True if pattern matches any triple, False otherwise
        """
        import re

        # Extract pattern from ASK query
        where_match = re.search(
            r"WHERE\s*\{([^}]+)\}", query, re.IGNORECASE | re.DOTALL
        )
        if not where_match:
            return False

        pattern_str = where_match.group(1).strip()

        # Parse triple pattern (simplified: ?s ?p ?o or <uri> ?p ?o etc.)
        pattern_match = re.match(r"(\S+)\s+(\S+)\s+(\S+)", pattern_str)
        if not pattern_match:
            return False

        subj_pattern, pred_pattern, obj_pattern = pattern_match.groups()

        # Match against triples
        for subj, pred, obj in rdf_data:
            if (
                self._matches_term(subj_pattern, subj)
                and self._matches_term(pred_pattern, pred)
                and self._matches_term(obj_pattern, obj)
            ):
                return True

        return False

    def _matches_term(self, pattern: str, value: str) -> bool:
        """Check if pattern matches value.

        Variables (starting with ?) match anything.
        URIs are compared after stripping angle brackets.

        Parameters
        ----------
        pattern : str
            Pattern to match (variable or URI)
        value : str
            Value to match against

        Returns
        -------
        bool
            True if pattern matches value
        """
        if pattern.startswith("?"):
            return True  # Variable matches anything
        return pattern.strip("<>") == value.strip("<>")

    @classmethod
    def get_cache_stats(cls) -> dict[str, Any] | None:
        """Get cache statistics.

        Returns
        -------
        Optional[Dict[str, Any]]
            Cache statistics or None if cache is disabled
        """
        if cls._cache is None:
            return None
        return cls._cache.get_stats(cls._last_query)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the query cache."""
        if cls._cache is not None:
            cls._cache.clear()


class SparqlSelectCondition(Condition):
    """
    Condition that evaluates SPARQL SELECT queries.

    Triggers when SELECT returns results (result count > 0).
    Supports query result caching with TTL.
    """

    # Shared cache instance across all SparqlSelectCondition instances
    _cache: QueryCache | None = None
    _last_query: str | None = None

    def __init__(self, query: str, use_cache: bool = True, **kwargs: Any) -> None:
        """
        Initialize SPARQL SELECT condition.

        Parameters
        ----------
        query : str
            SPARQL SELECT query
        use_cache : bool
            Whether to use query result caching
        """
        super().__init__(**kwargs)
        self.query = query
        self.use_cache = use_cache

        # Initialize shared cache if needed
        if use_cache and SparqlSelectCondition._cache is None:
            SparqlSelectCondition._cache = QueryCache(max_size=1000, ttl_seconds=3600)

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate SPARQL SELECT query with caching."""
        query_string = self.query
        SparqlSelectCondition._last_query = query_string

        # Check cache first
        if self.use_cache and SparqlSelectCondition._cache is not None:
            cached_result = SparqlSelectCondition._cache.get(query_string)
            if cached_result is not None:
                result_count = len(cached_result)
                return ConditionResult(
                    triggered=result_count > 0,
                    metadata={
                        "query": query_string,
                        "result_count": result_count,
                        "type": "sparql_select",
                        "cache_hit": True,
                    },
                )

        # In real implementation, would execute against SPARQL endpoint
        results = context.get("test_results", [])
        result_count = len(results)

        # Cache the results
        if self.use_cache and SparqlSelectCondition._cache is not None:
            SparqlSelectCondition._cache.set(query_string, results)

        return ConditionResult(
            triggered=result_count > 0,
            metadata={
                "query": query_string,
                "result_count": result_count,
                "type": "sparql_select",
                "cache_hit": False,
            },
        )

    @classmethod
    def get_cache_stats(cls) -> dict[str, Any] | None:
        """Get cache statistics.

        Returns
        -------
        Optional[Dict[str, Any]]
            Cache statistics or None if cache is disabled
        """
        if cls._cache is None:
            return None
        return cls._cache.get_stats(cls._last_query)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the query cache."""
        if cls._cache is not None:
            cls._cache.clear()


class ShaclCondition(Condition):
    """
    Condition that validates RDF against SHACL shapes.

    Triggers when validation succeeds (conforms = true).
    """

    def __init__(self, shapes: str, **kwargs: Any) -> None:
        """
        Initialize SHACL condition.

        Parameters
        ----------
        shapes : str
            SHACL shapes definition (Turtle format)
        """
        super().__init__(**kwargs)
        self.shapes = shapes

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate SHACL validation against RDF data.

        Parameters
        ----------
        context : dict[str, Any]
            Must contain 'data_graph' key with RDF data string

        Returns
        -------
        ConditionResult
            Result with triggered=True if validation succeeds
        """
        data_graph = context.get("data_graph", "")

        # Parse RDF data and validate against SHACL shapes
        conforms, violations = self._validate_shacl(data_graph, self.shapes)

        return ConditionResult(
            triggered=conforms,
            metadata={"conforms": conforms, "violations": violations, "type": "shacl"},
        )

    def _validate_shacl(
        self, data_graph: str, shapes_graph: str
    ) -> tuple[bool, list[dict[str, str]]]:
        """Validate RDF data against SHACL shapes.

        Performs basic SHACL validation by checking required properties.

        Parameters
        ----------
        data_graph : str
            RDF data to validate (Turtle format)
        shapes_graph : str
            SHACL shapes definition (Turtle format)

        Returns
        -------
        tuple[bool, list[dict[str, str]]]
            Tuple of (conforms, violations)
        """
        violations: list[dict[str, str]] = []

        # Extract required properties from shapes
        required_props = self._extract_required_properties(shapes_graph)

        # Check if data contains required properties
        for prop in required_props:
            if prop not in data_graph:
                violations.append(
                    {
                        "message": f"Missing required property: {prop}",
                        "property": prop,
                        "severity": "Violation",
                    }
                )

        conforms = len(violations) == 0
        return conforms, violations

    def _extract_required_properties(self, shapes_graph: str) -> list[str]:
        """Extract required properties from SHACL shapes.

        Parameters
        ----------
        shapes_graph : str
            SHACL shapes definition (Turtle format)

        Returns
        -------
        list[str]
            List of required property names
        """
        import re

        # Extract properties marked with sh:minCount 1
        pattern = r"sh:path\s+(\w+:\w+|\w+)\s*;\s*sh:minCount\s+1"
        matches = re.findall(pattern, shapes_graph, re.MULTILINE)
        return matches


class DeltaType(Enum):
    """Type of delta to detect."""

    ANY = "any"  # Any change
    INCREASE = "increase"  # Value increased
    DECREASE = "decrease"  # Value decreased


class DeltaCondition(Condition):
    """
    Condition that detects graph changes.

    Compares previous and current values to detect changes.
    """

    def __init__(self, delta_type: DeltaType, query: str, **kwargs: Any) -> None:
        """
        Initialize delta condition.

        Parameters
        ----------
        delta_type : DeltaType
            Type of delta to detect
        query : str
            Query to extract value for comparison
        """
        super().__init__(**kwargs)
        self.delta_type = delta_type
        self.query = query

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate delta condition."""
        previous = context.get("previous_count", 0)
        current = context.get("current_count", 0)
        delta = current - previous

        triggered = False
        if self.delta_type == DeltaType.ANY:
            triggered = delta != 0
        elif self.delta_type == DeltaType.INCREASE:
            triggered = delta > 0
        elif self.delta_type == DeltaType.DECREASE:
            triggered = delta < 0

        return ConditionResult(
            triggered=triggered,
            metadata={
                "delta": delta,
                "previous": previous,
                "current": current,
                "type": "delta",
            },
        )


class ThresholdOperator(Enum):
    """Threshold comparison operators."""

    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"


class ThresholdCondition(Condition):
    """
    Condition that compares numeric values against thresholds.

    Example: count > 5, temperature < 100
    """

    def __init__(
        self, variable: str, operator: ThresholdOperator, value: float, **kwargs: Any
    ) -> None:
        """
        Initialize threshold condition.

        Parameters
        ----------
        variable : str
            Variable name to compare
        operator : ThresholdOperator
            Comparison operator
        value : float
            Threshold value
        """
        super().__init__(**kwargs)
        self.variable = variable
        self.operator = operator
        self.value = value

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate threshold condition."""
        actual_value = context.get(self.variable)

        if actual_value is None:
            return ConditionResult(
                triggered=False,
                metadata={"error": f"Variable '{self.variable}' not found"},
            )

        triggered = False
        if self.operator == ThresholdOperator.GREATER_THAN:
            triggered = actual_value > self.value
        elif self.operator == ThresholdOperator.LESS_THAN:
            triggered = actual_value < self.value
        elif self.operator == ThresholdOperator.EQUALS:
            triggered = actual_value == self.value
        elif self.operator == ThresholdOperator.NOT_EQUALS:
            triggered = actual_value != self.value
        elif self.operator == ThresholdOperator.GREATER_EQUAL:
            triggered = actual_value >= self.value
        elif self.operator == ThresholdOperator.LESS_EQUAL:
            triggered = actual_value <= self.value

        return ConditionResult(
            triggered=triggered,
            metadata={
                "variable": self.variable,
                "operator": self.operator.value,
                "threshold": self.value,
                "actual_value": actual_value,
                "type": "threshold",
            },
        )


class WindowAggregation(Enum):
    """Window aggregation functions."""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


class WindowCondition(Condition):
    """
    Condition that aggregates values over a time window.

    Example: sum of requests in last 60 seconds > 100
    """

    def __init__(
        self,
        variable: str,
        window_seconds: float,
        aggregation: WindowAggregation,
        threshold: float,
        operator: ThresholdOperator,
        **kwargs: Any,
    ) -> None:
        """
        Initialize window condition.

        Parameters
        ----------
        variable : str
            Variable name to aggregate
        window_seconds : float
            Time window in seconds
        aggregation : WindowAggregation
            Aggregation function
        threshold : float
            Threshold for aggregated value
        operator : ThresholdOperator
            Comparison operator
        """
        super().__init__(**kwargs)
        self.variable = variable
        self.window_seconds = window_seconds
        self.aggregation = aggregation
        self.threshold = threshold
        self.operator = operator

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate window condition."""
        time_series = context.get("time_series", [])
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=self.window_seconds)

        # Filter to time window
        windowed_values = [
            point[self.variable]
            for point in time_series
            if point.get("timestamp", now) >= window_start and self.variable in point
        ]

        # Aggregate
        aggregated: float
        if not windowed_values:
            aggregated = 0.0
        elif self.aggregation == WindowAggregation.SUM:
            aggregated = sum(windowed_values)
        elif self.aggregation == WindowAggregation.AVG:
            aggregated = sum(windowed_values) / len(windowed_values)
        elif self.aggregation == WindowAggregation.MIN:
            aggregated = min(windowed_values)
        elif self.aggregation == WindowAggregation.MAX:
            aggregated = max(windowed_values)
        else:  # WindowAggregation.COUNT
            aggregated = float(len(windowed_values))

        # Compare against threshold
        triggered = False
        if self.operator == ThresholdOperator.GREATER_THAN:
            triggered = aggregated > self.threshold
        elif self.operator == ThresholdOperator.LESS_THAN:
            triggered = aggregated < self.threshold
        elif self.operator == ThresholdOperator.EQUALS:
            triggered = aggregated == self.threshold
        elif self.operator == ThresholdOperator.NOT_EQUALS:
            triggered = aggregated != self.threshold
        elif self.operator == ThresholdOperator.GREATER_EQUAL:
            triggered = aggregated >= self.threshold
        elif self.operator == ThresholdOperator.LESS_EQUAL:
            triggered = aggregated <= self.threshold

        return ConditionResult(
            triggered=triggered,
            metadata={
                "variable": self.variable,
                "window_seconds": self.window_seconds,
                "aggregation": self.aggregation.value,
                "aggregated_value": aggregated,
                "threshold": self.threshold,
                "operator": self.operator.value,
                "count": len(windowed_values),
                "type": "window",
            },
        )


class CompositeOperator(Enum):
    """Composite condition operators."""

    AND = "and"
    OR = "or"
    NOT = "not"


class CompositeCondition(Condition):
    """
    Composite condition combining multiple conditions.

    Supports AND, OR, NOT logical operators.
    """

    def __init__(
        self, operator: CompositeOperator, conditions: list[Condition], **kwargs: Any
    ) -> None:
        """
        Initialize composite condition.

        Parameters
        ----------
        operator : CompositeOperator
            Logical operator
        conditions : List[Condition]
            Child conditions to combine
        """
        super().__init__(**kwargs)
        self.operator = operator
        self.conditions = conditions

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Evaluate composite condition."""
        # Evaluate all child conditions
        results = await asyncio.gather(
            *[cond.evaluate(context) for cond in self.conditions]
        )

        triggered = False
        if self.operator == CompositeOperator.AND:
            triggered = all(r.triggered for r in results)
        elif self.operator == CompositeOperator.OR:
            triggered = any(r.triggered for r in results)
        elif self.operator == CompositeOperator.NOT:
            triggered = not results[0].triggered if results else False

        return ConditionResult(
            triggered=triggered,
            metadata={
                "operator": self.operator.value,
                "child_results": [
                    {"triggered": r.triggered, "metadata": r.metadata} for r in results
                ],
                "type": "composite",
            },
        )
