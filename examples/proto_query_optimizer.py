#!/usr/bin/env python3
"""
Hyper-Advanced SPARQL Query Optimizer Prototype.

Demonstrates cutting-edge Python techniques:
1. AST-based query transformation
2. Visitor pattern with singledispatch
3. Memoization with WeakValueDictionary
4. Expression trees with operator overloading
5. Cost model with __lt__ for comparison
6. Iterator protocol for lazy plan generation
7. Structural pattern matching for query patterns
8. Dataclass with custom __hash__ for caching
9. Context manager for query execution scope
10. Chainable builder pattern
11. Statistics with running averages
12. Topological sort for dependency resolution

Run: python examples/proto_query_optimizer.py
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import singledispatch
from graphlib import TopologicalSorter
from typing import Any, TypeAlias
from weakref import WeakValueDictionary

# ============================================================================
# 1. AST-based Query Node Types
# ============================================================================

QueryAST: TypeAlias = dict[str, Any]


class NodeType(Enum):
    """Query node types."""

    TRIPLE_PATTERN = auto()
    FILTER = auto()
    JOIN = auto()
    UNION = auto()
    OPTIONAL = auto()
    BGP = auto()  # Basic Graph Pattern


@dataclass(frozen=True, slots=True)
class Variable:
    """SPARQL variable."""

    name: str

    def __str__(self) -> str:
        return f"?{self.name}"


@dataclass(frozen=True, slots=True)
class URI:
    """SPARQL URI."""

    value: str

    def __str__(self) -> str:
        return f"<{self.value}>"


@dataclass(frozen=True, slots=True)
class Literal:
    """SPARQL literal."""

    value: str
    datatype: str | None = None

    def __str__(self) -> str:
        if self.datatype:
            return f'"{self.value}"^^{self.datatype}'
        return f'"{self.value}"'


Term: TypeAlias = Variable | URI | Literal
# Forward reference for recursive type definition (required for mutual recursion)
QueryNode: TypeAlias = "BGPNode | FilterNode | JoinNode"  # type: ignore[misc]


@dataclass(frozen=True, slots=True)
class TriplePattern:
    """SPARQL triple pattern."""

    subject: Term
    predicate: Term
    object: Term

    def __str__(self) -> str:
        return f"{self.subject} {self.predicate} {self.object}"


@dataclass(frozen=True, slots=True)
class FilterNode:
    """Filter operation node."""

    condition: str
    child: QueryNode
    node_type: NodeType = field(default=NodeType.FILTER, init=False)
    metadata: dict[str, Any] = field(default_factory=dict, init=False)


@dataclass(frozen=True, slots=True)
class JoinNode:
    """Join operation node."""

    left: QueryNode
    right: QueryNode
    join_vars: set[str]
    node_type: NodeType = field(default=NodeType.JOIN, init=False)
    metadata: dict[str, Any] = field(default_factory=dict, init=False)


@dataclass(frozen=True, slots=True)
class BGPNode:
    """Basic Graph Pattern node."""

    patterns: tuple[TriplePattern, ...]
    node_type: NodeType = field(default=NodeType.BGP, init=False)
    metadata: dict[str, Any] = field(default_factory=dict, init=False)


# ============================================================================
# 2. Visitor Pattern with singledispatch
# ============================================================================


@singledispatch
def optimize_node(node: QueryNode) -> QueryNode:
    """Optimize query node (default case)."""
    return node


@optimize_node.register
def _(node: FilterNode) -> QueryNode:
    """Push down filter closer to source."""
    # Recursively optimize child first
    optimized_child = optimize_node(node.child)

    # If child is a join, try to push filter down
    if isinstance(optimized_child, JoinNode):
        # Check if filter only references variables from left side
        filter_vars = extract_filter_variables(node.condition)
        left_vars = get_node_variables(optimized_child.left)

        if filter_vars <= left_vars:
            # Push filter to left side
            new_left = FilterNode(node.condition, optimized_child.left)
            return JoinNode(new_left, optimized_child.right, optimized_child.join_vars)

    return FilterNode(node.condition, optimized_child)


@optimize_node.register
def _(node: JoinNode) -> QueryNode:
    """Reorder join for optimal execution."""
    # Recursively optimize children
    opt_left = optimize_node(node.left)
    opt_right = optimize_node(node.right)

    # Calculate costs
    left_cost = estimate_cost(opt_left)
    right_cost = estimate_cost(opt_right)

    # Reorder if right is cheaper (smaller result set first)
    if right_cost < left_cost:
        return JoinNode(opt_right, opt_left, node.join_vars)

    return JoinNode(opt_left, opt_right, node.join_vars)


@optimize_node.register
def _(node: BGPNode) -> QueryNode:
    """Reorder triple patterns by selectivity."""
    # Calculate selectivity for each pattern
    selectivities = [(pattern, analyze_pattern(pattern)) for pattern in node.patterns]

    # Sort by selectivity (most selective first)
    sorted_patterns = tuple(p for p, _ in sorted(selectivities, key=lambda x: x[1]))

    return BGPNode(sorted_patterns)


def extract_filter_variables(condition: str) -> set[str]:
    """Extract variable names from filter condition."""
    # Simple extraction: find ?varname patterns
    import re

    return {match.group(1) for match in re.finditer(r"\?(\w+)", condition)}


def get_node_variables(node: QueryNode) -> set[str]:
    """Get all variables referenced in node."""
    if isinstance(node, BGPNode):
        vars_set: set[str] = set()
        for pattern in node.patterns:
            if isinstance(pattern.subject, Variable):
                vars_set.add(pattern.subject.name)
            if isinstance(pattern.predicate, Variable):
                vars_set.add(pattern.predicate.name)
            if isinstance(pattern.object, Variable):
                vars_set.add(pattern.object.name)
        return vars_set
    if isinstance(node, JoinNode):
        return get_node_variables(node.left) | get_node_variables(node.right)
    if isinstance(node, FilterNode):
        return get_node_variables(node.child)
    return set()


# ============================================================================
# 3. Memoization with WeakValueDictionary
# ============================================================================


@dataclass(frozen=True)
class OptimizedQuery:
    """Optimized query result."""

    root: QueryNode
    estimated_cost: QueryCost
    optimization_time_ms: float
    __weakref__: Any = field(default=None, init=False, repr=False, compare=False)


class QueryCache:
    """Cache for optimized queries using weak references."""

    _cache: dict[str, OptimizedQuery] = {}
    _weak_cache: WeakValueDictionary[str, OptimizedQuery] = WeakValueDictionary()

    @classmethod
    def get_or_compute(
        cls, query_str: str, compute: Callable[[str], OptimizedQuery]
    ) -> OptimizedQuery:
        """Get cached result or compute and cache."""
        # Check weak cache first
        if query_str in cls._weak_cache:
            result = cls._weak_cache[query_str]
            if result is not None:
                return result

        # Compute and store in both caches
        if query_str not in cls._cache:
            result = compute(query_str)
            cls._cache[query_str] = result
            try:
                cls._weak_cache[query_str] = result
            except TypeError:
                # Can't create weak reference - that's ok
                pass

        return cls._cache[query_str]

    @classmethod
    def clear(cls) -> None:
        """Clear cache."""
        cls._cache.clear()
        cls._weak_cache.clear()

    @classmethod
    def size(cls) -> int:
        """Get cache size."""
        return len(cls._cache)


# ============================================================================
# 4. Expression Trees with Operator Overloading
# ============================================================================


class QueryExpr:
    """Composable query expression with operator overloading."""

    def __and__(self, other: QueryExpr) -> AndExpr:
        """Combine with AND."""
        return AndExpr(self, other)

    def __or__(self, other: QueryExpr) -> OrExpr:
        """Combine with OR."""
        return OrExpr(self, other)

    def __invert__(self) -> NotExpr:
        """Negate expression."""
        return NotExpr(self)

    def to_sparql(self) -> str:
        """Convert to SPARQL."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class VarExpr(QueryExpr):
    """Variable expression."""

    var: str

    def to_sparql(self) -> str:
        return f"?{self.var}"


@dataclass(frozen=True, slots=True)
class AndExpr(QueryExpr):
    """AND expression."""

    left: QueryExpr
    right: QueryExpr

    def to_sparql(self) -> str:
        return f"({self.left.to_sparql()} && {self.right.to_sparql()})"


@dataclass(frozen=True, slots=True)
class OrExpr(QueryExpr):
    """OR expression."""

    left: QueryExpr
    right: QueryExpr

    def to_sparql(self) -> str:
        return f"({self.left.to_sparql()} || {self.right.to_sparql()})"


@dataclass(frozen=True, slots=True)
class NotExpr(QueryExpr):
    """NOT expression."""

    expr: QueryExpr

    def to_sparql(self) -> str:
        return f"!{self.expr.to_sparql()}"


# ============================================================================
# 5. Cost Model with __lt__ for Comparison
# ============================================================================


@dataclass(frozen=True, slots=True, order=True)
class QueryCost:
    """Comparable query cost for optimization decisions."""

    io_cost: float
    cpu_cost: float
    memory_cost: float

    @property
    def total(self) -> float:
        """Total weighted cost."""
        return self.io_cost + self.cpu_cost * 0.1 + self.memory_cost * 0.01

    def __str__(self) -> str:
        return f"Cost(io={self.io_cost:.2f}, cpu={self.cpu_cost:.2f}, mem={self.memory_cost:.2f}, total={self.total:.2f})"


def estimate_cost(node: QueryNode) -> QueryCost:
    """Estimate execution cost for query node."""
    if isinstance(node, BGPNode):
        # Cost based on number of patterns and selectivity
        total_selectivity = sum(analyze_pattern(p) for p in node.patterns)
        io_cost = total_selectivity * 1000  # Estimated rows
        cpu_cost = len(node.patterns) * 10
        memory_cost = total_selectivity * 100
        return QueryCost(io_cost, cpu_cost, memory_cost)

    if isinstance(node, JoinNode):
        left_cost = estimate_cost(node.left)
        right_cost = estimate_cost(node.right)
        # Join cost is product of input sizes
        io_cost = left_cost.io_cost * right_cost.io_cost * 0.1
        cpu_cost = left_cost.cpu_cost + right_cost.cpu_cost + 100
        memory_cost = max(left_cost.memory_cost, right_cost.memory_cost) * 2
        return QueryCost(io_cost, cpu_cost, memory_cost)

    if isinstance(node, FilterNode):
        child_cost = estimate_cost(node.child)
        # Filter reduces result set but adds CPU cost
        io_cost = child_cost.io_cost * 0.5  # Assume 50% selectivity
        cpu_cost = child_cost.cpu_cost + 50
        memory_cost = child_cost.memory_cost
        return QueryCost(io_cost, cpu_cost, memory_cost)

    return QueryCost(0.0, 0.0, 0.0)


# ============================================================================
# 6. Iterator Protocol for Lazy Plan Generation
# ============================================================================


@dataclass
class QueryPlan:
    """Executable query plan."""

    steps: tuple[QueryStep, ...]
    estimated_cost: QueryCost

    def __hash__(self) -> int:
        """Hash based on step operations."""
        return hash(tuple(s.operation for s in self.steps))


@dataclass(frozen=True, slots=True)
class QueryStep:
    """Individual query execution step."""

    id: str
    operation: str
    dependencies: set[str] = field(default_factory=set)
    estimated_rows: int = 0


class PlanGenerator:
    """Generate query plans lazily."""

    def __init__(self, root: QueryNode, max_plans: int = 10) -> None:
        self.root = root
        self.max_plans = max_plans
        self._current = 0
        self._plans_generated: list[QueryPlan] = []

    def __iter__(self) -> Iterator[QueryPlan]:
        return self

    def __next__(self) -> QueryPlan:
        if self._current >= self.max_plans:
            raise StopIteration

        # Generate different plans by varying join order, filter placement, etc.
        plan = self._generate_plan(self._current)
        self._plans_generated.append(plan)
        self._current += 1
        return plan

    def _generate_plan(self, variation: int) -> QueryPlan:
        """Generate a specific plan variation."""
        # Simple variation: different optimization passes
        optimized = self.root
        for _ in range(variation % 3):
            optimized = optimize_node(optimized)

        steps = self._node_to_steps(optimized)
        cost = estimate_cost(optimized)
        return QueryPlan(steps, cost)

    def _node_to_steps(self, node: QueryNode, step_id: int = 0) -> tuple[QueryStep, ...]:
        """Convert query node to execution steps."""
        if isinstance(node, BGPNode):
            return (
                QueryStep(
                    id=f"step_{step_id}",
                    operation=f"ScanTriples({len(node.patterns)})",
                    estimated_rows=int(sum(analyze_pattern(p) for p in node.patterns) * 100),
                ),
            )

        if isinstance(node, JoinNode):
            left_steps = self._node_to_steps(node.left, step_id)
            right_steps = self._node_to_steps(node.right, step_id + len(left_steps))
            join_step = QueryStep(
                id=f"step_{step_id + len(left_steps) + len(right_steps)}",
                operation=f"HashJoin({len(node.join_vars)})",
                dependencies={left_steps[-1].id, right_steps[-1].id},
                estimated_rows=int(
                    estimate_cost(node.left).io_cost * estimate_cost(node.right).io_cost * 0.1
                ),
            )
            return left_steps + right_steps + (join_step,)

        if isinstance(node, FilterNode):
            child_steps = self._node_to_steps(node.child, step_id)
            filter_step = QueryStep(
                id=f"step_{step_id + len(child_steps)}",
                operation=f"Filter({node.condition[:20]}...)",
                dependencies={child_steps[-1].id},
                estimated_rows=int(child_steps[-1].estimated_rows * 0.5),
            )
            return child_steps + (filter_step,)

        return ()


# ============================================================================
# 7. Structural Pattern Matching for Query Patterns
# ============================================================================


def analyze_pattern(pattern: TriplePattern) -> float:
    """Analyze triple pattern selectivity using pattern matching."""
    match pattern:
        case TriplePattern(subject=Variable(), predicate=URI(), object=Literal()):
            return 0.1  # Highly selective: bound predicate and object
        case TriplePattern(subject=URI(), predicate=_, object=_):
            return 0.3  # Subject bound
        case TriplePattern(predicate=URI(value="rdf:type"), object=URI()):
            return 0.2  # Type pattern - usually selective
        case TriplePattern(subject=Variable(), predicate=Variable(), object=Variable()):
            return 1.0  # Full scan - least selective
        case TriplePattern(subject=_, predicate=URI(), object=_):
            return 0.5  # Predicate bound
        case _:
            return 0.8  # Default moderate selectivity


# ============================================================================
# 8. Context Manager for Query Execution Scope
# ============================================================================


@dataclass
class OptimizerContext:
    """Optimization context with hints and configuration."""

    hints: OptimizationHints
    stats: RunningStats = field(default_factory=lambda: RunningStats())

    def record_optimization(self, cost: float) -> None:
        """Record optimization cost."""
        self.stats.update(cost)


@dataclass
class OptimizationHints:
    """Hints to guide query optimization."""

    prefer_index_scans: bool = True
    max_join_reorderings: int = 5
    enable_filter_pushdown: bool = True
    target_cost_reduction: float = 0.5


_current_context: ContextVar[OptimizerContext | None] = ContextVar(
    "_current_context", default=None
)


@contextmanager
def optimization_context(hints: OptimizationHints) -> Iterator[OptimizerContext]:
    """Scoped optimization with cleanup."""
    ctx = OptimizerContext(hints)
    token = _current_context.set(ctx)
    try:
        yield ctx
    finally:
        _current_context.reset(token)


def get_current_context() -> OptimizerContext | None:
    """Get current optimization context."""
    return _current_context.get()


# ============================================================================
# 9. Chainable Builder Pattern
# ============================================================================


class QueryBuilder:
    """Fluent query builder."""

    def __init__(self) -> None:
        self._select: tuple[str, ...] = ()
        self._patterns: list[TriplePattern] = []
        self._filters: list[str] = []

    def select(self, *vars: str) -> QueryBuilder:
        """Add SELECT clause."""
        self._select = vars
        return self

    def where(self, *patterns: TriplePattern) -> QueryBuilder:
        """Add WHERE patterns."""
        self._patterns.extend(patterns)
        return self

    def filter(self, condition: str) -> QueryBuilder:
        """Add FILTER clause."""
        self._filters.append(condition)
        return self

    def build(self) -> QueryNode:
        """Build final query node."""
        # Start with BGP
        bgp = BGPNode(tuple(self._patterns))

        # Add filters
        result: QueryNode = bgp
        for filter_cond in self._filters:
            result = FilterNode(filter_cond, result)

        return result


# ============================================================================
# 10. Statistics with Running Averages
# ============================================================================


class RunningStats:
    """Online algorithm for running statistics (Welford's method)."""

    __slots__ = ("_count", "_mean", "_m2")

    def __init__(self) -> None:
        self._count: int = 0
        self._mean: float = 0.0
        self._m2: float = 0.0

    def update(self, value: float) -> None:
        """Update statistics with new value."""
        self._count += 1
        delta = value - self._mean
        self._mean += delta / self._count
        delta2 = value - self._mean
        self._m2 += delta * delta2

    @property
    def count(self) -> int:
        """Number of samples."""
        return self._count

    @property
    def mean(self) -> float:
        """Sample mean."""
        return self._mean

    @property
    def variance(self) -> float:
        """Sample variance."""
        return self._m2 / self._count if self._count > 1 else 0.0

    @property
    def std_dev(self) -> float:
        """Standard deviation."""
        return self.variance**0.5

    def __str__(self) -> str:
        return f"Stats(n={self.count}, mean={self.mean:.2f}, std={self.std_dev:.2f})"


# ============================================================================
# 11. Topological Sort for Dependency Resolution
# ============================================================================


def order_by_dependencies(steps: list[QueryStep]) -> list[QueryStep]:
    """Order query steps by dependencies using topological sort."""
    # Build dependency graph
    graph: dict[str, set[str]] = {step.id: step.dependencies for step in steps}

    # Add empty dependencies for steps not yet in graph
    for step in steps:
        if step.id not in graph:
            graph[step.id] = set()

    # Topologically sort
    sorter = TopologicalSorter(graph)
    order = list(sorter.static_order())

    # Return steps in dependency order
    step_map = {s.id: s for s in steps}
    return [step_map[step_id] for step_id in order if step_id in step_map]


# ============================================================================
# 12. Complete Optimizer
# ============================================================================


class QueryOptimizer:
    """Complete SPARQL query optimizer."""

    def __init__(self) -> None:
        self.stats = RunningStats()

    def optimize(self, query: QueryNode, hints: OptimizationHints | None = None) -> OptimizedQuery:
        """Optimize query with context."""
        if hints is None:
            hints = OptimizationHints()

        with optimization_context(hints) as ctx:
            import time

            start = time.perf_counter()

            # Apply optimization passes
            optimized = query
            for _ in range(hints.max_join_reorderings):
                optimized = optimize_node(optimized)

            # Calculate cost
            cost = estimate_cost(optimized)

            # Record optimization time
            elapsed_ms = (time.perf_counter() - start) * 1000
            ctx.record_optimization(elapsed_ms)
            self.stats.update(elapsed_ms)

            return OptimizedQuery(optimized, cost, elapsed_ms)

    def optimize_cached(self, query_str: str, query: QueryNode) -> OptimizedQuery:
        """Optimize with caching."""
        return QueryCache.get_or_compute(
            query_str, lambda _: self.optimize(query)
        )


# ============================================================================
# TESTS
# ============================================================================


def test_pattern_matching_selectivity() -> None:
    """Test structural pattern matching for selectivity analysis."""
    # Highly selective: bound predicate and literal object
    p1 = TriplePattern(Variable("s"), URI("foaf:name"), Literal("Alice"))
    assert analyze_pattern(p1) == 0.1

    # Subject bound
    p2 = TriplePattern(URI("ex:person1"), Variable("p"), Variable("o"))
    assert analyze_pattern(p2) == 0.3

    # Type pattern
    p3 = TriplePattern(Variable("x"), URI("rdf:type"), URI("foaf:Person"))
    assert analyze_pattern(p3) == 0.2

    # Full scan
    p4 = TriplePattern(Variable("s"), Variable("p"), Variable("o"))
    assert analyze_pattern(p4) == 1.0

    print("✓ Pattern matching selectivity")


def test_visitor_pattern_optimization() -> None:
    """Test singledispatch visitor pattern for optimization."""
    # Create unoptimized query: BGP with unordered patterns
    p1 = TriplePattern(Variable("s"), Variable("p"), Variable("o"))  # Least selective
    p2 = TriplePattern(Variable("s"), URI("foaf:name"), Literal("Alice"))  # Most selective
    bgp = BGPNode((p1, p2))

    # Optimize
    optimized = optimize_node(bgp)

    # Should reorder to put most selective first
    assert isinstance(optimized, BGPNode)
    assert optimized.patterns[0] == p2  # Most selective first
    assert optimized.patterns[1] == p1

    print("✓ Visitor pattern optimization")


def test_filter_pushdown() -> None:
    """Test filter pushdown optimization."""
    # Create BGP
    p1 = TriplePattern(Variable("x"), URI("foaf:name"), Variable("name"))
    bgp1 = BGPNode((p1,))

    p2 = TriplePattern(Variable("y"), URI("foaf:age"), Variable("age"))
    bgp2 = BGPNode((p2,))

    # Join with filter on left side only
    join = JoinNode(bgp1, bgp2, {"x", "y"})
    filtered = FilterNode("?name = 'Alice'", join)

    # Optimize - should push filter down to left side
    optimized = optimize_node(filtered)

    # Should be join with filter on left
    assert isinstance(optimized, JoinNode)
    assert isinstance(optimized.left, FilterNode)

    print("✓ Filter pushdown")


def test_cost_model_comparison() -> None:
    """Test cost model with __lt__ comparison."""
    cost1 = QueryCost(io_cost=100.0, cpu_cost=10.0, memory_cost=50.0)
    cost2 = QueryCost(io_cost=200.0, cpu_cost=5.0, memory_cost=30.0)

    # cost1 should be cheaper (lower total)
    assert cost1 < cost2
    assert cost1.total < cost2.total

    print(f"✓ Cost model comparison: {cost1} < {cost2}")


def test_query_cache() -> None:
    """Test memoization with WeakValueDictionary."""
    optimizer = QueryOptimizer()

    p1 = TriplePattern(Variable("s"), URI("rdf:type"), URI("foaf:Person"))
    query = BGPNode((p1,))

    # First call - should compute
    result1 = optimizer.optimize_cached("query1", query)

    # Second call - should use cache
    result2 = optimizer.optimize_cached("query1", query)

    assert result1 is result2  # Same object
    assert QueryCache.size() >= 1

    print(f"✓ Query cache (size={QueryCache.size()})")


def test_expression_trees() -> None:
    """Test expression trees with operator overloading."""
    x = VarExpr("x")
    y = VarExpr("y")

    # Compose with operators
    expr = (x & y) | ~x

    sparql = expr.to_sparql()
    assert "&&" in sparql
    assert "||" in sparql
    assert "!" in sparql

    print(f"✓ Expression trees: {sparql}")


def test_plan_generator() -> None:
    """Test lazy plan generation with iterator protocol."""
    p1 = TriplePattern(Variable("s"), URI("rdf:type"), URI("foaf:Person"))
    p2 = TriplePattern(Variable("s"), URI("foaf:name"), Variable("name"))
    query = BGPNode((p1, p2))

    generator = PlanGenerator(query, max_plans=5)
    plans = list(generator)

    assert len(plans) == 5
    assert all(isinstance(p, QueryPlan) for p in plans)
    assert all(len(p.steps) > 0 for p in plans)

    print(f"✓ Plan generator: {len(plans)} plans")


def test_builder_pattern() -> None:
    """Test chainable builder pattern."""
    query = (
        QueryBuilder()
        .select("s", "name")
        .where(
            TriplePattern(Variable("s"), URI("rdf:type"), URI("foaf:Person")),
            TriplePattern(Variable("s"), URI("foaf:name"), Variable("name")),
        )
        .filter("?name = 'Alice'")
        .build()
    )

    assert isinstance(query, FilterNode)
    assert isinstance(query.child, BGPNode)
    assert len(query.child.patterns) == 2

    print("✓ Builder pattern")


def test_running_statistics() -> None:
    """Test running statistics with online algorithm."""
    stats = RunningStats()

    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    for v in values:
        stats.update(v)

    assert stats.count == 5
    assert abs(stats.mean - 30.0) < 0.01
    assert stats.variance > 0

    print(f"✓ Running statistics: {stats}")


def test_topological_sort() -> None:
    """Test dependency resolution with topological sort."""
    step1 = QueryStep(id="s1", operation="Scan", dependencies=set())
    step2 = QueryStep(id="s2", operation="Scan", dependencies=set())
    step3 = QueryStep(id="s3", operation="Join", dependencies={"s1", "s2"})
    step4 = QueryStep(id="s4", operation="Filter", dependencies={"s3"})

    steps = [step4, step3, step2, step1]  # Unordered
    ordered = order_by_dependencies(steps)

    # s1 and s2 should come before s3, s3 before s4
    s1_idx = next(i for i, s in enumerate(ordered) if s.id == "s1")
    s2_idx = next(i for i, s in enumerate(ordered) if s.id == "s2")
    s3_idx = next(i for i, s in enumerate(ordered) if s.id == "s3")
    s4_idx = next(i for i, s in enumerate(ordered) if s.id == "s4")

    assert s1_idx < s3_idx
    assert s2_idx < s3_idx
    assert s3_idx < s4_idx

    print(f"✓ Topological sort: {[s.id for s in ordered]}")


def test_optimization_context() -> None:
    """Test context manager for optimization scope."""
    hints = OptimizationHints(max_join_reorderings=3, enable_filter_pushdown=True)

    with optimization_context(hints) as ctx:
        assert get_current_context() is ctx
        ctx.record_optimization(10.5)
        ctx.record_optimization(12.3)
        assert ctx.stats.count == 2

    # Context should be cleared
    assert get_current_context() is None

    print(f"✓ Optimization context: {ctx.stats}")


def test_complete_optimization_pipeline() -> None:
    """Test complete optimization pipeline with all techniques."""
    # Build complex query
    query = (
        QueryBuilder()
        .select("person", "name", "age")
        .where(
            TriplePattern(Variable("person"), URI("rdf:type"), URI("foaf:Person")),
            TriplePattern(Variable("person"), URI("foaf:name"), Variable("name")),
            TriplePattern(Variable("person"), URI("foaf:age"), Variable("age")),
        )
        .filter("?age > 18")
        .build()
    )

    # Optimize with hints
    optimizer = QueryOptimizer()
    hints = OptimizationHints(
        prefer_index_scans=True, max_join_reorderings=5, enable_filter_pushdown=True
    )

    result = optimizer.optimize(query, hints)

    assert result.optimization_time_ms > 0
    assert result.estimated_cost.total > 0
    assert isinstance(result.root, (FilterNode, BGPNode))

    # Generate execution plans
    generator = PlanGenerator(result.root, max_plans=3)
    plans = list(generator)

    assert len(plans) == 3

    # Order plan steps by dependencies
    ordered_steps = order_by_dependencies(list(plans[0].steps))
    assert len(ordered_steps) > 0

    print(f"✓ Complete pipeline: {result.estimated_cost}, {len(plans)} plans")


def run_all_tests() -> int:
    """Run all tests and return count."""
    tests = [
        test_pattern_matching_selectivity,
        test_visitor_pattern_optimization,
        test_filter_pushdown,
        test_cost_model_comparison,
        test_query_cache,
        test_expression_trees,
        test_plan_generator,
        test_builder_pattern,
        test_running_statistics,
        test_topological_sort,
        test_optimization_context,
        test_complete_optimization_pipeline,
    ]

    print("=" * 70)
    print("HYPER-ADVANCED SPARQL QUERY OPTIMIZER - TEST SUITE")
    print("=" * 70)

    for test in tests:
        test()

    print("=" * 70)
    print(f"✓ ALL {len(tests)} TESTS PASSED")
    print("=" * 70)

    return len(tests)


# ============================================================================
# ADVANCED TECHNIQUES DEMONSTRATED
# ============================================================================

TECHNIQUES = [
    "1. AST-based Query Transformation (QueryNode, TriplePattern)",
    "2. Visitor Pattern with singledispatch (@optimize_node.register)",
    "3. Memoization with WeakValueDictionary (QueryCache)",
    "4. Expression Trees with Operator Overloading (__and__, __or__, __invert__)",
    "5. Cost Model with __lt__ Comparison (QueryCost ordering)",
    "6. Iterator Protocol for Lazy Plan Generation (PlanGenerator.__next__)",
    "7. Structural Pattern Matching (match/case in analyze_pattern)",
    "8. Dataclass with Custom __hash__ (QueryPlan caching)",
    "9. Context Manager for Execution Scope (optimization_context)",
    "10. Chainable Builder Pattern (QueryBuilder.select().where())",
    "11. Running Statistics (Welford's online algorithm)",
    "12. Topological Sort for Dependencies (graphlib.TopologicalSorter)",
]


if __name__ == "__main__":
    test_count = run_all_tests()

    print("\nADVANCED TECHNIQUES DEMONSTRATED:")
    print("-" * 70)
    for technique in TECHNIQUES:
        print(f"  ✓ {technique}")
    print("-" * 70)
    print(f"\n🚀 {len(TECHNIQUES)} cutting-edge Python techniques demonstrated")
    print(f"✓ {test_count} comprehensive tests passed\n")
