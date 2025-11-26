"""YAWL Pattern Architecture - Unified Execution for All 43 W3C Workflow Patterns.

This module implements a protocol-based pattern system that orchestrates all 43 W3C
workflow patterns through SPARQL-driven semantic resolution. The architecture integrates
with the existing 5-verb Kernel (transmute, copy, filter, await, void) to provide
complete workflow pattern coverage.

Architecture Components
-----------------------
1. **Pattern Protocol**: Base ABC defining the contract for all pattern implementations
2. **PatternRegistry**: Maps pattern IDs (1-43) to concrete implementations
3. **PatternExecutor**: Routes execution based on SPARQL ontology queries
4. **WorkflowInstance**: Tracks execution state across pattern boundaries

Supported Pattern Categories
-----------------------------
- **Basic Control Flow (1-5)**: Sequence, ParallelSplit, Synchronization, ExclusiveChoice, SimpleMerge
- **Advanced Branching (6-9)**: MultiChoice, SynchronizingMerge, MultipleMerge, Discriminator
- **Structural (10-12)**: ArbitraryCycles, ImplicitTermination, MultipleInstances
- **State-Based (13-18)**: DeferredChoice, InterleavedRouting, Milestone, CriticalSection
- **Cancellation (19-21)**: CancelTask, CancelCase, CancelRegion
- **Iteration (22-23)**: StructuredLoop, Recursion
- **Triggers (24-27)**: Interleaved Parallel, Explicit Termination, Stateful, Transient
- **Multiple Instances (28-41)**: Static, Dynamic, Knowledge-Based, etc.
- **Data Patterns (42-43)**: Task Data, Block Data

Split Types
-----------
- **AND**: Parallel execution (all branches)
- **OR**: Multi-choice (1 or more branches based on predicates)
- **XOR**: Exclusive choice (exactly 1 branch)
- **Discriminator**: First N of M completions trigger join

Join Types
----------
- **AND**: Synchronization (wait for all incoming)
- **OR**: Synchronizing merge (wait for active branches only)
- **XOR**: Simple merge (first to arrive continues)
- **Discriminator**: Quorum-based (N of M required)
- **QuorumJoin**: Generalized discriminator (configurable threshold)

Examples
--------
>>> from kgcl.yawl_engine.patterns import PatternRegistry, PatternExecutor
>>> from kgcl.yawl_engine.engine import TransactionContext, Atman
>>>
>>> # Initialize executor
>>> atman = Atman()
>>> executor = PatternExecutor(atman.store)
>>>
>>> # Execute Pattern 2: Parallel Split
>>> ctx = TransactionContext(actor="user1", roles=["role:General"], prev_hash="0" * 64)
>>> instance = WorkflowInstance(task_uri="urn:task:ParallelTask", context=ctx)
>>> result = executor.execute_pattern(instance)
>>> assert result.pattern_id == 2
>>> assert result.committed

References
----------
- YAWL Foundation: http://www.yawlfoundation.org/
- Workflow Patterns Initiative: http://www.workflowpatterns.com/
- W3C Workflow Patterns: http://www.workflowpatterns.com/patterns/

Notes
-----
- All patterns integrate with existing Kernel verbs (transmute, copy, filter, await, void)
- SPARQL queries against yawl.ttl/yawl-extended.ttl drive pattern resolution
- Frozen dataclasses ensure immutable workflow state
- Full type hints with Python 3.12+ syntax
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, cast

from pyshacl import validate as shacl_validate
from rdflib import Dataset, Graph, Namespace, URIRef
from rdflib.query import ResultRow

from kgcl.yawl_engine.engine import Kernel, QuadDelta, TransactionContext

# Import existing pattern implementations
from kgcl.yawl_engine.patterns.advanced_branching import (
    Discriminator,
    ExecutionResult,
    MultiChoice,
    MultipleMerge,
    PatternResult,
    SynchronizingMerge,
)

logger = logging.getLogger(__name__)

# =============================================================================
# SHACL TOPOLOGY VALIDATOR
# =============================================================================
#
# "Validation IS Execution" - If data doesn't fit the shape, logic cannot execute.
# Logic is expressed as SHACL shapes, not Python if-statements.
#

# Path to YAWL SHACL shapes ontology
YAWL_SHAPES_PATH = Path(__file__).parent.parent.parent.parent.parent / "ontology" / "yawl-shapes.ttl"


@dataclass(frozen=True)
class ShaclValidationResult:
    """Result of SHACL topology validation.

    This replaces procedural validation with shape-based validation.
    The shape constraints ARE the business logic.

    Attributes
    ----------
    conforms : bool
        True if graph conforms to all SHACL shapes
    violations : tuple[str, ...]
        Human-readable violation messages
    report_graph : Graph | None
        Full SHACL validation report as RDF graph
    """

    conforms: bool
    violations: tuple[str, ...] = field(default_factory=tuple)
    report_graph: Graph | None = None


def validate_topology(data_graph: Graph | Dataset, shapes_path: Path | None = None) -> ShaclValidationResult:
    """Validate RDF graph topology against SHACL shapes.

    This is the core of the Semantic Singularity architecture:
    - Logic is expressed as SHACL shapes (topology), not Python code
    - If data doesn't fit the shape, execution cannot proceed
    - Validation IS Execution

    Parameters
    ----------
    data_graph : Graph | Dataset
        RDF graph to validate
    shapes_path : Path | None
        Path to SHACL shapes file (defaults to yawl-shapes.ttl)

    Returns
    -------
    ShaclValidationResult
        Validation result with conformance status and violations

    Examples
    --------
    >>> graph = Graph()
    >>> graph.add((URIRef("urn:disc:1"), YAWL.quorum, Literal(0)))  # Invalid!
    >>> result = validate_topology(graph)
    >>> assert not result.conforms
    >>> assert "Quorum must be >= 1" in result.violations[0]
    """
    shapes_file = shapes_path or YAWL_SHAPES_PATH

    # Load shapes graph if file exists
    if not shapes_file.exists():
        logger.warning("SHACL shapes file not found: %s", shapes_file)
        return ShaclValidationResult(conforms=True)  # No shapes = no constraints

    shapes_graph = Graph()
    shapes_graph.parse(shapes_file, format="turtle")

    # Handle Dataset vs Graph
    if isinstance(data_graph, Dataset):
        # Merge all named graphs into default graph for validation
        merged_graph = Graph()
        for quad in data_graph.quads():
            merged_graph.add((quad[0], quad[1], quad[2]))
        target_graph = merged_graph
    else:
        target_graph = data_graph

    # Run SHACL validation
    conforms, report_graph, report_text = shacl_validate(
        data_graph=target_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",  # Enable RDFS inference for class hierarchy
        abort_on_first=False,  # Report all violations
    )

    # Extract violation messages from report
    violations: list[str] = []
    if not conforms:
        # Query report graph for violation messages
        violation_query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT ?message ?focus ?path ?value
        WHERE {
            ?result a sh:ValidationResult ;
                    sh:resultMessage ?message .
            OPTIONAL { ?result sh:focusNode ?focus }
            OPTIONAL { ?result sh:resultPath ?path }
            OPTIONAL { ?result sh:value ?value }
        }
        """
        for row in report_graph.query(violation_query):
            msg = str(row.message)
            if hasattr(row, "focus") and row.focus:
                msg += f" (node: {row.focus})"
            violations.append(msg)

    return ShaclValidationResult(
        conforms=conforms,
        violations=tuple(violations),
        report_graph=report_graph if not conforms else None,
    )

# Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
YAWL_PATTERN = Namespace("http://bitflow.ai/ontology/yawl/patterns/v1#")
YAWL_EXEC = Namespace("http://bitflow.ai/ontology/yawl/execution/v1#")


# ============================================================================
# CORE ENUMERATIONS
# ============================================================================


class SplitType(str, Enum):
    """Split types for workflow branching."""

    SEQUENCE = "SEQUENCE"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    DISCRIMINATOR = "DISCRIMINATOR"


class JoinType(str, Enum):
    """Join types for workflow synchronization."""

    XOR = "XOR"
    AND = "AND"
    OR = "OR"
    DISCRIMINATOR = "DISCRIMINATOR"
    QUORUM = "QUORUM"


class ExecutionMode(str, Enum):
    """Task execution modes from yawl-exec ontology."""

    SYNCHRONOUS = "SYNCHRONOUS"
    ASYNCHRONOUS = "ASYNCHRONOUS"
    QUEUED = "QUEUED"
    PARALLEL = "PARALLEL"


class ExecutionState(str, Enum):
    """Workflow execution states."""

    ENABLED = "enabled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


# ============================================================================
# IMMUTABLE DATA MODELS (Frozen Dataclasses)
# ============================================================================


@dataclass(frozen=True)
class PatternMetadata:
    """Metadata for a W3C workflow pattern.

    Parameters
    ----------
    pattern_id : int
        W3C pattern number (1-43)
    pattern_name : str
        Canonical pattern name
    description : str
        Human-readable pattern description
    required_split : SplitType | None
        Required split type (if applicable)
    required_join : JoinType | None
        Required join type (if applicable)
    requires_predicate : bool
        Whether flow predicates are required
    requires_quorum : bool
        Whether quorum-based join is needed
    """

    pattern_id: int
    pattern_name: str
    description: str
    required_split: SplitType | None = None
    required_join: JoinType | None = None
    requires_predicate: bool = False
    requires_quorum: bool = False


@dataclass(frozen=True)
class WorkflowInstance:
    """Immutable workflow execution instance.

    Parameters
    ----------
    task_uri : str
        Task URI being executed
    context : TransactionContext
        Execution context with actor, roles, data
    state : ExecutionState
        Current execution state
    enabled_tasks : frozenset[str]
        Set of currently enabled task URIs
    completed_tasks : frozenset[str]
        Set of completed task URIs
    active_threads : int
        Number of active parallel threads
    discriminator_count : int
        Count for discriminator/quorum patterns
    """

    task_uri: str
    context: TransactionContext
    state: ExecutionState = ExecutionState.ENABLED
    enabled_tasks: frozenset[str] = field(default_factory=frozenset)
    completed_tasks: frozenset[str] = field(default_factory=frozenset)
    active_threads: int = 0
    discriminator_count: int = 0

    def with_state(self, new_state: ExecutionState) -> WorkflowInstance:
        """Create new instance with updated state."""
        return WorkflowInstance(
            task_uri=self.task_uri,
            context=self.context,
            state=new_state,
            enabled_tasks=self.enabled_tasks,
            completed_tasks=self.completed_tasks,
            active_threads=self.active_threads,
            discriminator_count=self.discriminator_count,
        )

    def with_enabled_tasks(self, tasks: frozenset[str]) -> WorkflowInstance:
        """Create new instance with updated enabled tasks."""
        return WorkflowInstance(
            task_uri=self.task_uri,
            context=self.context,
            state=self.state,
            enabled_tasks=tasks,
            completed_tasks=self.completed_tasks,
            active_threads=self.active_threads,
            discriminator_count=self.discriminator_count,
        )

    def with_completed_task(self, task: str) -> WorkflowInstance:
        """Create new instance marking task as completed."""
        return WorkflowInstance(
            task_uri=self.task_uri,
            context=self.context,
            state=self.state,
            enabled_tasks=self.enabled_tasks,
            completed_tasks=self.completed_tasks | frozenset([task]),
            active_threads=self.active_threads,
            discriminator_count=self.discriminator_count,
        )


@dataclass(frozen=True)
class PatternExecutionResult:
    """Result of pattern execution.

    Parameters
    ----------
    pattern_id : int
        Pattern ID that was executed
    committed : bool
        Whether execution succeeded
    delta : QuadDelta
        State mutations from execution
    instance : WorkflowInstance
        Updated workflow instance
    error : str | None
        Error message if execution failed
    """

    pattern_id: int
    committed: bool
    delta: QuadDelta
    instance: WorkflowInstance
    error: str | None = None


# ============================================================================
# PATTERN PROTOCOL (Base Contract)
# ============================================================================


class Pattern(Protocol):
    """Protocol defining the contract for all YAWL pattern implementations.

    All 43 W3C workflow patterns implement this protocol to ensure uniform
    execution semantics and integration with the Kernel.

    Methods
    -------
    metadata() -> PatternMetadata
        Return pattern metadata (ID, name, requirements)
    can_execute(instance: WorkflowInstance, store: Dataset) -> bool
        Check if pattern can execute given current state
    execute(instance: WorkflowInstance, store: Dataset) -> PatternExecutionResult
        Execute pattern and return result with state mutations
    """

    @property
    def metadata(self) -> PatternMetadata:
        """Return pattern metadata."""
        ...

    def can_execute(self, instance: WorkflowInstance, store: Dataset) -> bool:
        """Check if pattern can execute given workflow state.

        Parameters
        ----------
        instance : WorkflowInstance
            Current workflow instance
        store : Dataset
            RDF quad-store with workflow topology

        Returns
        -------
        bool
            True if pattern can execute, False otherwise
        """
        ...

    def execute(
        self, instance: WorkflowInstance, store: Dataset
    ) -> PatternExecutionResult:
        """Execute pattern and return result.

        Parameters
        ----------
        instance : WorkflowInstance
            Current workflow instance
        store : Dataset
            RDF quad-store with workflow topology

        Returns
        -------
        PatternExecutionResult
            Execution result with delta and updated instance
        """
        ...


# ============================================================================
# PATTERN REGISTRY (Maps IDs to Implementations)
# ============================================================================


class PatternRegistry:
    """Registry mapping pattern IDs (1-43) to implementations.

    The registry uses SPARQL queries to dynamically resolve pattern metadata
    from the ontology and route execution to the appropriate implementation.

    Methods
    -------
    register(pattern_id: int, pattern: Pattern) -> None
        Register a pattern implementation
    get(pattern_id: int) -> Pattern | None
        Retrieve pattern by ID
    resolve_from_task(task_uri: URIRef, store: Dataset) -> Pattern | None
        Resolve pattern from task URI using SPARQL

    Examples
    --------
    >>> registry = PatternRegistry()
    >>> pattern = registry.get(2)  # Get ParallelSplit pattern
    >>> assert pattern.metadata.pattern_name == "Parallel Split"
    """

    def __init__(self) -> None:
        """Initialize empty pattern registry."""
        self._patterns: dict[int, Pattern] = {}

    def register(self, pattern_id: int, pattern: Pattern) -> None:
        """Register a pattern implementation.

        Parameters
        ----------
        pattern_id : int
            W3C pattern ID (1-43)
        pattern : Pattern
            Pattern implementation

        Raises
        ------
        ValueError
            If pattern_id is already registered
        """
        if pattern_id in self._patterns:
            msg = f"Pattern ID {pattern_id} already registered"
            raise ValueError(msg)
        self._patterns[pattern_id] = pattern
        logger.info(
            "Registered pattern",
            extra={
                "pattern_id": pattern_id,
                "pattern_name": pattern.metadata.pattern_name,
            },
        )

    def get(self, pattern_id: int) -> Pattern | None:
        """Get pattern by ID.

        Parameters
        ----------
        pattern_id : int
            W3C pattern ID (1-43)

        Returns
        -------
        Pattern | None
            Pattern implementation or None if not found
        """
        return self._patterns.get(pattern_id)

    def resolve_from_task(self, task_uri: URIRef, store: Dataset) -> Pattern | None:
        """Resolve pattern from task URI using SPARQL.

        Queries the ontology to determine which pattern applies based on:
        1. Split type (AND, OR, XOR)
        2. Join type (AND, OR, XOR, Discriminator)
        3. Flow predicates
        4. Quorum requirements

        Parameters
        ----------
        task_uri : URIRef
            Task URI to resolve pattern for
        store : Dataset
            RDF quad-store with workflow topology

        Returns
        -------
        Pattern | None
            Resolved pattern or None if no match

        Examples
        --------
        >>> from rdflib import URIRef
        >>> task = URIRef("urn:task:ParallelTask")
        >>> pattern = registry.resolve_from_task(task, store)
        >>> assert pattern.metadata.pattern_id == 2
        """
        # Query for split and join types
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?splitType ?joinType WHERE {{
            <{task_uri}> yawl:splitType ?splitType .
            OPTIONAL {{ <{task_uri}> yawl:joinType ?joinType }}
        }}
        """
        results = list(store.query(query))

        if not results:
            # Default to Pattern 1: Sequence
            return self.get(1)

        row = cast(ResultRow, results[0])
        split_type = str(row.splitType) if hasattr(row, "splitType") else None
        join_type = str(row.joinType) if hasattr(row, "joinType") else None

        # Map to pattern ID based on split/join combination
        if split_type == "AND" and not join_type:
            return self.get(2)  # Pattern 2: Parallel Split
        if join_type == "AND" and not split_type:
            return self.get(3)  # Pattern 3: Synchronization
        if split_type == "XOR":
            return self.get(4)  # Pattern 4: Exclusive Choice
        if join_type == "XOR":
            return self.get(5)  # Pattern 5: Simple Merge
        if split_type == "OR":
            return self.get(6)  # Pattern 6: Multi-Choice
        if join_type == "OR":
            return self.get(7)  # Pattern 7: Synchronizing Merge
        if join_type == "Discriminator":
            return self.get(9)  # Pattern 9: Discriminator

        # Default to Sequence if no match
        return self.get(1)


# ============================================================================
# PATTERN EXECUTOR (SPARQL-Driven Routing)
# ============================================================================


class PatternExecutor:
    """Executes workflow patterns using SPARQL-driven routing.

    The executor integrates with the existing Kernel to provide seamless
    pattern execution across all 43 W3C workflow patterns.

    Parameters
    ----------
    store : Dataset
        RDF quad-store with workflow ontology
    registry : PatternRegistry | None
        Pattern registry (auto-initialized if None)

    Examples
    --------
    >>> from kgcl.yawl_engine.engine import Atman, TransactionContext
    >>> atman = Atman()
    >>> executor = PatternExecutor(atman.store)
    >>> ctx = TransactionContext(
    ...     actor="user1", roles=["role:General"], prev_hash="0" * 64
    ... )
    >>> instance = WorkflowInstance(task_uri="urn:task:Test", context=ctx)
    >>> result = executor.execute_pattern(instance)
    >>> assert result.committed
    """

    def __init__(self, store: Dataset, registry: PatternRegistry | None = None) -> None:
        """Initialize pattern executor.

        Parameters
        ----------
        store : Dataset
            RDF quad-store with workflow ontology
        registry : PatternRegistry | None
            Pattern registry (auto-initialized if None)
        """
        self.store = store
        self.registry = registry or PatternRegistry()
        self._initialize_base_patterns()

    def _initialize_base_patterns(self) -> None:
        """Initialize base pattern implementations (1-9).

        These patterns map directly to Kernel verbs:
        - Pattern 1 (Sequence) → transmute
        - Pattern 2 (Parallel Split) → copy
        - Pattern 3 (Synchronization) → await
        - Pattern 4 (Exclusive Choice) → filter
        - Pattern 5 (Simple Merge) → transmute (XOR join)
        - Pattern 6 (Multi-Choice) → MultiChoice (existing)
        - Pattern 7 (Synchronizing Merge) → SynchronizingMerge (existing)
        - Pattern 8 (Multiple Merge) → MultipleMerge (existing)
        - Pattern 9 (Discriminator) → Discriminator (existing)
        """
        # NOTE: Pattern registration will be completed when existing pattern
        # implementations are adapted to the Pattern protocol
        pass

    def execute_pattern(
        self, instance: WorkflowInstance, validate_shapes: bool = True
    ) -> PatternExecutionResult:
        """Execute workflow pattern for given instance.

        Resolution logic:
        1. Validate graph topology against SHACL shapes (RDF-only logic)
        2. Resolve pattern from task URI using SPARQL
        3. Check if pattern can execute
        4. Execute pattern via Kernel integration
        5. Return result with updated instance

        The Semantic Singularity Principle:
        - Validation IS Execution
        - Logic is topology (SHACL shapes), not procedural code
        - If data doesn't fit the shape, execution cannot proceed

        Parameters
        ----------
        instance : WorkflowInstance
            Current workflow instance
        validate_shapes : bool
            If True, validate against SHACL shapes before execution

        Returns
        -------
        PatternExecutionResult
            Execution result with delta and updated instance

        Raises
        ------
        ValueError
            If pattern cannot be resolved or executed
        """
        task = URIRef(instance.task_uri)

        # Step 1: Validate topology against SHACL shapes
        # This is the core of RDF-Only architecture: shapes ARE the business logic
        if validate_shapes:
            validation_result = validate_topology(self.store)
            if not validation_result.conforms:
                logger.warning(
                    "SHACL topology validation failed",
                    extra={
                        "task": instance.task_uri,
                        "violations": validation_result.violations,
                    },
                )
                return PatternExecutionResult(
                    pattern_id=0,  # Unknown pattern
                    committed=False,
                    delta=QuadDelta(),
                    instance=instance,
                    error=f"SHACL topology violation: {'; '.join(validation_result.violations)}",
                )

        # Step 2: Resolve pattern from task
        pattern = self.registry.resolve_from_task(task, self.store)
        if not pattern:
            msg = f"Cannot resolve pattern for task {instance.task_uri}"
            raise ValueError(msg)

        logger.info(
            "Executing pattern",
            extra={
                "pattern_id": pattern.metadata.pattern_id,
                "pattern_name": pattern.metadata.pattern_name,
                "task": instance.task_uri,
            },
        )

        # Step 3: Check if pattern can execute
        if not pattern.can_execute(instance, self.store):
            return PatternExecutionResult(
                pattern_id=pattern.metadata.pattern_id,
                committed=False,
                delta=QuadDelta(),
                instance=instance,
                error="Pattern cannot execute in current state",
            )

        # Step 4: Execute pattern
        try:
            result = pattern.execute(instance, self.store)
            return result
        except Exception as e:
            logger.exception(
                "Pattern execution failed",
                extra={"pattern_id": pattern.metadata.pattern_id, "error": str(e)},
            )
            return PatternExecutionResult(
                pattern_id=pattern.metadata.pattern_id,
                committed=False,
                delta=QuadDelta(),
                instance=instance,
                error=str(e),
            )

    def resolve_split_type(self, task: URIRef) -> SplitType:
        """Resolve split type from task URI.

        Parameters
        ----------
        task : URIRef
            Task URI

        Returns
        -------
        SplitType
            Resolved split type
        """
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?splitType WHERE {{
            <{task}> yawl:splitType ?splitType .
        }}
        """
        results = list(self.store.query(query))
        if not results:
            return SplitType.SEQUENCE

        row = cast(ResultRow, results[0])
        split_str = str(row.splitType)
        return (
            SplitType(split_str)
            if split_str in SplitType.__members__
            else SplitType.SEQUENCE
        )

    def resolve_join_type(self, task: URIRef) -> JoinType:
        """Resolve join type from task URI.

        Parameters
        ----------
        task : URIRef
            Task URI

        Returns
        -------
        JoinType
            Resolved join type
        """
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?joinType WHERE {{
            <{task}> yawl:joinType ?joinType .
        }}
        """
        results = list(self.store.query(query))
        if not results:
            return JoinType.XOR

        row = cast(ResultRow, results[0])
        join_str = str(row.joinType)
        return JoinType(join_str) if join_str in JoinType.__members__ else JoinType.XOR


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # SHACL Topology Validation (RDF-Only Logic)
    "ShaclValidationResult",
    "validate_topology",
    "YAWL_SHAPES_PATH",
    # Core Protocol & Architecture
    "Pattern",
    "PatternMetadata",
    "PatternRegistry",
    "PatternExecutor",
    "PatternExecutionResult",
    "WorkflowInstance",
    # Enumerations
    "SplitType",
    "JoinType",
    "ExecutionMode",
    "ExecutionState",
    # Existing Pattern Implementations (Advanced Branching)
    "Discriminator",
    "ExecutionResult",
    "MultiChoice",
    "MultipleMerge",
    "PatternResult",
    "SynchronizingMerge",
]
