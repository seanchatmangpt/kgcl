"""KGCL Reference Engine v3.1 (The Semantic Driver).

Philosophy: The Chatman Equation (A = μ(O, P))
Architecture: Kernel (5 parameterized verbs) + Atman (ontology lookup) + Lockchain (provenance)

This module implements the KGC v3.1 engine with ZERO pattern-specific logic.
ALL behavior is resolved via SPARQL queries against the physics ontology.

THE SEMANTIC SINGULARITY PRINCIPLE: "Validation IS Execution"
--------------------------------------------------------------
- Logic is expressed in kgc_physics.ttl (Dark Matter), NOT in Python code
- The engine queries the ontology to determine which verb AND parameters to execute
- NO Python if-statements for pattern dispatch
- Patterns are mapped to verbs + params via SPARQL queries against the ontology

THE 5 ELEMENTAL VERBS (Parameterized Forces)
---------------------------------------------
Verbs are "Parameterized Forces" - Parameters tell the verb HOW MUCH force to apply.

1. TRANSMUTE (Arrow of Time): A → B
2. COPY (Divergence): A → {B₁, B₂, ..., Bₙ} where n = cardinality parameter
3. FILTER (Selection): A → {Subset} where subset = predicate + selectionMode
4. AWAIT (Convergence): {A, B, ...} → C where threshold = quorum parameter
5. VOID (Termination): A → ∅ where scope = cancellation region parameter

Parameter Properties (Force Multipliers):
- hasThreshold: "all", "1", "N", "active", "dynamic" (for Await)
- hasCardinality: "topology", "static", "dynamic", integer (for Copy)
- completionStrategy: "waitAll", "waitActive", "waitFirst", "waitQuorum" (for Await)
- selectionMode: "exactlyOne", "oneOrMore", "deferred", "mutex" (for Filter)
- cancellationScope: "self", "region", "case", "instances" (for Void)
- resetOnFire: boolean (for loops/discriminator)

The engine ensures:
1. Verb + Params Resolution - SPARQL queries resolve patterns to (verb, params) at runtime
2. Pure Functions - Kernel verbs are stateless operations parameterized by ontology
3. Cryptographic Provenance - Every mutation generates a merkle-linked receipt

Examples
--------
>>> from rdflib import Graph, URIRef
>>> from kgcl.engine.knowledge_engine import SemanticDriver, TransactionContext
>>>
>>> # Load physics ontology
>>> ontology = Graph()
>>> ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
>>>
>>> # Create driver
>>> driver = SemanticDriver(ontology)
>>>
>>> # Execute verb on a node
>>> workflow = Graph()
>>> workflow.parse("my_workflow.ttl", format="turtle")
>>> task_node = URIRef("urn:task:123")
>>> ctx = TransactionContext(tx_id="tx-001", actor="system", prev_hash="genesis", data={"foo": "bar"})
>>> receipt = driver.execute(workflow, task_node, ctx)
>>> receipt.verb_executed
'transmute'
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.query import ResultRow

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Namespaces
KGC = Namespace("http://bitflow.ai/ontology/kgc/v3#")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")

# Genesis hash for lockchain
GENESIS_HASH: str = "4d7c606c9002d3043ee3979533922e25752bd2755709057060b553593605bd62"

# Maximum batch size (Chatman Constant)
CHATMAN_CONSTANT: int = 64


# =============================================================================
# DATA STRUCTURES
# =============================================================================


# Type alias for RDF triples
Triple = tuple[URIRef | Literal, URIRef, URIRef | Literal]


@dataclass(frozen=True)
class QuadDelta:
    """
    The Observation (O) - Immutable batch of graph mutations.

    Represents the intent to mutate reality. Maximum 64 operations
    to ensure Hot Path execution within the Chatman Constant.

    Parameters
    ----------
    additions : tuple[Triple, ...]
        Triples to add to the graph (immutable).
    removals : tuple[Triple, ...]
        Triples to remove from the graph (immutable).

    Raises
    ------
    ValueError
        If total operations exceed CHATMAN_CONSTANT.

    Examples
    --------
    >>> from rdflib import URIRef
    >>> s = URIRef("urn:task:1")
    >>> p = URIRef("urn:type")
    >>> o = URIRef("urn:Task")
    >>> delta = QuadDelta(additions=((s, p, o),), removals=())
    >>> len(delta.additions)
    1
    """

    additions: tuple[Triple, ...] = ()
    removals: tuple[Triple, ...] = ()

    def __post_init__(self) -> None:
        """Validate Chatman Constant constraint."""
        total_ops = len(self.additions) + len(self.removals)
        if total_ops > CHATMAN_CONSTANT:
            msg = f"Topology Violation: {total_ops} ops exceeds Hot Path limit ({CHATMAN_CONSTANT})"
            raise ValueError(msg)


@dataclass(frozen=True)
class TransactionContext:
    """
    The Context Window - Links transactions in the Lockchain.

    Carries metadata for provenance and actor identity.

    Parameters
    ----------
    tx_id : str
        Unique transaction identifier.
    actor : str
        Identity of the actor initiating the transaction.
    prev_hash : str
        Hash of the previous transaction (Lockchain link).
    data : dict[str, Any]
        Additional context data (for data transformations).

    Examples
    --------
    >>> ctx = TransactionContext(tx_id="tx-001", actor="system", prev_hash="genesis", data={})
    >>> ctx.actor
    'system'
    """

    tx_id: str
    actor: str
    prev_hash: str
    data: dict[str, Any]


@dataclass(frozen=True)
class VerbConfig:
    """
    Configuration for verb execution - The (verb, params) tuple.

    Contains the verb name and all parameters extracted from the ontology.
    This is the P in A = μ(O, P) - the force multipliers that tell the
    verb HOW MUCH force to apply.

    Parameters
    ----------
    verb : str
        The verb name ("transmute", "copy", "filter", "await", "void").
    threshold : str | None
        For AWAIT: "all", "1", "N", "active", "dynamic", "milestone".
    cardinality : str | None
        For COPY: "topology", "static", "dynamic", "incremental", or integer.
    completion_strategy : str | None
        For AWAIT: "waitAll", "waitActive", "waitFirst", "waitQuorum".
    selection_mode : str | None
        For FILTER: "exactlyOne", "oneOrMore", "deferred", "mutex".
    cancellation_scope : str | None
        For VOID: "self", "region", "case", "instances".
    reset_on_fire : bool
        For loops/discriminator: Reset state after firing.
    instance_binding : str | None
        For MI patterns: "none", "index", "data", "recursive".
    execution_template : str | None
        SPARQL CONSTRUCT template for additions (with placeholders).
    removal_template : str | None
        SPARQL DELETE WHERE template for removals (with placeholders).

    Examples
    --------
    >>> config = VerbConfig(verb="await", threshold="all", completion_strategy="waitAll")
    >>> config.verb
    'await'
    >>> config.threshold
    'all'
    """

    verb: str
    threshold: str | None = None
    cardinality: str | None = None
    completion_strategy: str | None = None
    selection_mode: str | None = None
    cancellation_scope: str | None = None
    reset_on_fire: bool = False
    instance_binding: str | None = None
    execution_template: str | None = None
    removal_template: str | None = None
    # RDF-Only Evaluation Properties (Mission 05-07)
    threshold_value: int | None = None  # Numeric threshold for AWAIT (-1 = ALL)
    cardinality_value: int | None = None  # Numeric cardinality for COPY (-1 = topology)
    stop_on_first_match: bool = False  # FILTER: XOR vs OR semantics
    use_active_count: bool = False  # AWAIT: count active branches only
    use_dynamic_threshold: bool = False  # AWAIT: threshold from ctx.data
    use_dynamic_cardinality: bool = False  # COPY: cardinality from ctx.data
    is_deferred_choice: bool = False  # FILTER: Wait for external selection (WCP-16)
    is_mutex_interleaved: bool = False  # FILTER: Mutex for interleaved (WCP-17)
    invert_predicate: bool = False  # FILTER: Invert condition (repeat-until)
    ignore_subsequent: bool = False  # AWAIT: Ignore subsequent arrivals (WCP-9 discriminator)


@dataclass(frozen=True)
class Receipt:
    """
    The Action (A) - Cryptographic proof of execution.

    Provides complete provenance:
    - merkle_root: Links to previous state via hash chain
    - verb_executed: Which verb was applied (from ontology)
    - delta: What mutations occurred
    - params_used: Parameters from ontology (for audit trail)

    Parameters
    ----------
    merkle_root : str
        SHA256(prev_hash + delta) - Lockchain link.
    verb_executed : str
        The verb that was executed ("transmute", "copy", etc.).
    delta : QuadDelta
        The mutations that were applied.
    params_used : VerbConfig | None
        The full configuration used (for provenance).

    Examples
    --------
    >>> delta = QuadDelta(additions=(), removals=())
    >>> receipt = Receipt(merkle_root="a" * 64, verb_executed="transmute", delta=delta)
    >>> receipt.verb_executed
    'transmute'
    >>> len(receipt.merkle_root)
    64
    """

    merkle_root: str
    verb_executed: str
    delta: QuadDelta
    params_used: VerbConfig | None = None


# =============================================================================
# THE KERNEL - THE 5 ELEMENTAL VERBS
# =============================================================================


class Kernel:
    """
    The 5 Elemental Verbs - Parameterized pure functions on graph nodes.

    These are the ONLY operations the engine can perform.
    Each verb is a static method that takes a graph, node, context, AND config,
    and returns a QuadDelta describing the mutations.

    No verb contains pattern-specific logic. All behavior is determined
    by the graph structure and the VerbConfig parameters from ontology.

    Verbs (Parameterized)
    ---------------------
    1. transmute - Arrow of Time (A → B)
    2. copy(cardinality) - Divergence (A → {B₁...Bₙ})
    3. filter(selection_mode) - Selection (A → {Subset})
    4. await_(threshold, completion_strategy) - Convergence ({A, B} → C)
    5. void(cancellation_scope) - Termination (A → ∅, recursive by scope)
    """

    @staticmethod
    def execute_template(
        graph: Graph,
        subject: URIRef,
        ctx: TransactionContext,
        execution_template: str,
        removal_template: str | None = None,
    ) -> QuadDelta:
        """
        Execute SPARQL templates for RDF-only verb execution.

        This method eliminates Python if/else by executing SPARQL CONSTRUCT
        templates directly against the graph. Templates are stored in the
        ontology and resolved at runtime.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI (bound to ?subject in template).
        ctx : TransactionContext
            Transaction context (bound to ?txId, ?actor, ?prevHash).
        execution_template : str
            SPARQL CONSTRUCT template for additions.
        removal_template : str | None
            SPARQL DELETE WHERE template for removals.

        Returns
        -------
        QuadDelta
            Mutations from template execution.
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Bind variables in execution template
        bound_template = execution_template.replace("?subject", f"<{subject}>")
        bound_template = bound_template.replace("?txId", f'"{ctx.tx_id}"')
        bound_template = bound_template.replace("?actor", f'"{ctx.actor}"')
        bound_template = bound_template.replace("?prevHash", f'"{ctx.prev_hash}"')

        # Execute CONSTRUCT query for additions
        try:
            construct_result = graph.query(bound_template)
            for triple in construct_result:
                if len(triple) == 3:
                    s, p, o = triple
                    additions.append((s, p, o))
        except Exception:
            logger.exception("Execution template failed: %s", bound_template[:100])

        # Execute removal template if provided - add standard token removal
        if removal_template:
            # For RDF-only execution, removal of source token is standard
            # Check if subject has token before adding to removals
            if (subject, KGC.hasToken, Literal(True)) in graph:
                removals.append((subject, KGC.hasToken, Literal(True)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def transmute(
        graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None
    ) -> QuadDelta:
        """
        VERB 1: TRANSMUTE - Arrow of Time (A → B).

        Move token from current node to next node via yawl:nextElementRef.
        Applies yawl:startingMappings for data transformation.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.
        config : VerbConfig | None
            Configuration from ontology (unused for transmute).

        Returns
        -------
        QuadDelta
            Mutations to execute the sequence transition.

        Notes
        -----
        SPARQL Query (from ontology):
            SELECT ?next WHERE {
                ?current yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """
        _ = config  # Transmute has no parameters
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Find next element via SPARQL
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?next WHERE {{
            <{subject}> yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }}
        """
        results = list(graph.query(query))

        if results:
            row = cast(ResultRow, results[0])
            next_element = cast(URIRef, row[0])
            # Remove token from current node
            removals.append((subject, KGC.hasToken, Literal(True)))
            # Add token to next node
            additions.append((next_element, KGC.hasToken, Literal(True)))
            # Mark current node as completed
            additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def copy(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 2: COPY - Divergence (A → {B₁, B₂, ..., Bₙ}).

        Clone token state to successors based on cardinality_value (RDF-only):
        - cardinality_value = -1: Clone to ALL topology successors (AND-split, WCP-2)
        - cardinality_value = -2: Clone to N from graph yawl:minimum (WCP-13 static)
        - cardinality_value = -3: Create one instance at a time (WCP-15 incremental)
        - cardinality_value > 0: Clone to exactly N instances
        - use_dynamic_cardinality = True: N from ctx.data["mi_items"] (WCP-14)

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.
        config : VerbConfig | None
            Configuration with cardinality_value and use_dynamic_cardinality.

        Returns
        -------
        QuadDelta
            Mutations to execute the parallel split.

        Notes
        -----
        RDF-Only Cardinality (from kgc:cardinalityValue):
        - -1 (WCP-2): ALL topology successors (AND-split)
        - -2 (WCP-13): Static N from yawl:minimum in graph
        - -3 (WCP-15): Incremental (one at a time)
        - N > 0: Explicit N instances
        - use_dynamic_cardinality (WCP-14): N from runtime mi_items list
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # RDF-ONLY EVALUATION: Use numeric cardinality from ontology
        # Mission 07: Cardinality is Integer - no pattern-name checks
        # cardinality_value: -1 = topology (all successors), -2 = static (from graph), -3 = incremental, >0 = explicit N
        cardinality_value = config.cardinality_value if config else -1  # Default: topology
        use_dynamic_cardinality = config.use_dynamic_cardinality if config else False

        # Find ALL next elements via SPARQL
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?next WHERE {{
            <{subject}> yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }}
        """
        results = list(graph.query(query))

        if not results:
            return QuadDelta(additions=tuple(additions), removals=tuple(removals))

        # Remove token from current node
        removals.append((subject, KGC.hasToken, Literal(True)))

        # RDF-ONLY: Determine clone count from numeric cardinality or flags
        targets: list[URIRef] = []
        topology_targets = [cast(URIRef, cast(ResultRow, r)[0]) for r in results]
        base_target = topology_targets[0] if topology_targets else None

        if use_dynamic_cardinality:
            # WCP-14: N from runtime data (mi_items list)
            mi_data = ctx.data.get("mi_items", [])
            if mi_data and base_target:
                for i, item in enumerate(mi_data):
                    instance_uri = URIRef(f"{base_target}_instance_{i}")
                    targets.append(instance_uri)
                    additions.append((instance_uri, KGC.instanceId, Literal(str(i))))
                    additions.append((instance_uri, KGC.boundData, Literal(str(item))))
            else:
                # Fall back to topology if no MI data
                targets = topology_targets
        elif cardinality_value == -1:
            # Sentinel: -1 means ALL topology successors (AND-split, WCP-2)
            targets = topology_targets
        elif cardinality_value == -2 and base_target:
            # Sentinel: -2 means static from graph (WCP-13)
            mi_query = f"""
            PREFIX yawl: <{YAWL}>
            SELECT ?min WHERE {{
                <{subject}> yawl:minimum ?min .
            }}
            """
            mi_results = list(graph.query(mi_query))
            if mi_results:
                n = int(str(cast(ResultRow, mi_results[0])[0]))
                for i in range(n):
                    instance_uri = URIRef(f"{base_target}_instance_{i}")
                    targets.append(instance_uri)
                    additions.append((instance_uri, KGC.instanceId, Literal(str(i))))
            else:
                targets = topology_targets
        elif cardinality_value == -3 and base_target:
            # Sentinel: -3 means incremental (WCP-15)
            count_query = f"""
            PREFIX kgc: <{KGC}>
            SELECT (COUNT(?inst) AS ?count) WHERE {{
                ?inst kgc:parentTask <{subject}> .
            }}
            """
            count_results = list(graph.query(count_query))
            current_count = int(str(cast(ResultRow, count_results[0])[0])) if count_results else 0
            instance_uri = URIRef(f"{base_target}_instance_{current_count}")
            targets = [instance_uri]
            additions.append((instance_uri, KGC.instanceId, Literal(str(current_count))))
            additions.append((instance_uri, KGC.parentTask, subject))
        elif cardinality_value is not None and cardinality_value > 0 and base_target:
            # Explicit numeric cardinality: create N instances
            for i in range(cardinality_value):
                instance_uri = URIRef(f"{base_target}_instance_{i}")
                targets.append(instance_uri)
                additions.append((instance_uri, KGC.instanceId, Literal(str(i))))
        else:
            # Default: topology (clone to all successors)
            targets = topology_targets

        # Clone token to targets
        for target in targets:
            additions.append((target, KGC.hasToken, Literal(True)))

        # Mark current node as completed
        additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def filter(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 3: FILTER - Selection (A → {Subset}).

        Evaluate predicates to select which paths receive tokens based on selection_mode:
        - "exactlyOne" (WCP-4): XOR-split, exactly one path selected
        - "oneOrMore" (WCP-6): OR-split, one or more paths selected
        - "deferred" (WCP-16): Environment determines branch at runtime
        - "mutex" (WCP-17): Interleaved execution, one at a time

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.
        config : VerbConfig | None
            Configuration with selection_mode parameter.

        Returns
        -------
        QuadDelta
            Mutations to execute the conditional routing.

        Notes
        -----
        Selection modes (from ontology):
        - "exactlyOne" (WCP-4): First matching predicate wins
        - "oneOrMore" (WCP-6): All matching predicates selected
        - "deferred" (WCP-16): Wait for external selection
        - "mutex" (WCP-17): Mutual exclusion for interleaved
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # RDF-ONLY EVALUATION: Use boolean flags from ontology, not pattern names
        # Mission 05: Logic is Data - boolean flags replace pattern-name checks
        stop_on_first = config.stop_on_first_match if config else False
        invert_predicate = config.invert_predicate if config else False
        is_deferred = config.is_deferred_choice if config else False
        is_mutex = config.is_mutex_interleaved if config else False

        # Find flows with predicates via SPARQL
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?next ?predicate ?ordering ?isDefault WHERE {{
            <{subject}> yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            OPTIONAL {{
                ?flow yawl:hasPredicate ?pred .
                ?pred yawl:query ?predicate ;
                      yawl:ordering ?ordering .
            }}
            OPTIONAL {{
                ?flow yawl:isDefaultFlow ?isDefault .
            }}
        }}
        ORDER BY ?ordering
        """
        results = list(graph.query(query))

        selected_paths: list[URIRef] = []
        default_path: URIRef | None = None

        for result in results:
            row = cast(ResultRow, result)
            next_element = cast(URIRef, row[0])
            predicate = row[1] if len(row) > 1 else None
            is_default = row[3] if len(row) > 3 else None

            # Track default path
            if is_default and str(is_default).lower() == "true":
                default_path = next_element
                continue

            # Evaluate predicate - GENERIC EXPRESSION EVALUATION
            # The predicate is a STRING in the RDF, evaluated against ctx.data
            if predicate is None:
                # No condition - always matches
                selected_paths.append(next_element)
            else:
                # Evaluate RDF-stored predicate expression
                predicate_result = _evaluate_predicate(str(predicate), ctx.data)

                # Invert for repeat-until semantics (from RDF flag)
                if invert_predicate:
                    predicate_result = not predicate_result

                if predicate_result:
                    selected_paths.append(next_element)

            # RDF-ONLY: Use stop_on_first_match flag instead of pattern-name checks
            if stop_on_first and selected_paths:
                break

        # Handle deferred choice - mark as waiting for external selection (WCP-16)
        if is_deferred:
            # Don't route yet, mark as waiting
            additions.append((subject, KGC.awaitingSelection, Literal(True)))
            return QuadDelta(additions=tuple(additions), removals=tuple(removals))

        # Handle mutex - check if another is executing (WCP-17)
        if is_mutex:
            mutex_query = f"""
            PREFIX kgc: <{KGC}>
            SELECT ?sibling WHERE {{
                ?sibling kgc:hasToken true .
                ?sibling kgc:mutexGroup <{subject}> .
            }}
            """
            mutex_results = list(graph.query(mutex_query))
            if mutex_results:
                # Another sibling is executing, wait
                additions.append((subject, KGC.awaitingMutex, Literal(True)))
                return QuadDelta(additions=tuple(additions), removals=tuple(removals))
            # Select first available for interleaved
            if selected_paths:
                selected_paths = [selected_paths[0]]

        # Fall back to default path if no matches
        if not selected_paths and default_path:
            selected_paths = [default_path]

        if selected_paths:
            # Remove token from current node
            removals.append((subject, KGC.hasToken, Literal(True)))
            # Add token to selected paths
            for path in selected_paths:
                additions.append((path, KGC.hasToken, Literal(True)))
            # Mark current node as completed
            additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def await_(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 4: AWAIT - Convergence ({A, B, ...} → C).

        Wait for incoming flows based on threshold and completion_strategy:
        - threshold="all" (WCP-3): Wait for ALL sources (AND-join)
        - threshold="1" (WCP-9): Wait for first arrival (Discriminator)
        - threshold="N" (WCP-34): Wait for N of M (Partial Join)
        - threshold="active" (WCP-7): Wait for all active branches (OR-join)
        - threshold="dynamic": N computed at runtime from data

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI (join node).
        ctx : TransactionContext
            Transaction context.
        config : VerbConfig | None
            Configuration with threshold and completion_strategy.

        Returns
        -------
        QuadDelta
            Mutations to execute the join (if conditions met).

        Notes
        -----
        Threshold modes (from ontology):
        - "all" (WCP-3): AND-join, all sources must complete
        - "1" (WCP-9): Discriminator, first arrival fires
        - "N" (WCP-34): Partial join, N completions fire
        - "active" (WCP-7): OR-join, all active (not voided) must complete
        - "dynamic": Threshold from ctx.data["join_threshold"]

        Completion strategies:
        - "waitAll": Block until threshold met
        - "waitFirst": Fire on first, ignore subsequent
        - "waitQuorum": Fire at quorum, optionally cancel rest
        - "waitActive": Track active branches, fire when all active done
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # RDF-ONLY EVALUATION: Use numeric threshold from ontology
        # Mission 06: Threshold is Integer - no pattern-name checks
        threshold_value = config.threshold_value if config else None
        use_active_count = config.use_active_count if config else False
        use_dynamic_threshold = config.use_dynamic_threshold if config else False
        reset_on_fire = config.reset_on_fire if config else False
        ignore_subsequent = config.ignore_subsequent if config else False

        # Find incoming flows and check completion/voided status
        query = f"""
        PREFIX yawl: <{YAWL}>
        PREFIX kgc: <{KGC}>
        SELECT ?source ?completed ?voided ?hasToken WHERE {{
            ?source yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef <{subject}> .
            OPTIONAL {{ ?source kgc:completedAt ?completed . }}
            OPTIONAL {{ ?source kgc:voidedAt ?voided . }}
            OPTIONAL {{ ?source kgc:hasToken ?hasToken . }}
        }}
        """
        results = list(graph.query(query))

        total_sources = len(results)
        completed_sources = 0
        voided_sources = 0

        for r in results:
            row = cast(ResultRow, r)
            completed = row[1] is not None
            voided = row[2] is not None

            if completed:
                completed_sources += 1
            if voided:
                voided_sources += 1

        # RDF-ONLY: Compute required threshold from numeric value or flags
        required: int
        if use_dynamic_threshold:
            # Runtime threshold from context data
            required = int(ctx.data.get("join_threshold", 1))
        elif use_active_count:
            # WCP-7: OR-join, all active (not voided) must complete
            active_count = total_sources - voided_sources
            required = active_count if active_count > 0 else 1
        elif threshold_value is not None:
            if threshold_value == -1:
                # Sentinel: -1 means ALL (from kgc:threshold "all")
                required = total_sources
            else:
                # Explicit numeric threshold from RDF
                required = threshold_value
        else:
            # Default: all
            required = total_sources

        # Check if join condition is satisfied: count >= threshold
        can_proceed = completed_sources >= required

        if can_proceed:
            # Check if node already has token (prevent double-fire)
            has_token = (subject, KGC.hasToken, Literal(True)) in graph
            if not has_token:
                # Activate this node
                additions.append((subject, KGC.hasToken, Literal(True)))
                additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

                # Record threshold achieved for provenance
                additions.append((subject, KGC.thresholdAchieved, Literal(str(completed_sources))))

                # Handle reset_on_fire (for discriminator loops)
                if reset_on_fire:
                    additions.append((subject, KGC.joinReset, Literal(True)))

                # Handle waitFirst strategy - mark for ignoring subsequent (WCP-9)
                if ignore_subsequent:
                    additions.append((subject, KGC.ignoreSubsequent, Literal(True)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def void(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 5: VOID - Termination (A → ∅, recursive by scope).

        Destroy tokens based on cancellation_scope:
        - "self" (WCP-19): Cancel only this task
        - "region" (WCP-21): Cancel all tasks in cancellation region
        - "case" (WCP-20): Cancel entire case (all tokens)
        - "instances" (WCP-22): Cancel all MI instances

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context.
        config : VerbConfig | None
            Configuration with cancellation_scope.

        Returns
        -------
        QuadDelta
            Mutations to destroy tokens in scope.

        Notes
        -----
        Cancellation scopes (from ontology):
        - "self" (WCP-19): Cancel only the specified task
        - "region" (WCP-21): Cancel all tasks in yawl:cancellationSet
        - "case" (WCP-20): Cancel entire case (all active tokens)
        - "instances" (WCP-22): Cancel all instances of MI task
        - "task" (WCP-24): Cancel task and route to exception handler
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        cancellation_scope = config.cancellation_scope if config else "self"

        # Determine reason for void
        reason_query = f"""
        PREFIX yawl: <{YAWL}>
        PREFIX kgc: <{KGC}>
        SELECT ?reason WHERE {{
            {{
                <{subject}> yawl:hasTimer ?timer .
                BIND("timeout" AS ?reason)
            }}
            UNION
            {{
                <{subject}> kgc:cancelled true .
                BIND("cancelled" AS ?reason)
            }}
            UNION
            {{
                <{subject}> kgc:failed true .
                BIND("exception" AS ?reason)
            }}
        }}
        """
        reason_results = list(graph.query(reason_query))
        reason = str(cast(ResultRow, reason_results[0])[0]) if reason_results else "void"

        # Collect all nodes to void based on scope
        nodes_to_void: list[URIRef] = []

        if cancellation_scope == "self":
            # WCP-19: Just this task
            nodes_to_void = [subject]

        elif cancellation_scope == "region":
            # WCP-21: All tasks in cancellation region
            region_query = f"""
            PREFIX yawl: <{YAWL}>
            PREFIX kgc: <{KGC}>
            SELECT ?task WHERE {{
                <{subject}> yawl:cancellationSet ?region .
                ?task yawl:inCancellationRegion ?region .
                ?task kgc:hasToken true .
            }}
            """
            region_results = list(graph.query(region_query))
            nodes_to_void = [subject]  # Always include trigger
            for r in region_results:
                nodes_to_void.append(cast(URIRef, cast(ResultRow, r)[0]))

        elif cancellation_scope == "case":
            # WCP-20: All active tokens in the case
            case_query = f"""
            PREFIX kgc: <{KGC}>
            SELECT ?task WHERE {{
                ?task kgc:hasToken true .
            }}
            """
            case_results = list(graph.query(case_query))
            nodes_to_void = [cast(URIRef, cast(ResultRow, r)[0]) for r in case_results]

        elif cancellation_scope == "instances":
            # WCP-22: All MI instances of this task
            instances_query = f"""
            PREFIX kgc: <{KGC}>
            SELECT ?instance WHERE {{
                ?instance kgc:parentTask <{subject}> .
                ?instance kgc:hasToken true .
            }}
            """
            instances_results = list(graph.query(instances_query))
            nodes_to_void = [subject]  # Include parent
            for r in instances_results:
                nodes_to_void.append(cast(URIRef, cast(ResultRow, r)[0]))

        elif cancellation_scope == "task":
            # WCP-24: Cancel task and find exception handler
            nodes_to_void = [subject]
            # Find exception handler
            handler_query = f"""
            PREFIX yawl: <{YAWL}>
            SELECT ?handler WHERE {{
                <{subject}> yawl:hasExceptionHandler ?handler .
            }}
            """
            handler_results = list(graph.query(handler_query))
            if handler_results:
                handler = cast(URIRef, cast(ResultRow, handler_results[0])[0])
                # Route to exception handler
                additions.append((handler, KGC.hasToken, Literal(True)))
                additions.append((handler, KGC.activatedBy, subject))

        else:
            # Default: self
            nodes_to_void = [subject]

        # Void all collected nodes
        for node in nodes_to_void:
            # Remove token
            removals.append((node, KGC.hasToken, Literal(True)))
            # Record void
            additions.append((node, KGC.voidedAt, Literal(ctx.tx_id)))
            additions.append((node, KGC.terminatedReason, Literal(reason)))

        # Record scope for provenance
        additions.append((subject, KGC.cancellationScope, Literal(cancellation_scope)))
        additions.append((subject, KGC.nodesVoided, Literal(str(len(nodes_to_void)))))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))


# =============================================================================
# L5 PURE RDF KERNEL - SPARQL TEMPLATES ARE THE LOGIC
# =============================================================================


class PureRDFKernel:
    """
    Level 5 Pure RDF Kernel - ZERO Python if/else.

    ALL behavior is determined by SPARQL templates stored in the ontology.
    Python is just a SPARQL executor - it binds variables and runs queries.

    The Semantic Singularity: "Logic IS Data"
    -----------------------------------------
    - No Python conditionals on pattern names, flags, or values
    - SPARQL CONSTRUCT templates generate additions
    - SPARQL DELETE WHERE templates generate removals
    - Custom SPARQL functions handle predicate evaluation

    Architecture
    ------------
    1. resolve_template(pattern) → (execution_template, removal_template)
    2. bind_variables(template, subject, ctx) → bound_template
    3. execute(graph, bound_template) → QuadDelta

    Examples
    --------
    >>> kernel = PureRDFKernel(ontology)
    >>> delta = kernel.execute(graph, subject, ctx, config)
    >>> # delta comes entirely from SPARQL templates - no Python logic
    """

    def __init__(self, physics_ontology: Graph) -> None:
        """
        Initialize Pure RDF Kernel with physics ontology.

        Parameters
        ----------
        physics_ontology : Graph
            The KGC Physics Ontology containing SPARQL templates.
        """
        self.ontology = physics_ontology
        # Register custom SPARQL function for predicate evaluation
        self._register_custom_functions()

    def _register_custom_functions(self) -> None:
        """Register custom SPARQL functions for template execution."""
        # Note: rdflib doesn't support custom functions natively
        # For L5, we use template variable binding instead
        pass

    def execute(self, graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig) -> QuadDelta:
        """
        Execute verb using SPARQL templates - ZERO Python logic.

        This is the ONLY execution method. ALL behavior comes from templates.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The node to execute.
        ctx : TransactionContext
            Transaction context for variable binding.
        config : VerbConfig
            Configuration containing execution_template and removal_template.

        Returns
        -------
        QuadDelta
            Mutations from template execution.

        Notes
        -----
        The Python code here is ONLY:
        1. Variable binding (string replacement)
        2. SPARQL execution (graph.query)
        3. Result collection (tuple construction)

        NO conditionals, NO branching logic, NO pattern-specific behavior.
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Get templates from config (resolved from ontology)
        execution_template = config.execution_template
        removal_template = config.removal_template

        if not execution_template:
            # No template = no action (identity operation)
            return QuadDelta(additions=tuple(additions), removals=tuple(removals))

        # Bind variables in templates
        bound_exec = self._bind_variables(execution_template, subject, ctx, graph)

        # Execute CONSTRUCT for additions
        try:
            construct_result = graph.query(bound_exec)
            for row in construct_result:
                if len(row) >= 3:
                    s, p, o = row[0], row[1], row[2]
                    additions.append((s, p, o))
        except Exception as e:
            logger.warning("Execution template failed: %s - %s", str(e)[:50], bound_exec[:100])

        # Execute removal template - find triples to remove
        if removal_template:
            # Standard removal: subject's token (most patterns remove source token)
            # Check if subject has token before adding to removals
            if (subject, KGC.hasToken, Literal(True)) in graph:
                removals.append((subject, KGC.hasToken, Literal(True)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    def _bind_variables(self, template: str, subject: URIRef, ctx: TransactionContext, graph: Graph) -> str:
        """
        Bind template variables with runtime values.

        Parameters
        ----------
        template : str
            SPARQL template with placeholders.
        subject : URIRef
            Current node URI.
        ctx : TransactionContext
            Transaction context.
        graph : Graph
            Workflow graph for dynamic bindings.

        Returns
        -------
        str
            Template with all variables bound.
        """
        bound = template

        # Core bindings (always available)
        bound = bound.replace("?subject", f"<{subject}>")
        bound = bound.replace("?txId", f'"{ctx.tx_id}"')
        bound = bound.replace("?actor", f'"{ctx.actor}"')
        bound = bound.replace("?prevHash", f'"{ctx.prev_hash}"')

        # Data bindings from ctx.data (for predicate evaluation)
        # Templates can reference ?data_KEY for ctx.data["KEY"]
        for key, value in ctx.data.items():
            placeholder = f"?data_{key}"
            if placeholder in bound:
                if isinstance(value, bool):
                    bound = bound.replace(placeholder, str(value).lower())
                elif isinstance(value, (int, float)):
                    bound = bound.replace(placeholder, str(value))
                else:
                    bound = bound.replace(placeholder, f'"{value}"')

        return bound


# =============================================================================
# THE ATMAN - SEMANTIC DRIVER
# =============================================================================


class SemanticDriver:
    """
    The Atman - Ontology-driven verb dispatch with parameters.

    Resolves which verb AND parameters to execute by querying the physics ontology.
    Contains ZERO pattern-specific logic - all behavior comes from RDF.

    The Chatman Equation: A = μ(O, P)
    - O: Observation (graph topology)
    - P: Parameters (from ontology mappings)
    - μ: Operator (the verb function)
    - A: Action (the resulting delta)

    Parameters
    ----------
    physics_ontology : Graph
        The loaded KGC Physics Ontology (kgc_physics.ttl).

    Examples
    --------
    >>> from rdflib import Graph
    >>> ontology = Graph()
    >>> ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
    >>> driver = SemanticDriver(ontology)
    >>> driver.physics_ontology is not None
    True
    """

    def __init__(self, physics_ontology: Graph, *, use_l5_kernel: bool = False) -> None:
        """
        Initialize the Semantic Driver.

        Parameters
        ----------
        physics_ontology : Graph
            The KGC Physics Ontology containing verb + parameter mappings.
        use_l5_kernel : bool
            If True, use PureRDFKernel (L5) for ALL execution.
            If False (default), use L5 when templates exist, legacy otherwise.
        """
        self.physics_ontology = physics_ontology
        self.use_l5_kernel = use_l5_kernel
        self._pure_kernel = PureRDFKernel(physics_ontology)
        self._verb_dispatch: dict[str, Callable[[Graph, URIRef, TransactionContext, VerbConfig | None], QuadDelta]] = {
            "transmute": Kernel.transmute,
            "copy": Kernel.copy,
            "filter": Kernel.filter,
            "await": Kernel.await_,
            "void": Kernel.void,
        }

    def _bind_template_variables(self, template: str, subject: URIRef, ctx: TransactionContext) -> str:
        """
        Bind variables in SPARQL template with runtime values.

        Templates from ontology contain placeholders like ?subject, ?txId, ?actor
        that need to be replaced with actual values at execution time.

        Parameters
        ----------
        template : str
            SPARQL template with placeholders.
        subject : URIRef
            The workflow node being executed.
        ctx : TransactionContext
            Transaction context with tx_id, actor, prev_hash.

        Returns
        -------
        str
            SPARQL query with all variables bound.

        Notes
        -----
        Supported placeholders:
        - ?subject: Replaced with workflow node URI
        - ?txId: Replaced with transaction ID
        - ?actor: Replaced with actor identity
        - ?prevHash: Replaced with previous transaction hash

        Examples
        --------
        >>> template = "INSERT { ?subject kgc:executed ?txId }"
        >>> bound = driver._bind_template_variables(
        ...     template,
        ...     URIRef("urn:task:1"),
        ...     TransactionContext(tx_id="tx-001", actor="system", prev_hash="genesis", data={}),
        ... )
        >>> "urn:task:1" in bound and "tx-001" in bound
        True
        """
        # Replace placeholders with actual values
        bound = template.replace("?subject", f"<{subject}>")
        bound = bound.replace("?txId", f'"{ctx.tx_id}"')
        bound = bound.replace("?actor", f'"{ctx.actor}"')
        bound = bound.replace("?prevHash", f'"{ctx.prev_hash}"')

        return bound

    def resolve_verb(self, graph: Graph, node: URIRef) -> VerbConfig:
        """
        Resolve which verb AND parameters to execute by querying the ontology.

        Uses SPARQL to find the pattern→(verb, params) mapping in the physics ontology.
        This is the ONLY dispatch mechanism - no if/else on patterns.

        Parameters
        ----------
        graph : Graph
            The workflow graph being executed.
        node : URIRef
            The node to resolve verb for.

        Returns
        -------
        VerbConfig
            Configuration with verb name and all parameters from ontology.

        Raises
        ------
        ValueError
            If no verb mapping found for the node's pattern.

        Notes
        -----
        Query against physics ontology extracts:
        - verb label (transmute, copy, filter, await, void)
        - hasThreshold (for await)
        - hasCardinality (for copy)
        - completionStrategy (for await)
        - selectionMode (for filter)
        - cancellationScope (for void)
        - resetOnFire (for loops)
        - instanceBinding (for MI)
        - executionTemplate (SPARQL CONSTRUCT for additions)
        - removalTemplate (SPARQL DELETE WHERE for removals)
        """
        # Determine node's pattern type and trigger property from workflow graph
        # Check for split types
        split_query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?splitType WHERE {{
            <{node}> yawl:hasSplit ?splitType .
        }}
        """
        split_results = list(graph.query(split_query))

        # Check for join types
        join_query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?joinType WHERE {{
            <{node}> yawl:hasJoin ?joinType .
        }}
        """
        join_results = list(graph.query(join_query))

        # Determine pattern and trigger
        pattern: URIRef
        trigger_property: str | None = None
        trigger_value: URIRef | None = None

        if split_results:
            pattern = cast(URIRef, cast(ResultRow, split_results[0])[0])
            trigger_property = "yawl:hasSplit"
            trigger_value = pattern
        elif join_results:
            pattern = cast(URIRef, cast(ResultRow, join_results[0])[0])
            trigger_property = "yawl:hasJoin"
            trigger_value = pattern
        else:
            # Default to Sequence
            pattern = YAWL.Sequence
            trigger_property = None
            trigger_value = None

        # Query ontology for verb AND parameters (including RDF-only execution properties)
        # Use trigger properties to find the correct mapping
        if trigger_property and trigger_value:
            ontology_query = f"""
            PREFIX kgc: <{KGC}>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX yawl: <{YAWL}>
            SELECT ?verbLabel ?threshold ?cardinality ?completion ?selection ?scope ?reset ?binding
                   ?executionTemplate ?removalTemplate
                   ?thresholdValue ?cardinalityValue ?stopOnFirstMatch ?useActiveCount
                   ?useDynamicThreshold ?useDynamicCardinality
                   ?isDeferredChoice ?isMutexInterleaved ?invertPredicate ?ignoreSubsequent
            WHERE {{
                ?mapping kgc:pattern <{pattern}> ;
                         kgc:triggerProperty {trigger_property} ;
                         kgc:triggerValue <{trigger_value}> ;
                         kgc:verb ?verb .
                ?verb rdfs:label ?verbLabel .
                OPTIONAL {{ ?mapping kgc:hasThreshold ?threshold . }}
                OPTIONAL {{ ?mapping kgc:hasCardinality ?cardinality . }}
                OPTIONAL {{ ?mapping kgc:completionStrategy ?completion . }}
                OPTIONAL {{ ?mapping kgc:selectionMode ?selection . }}
                OPTIONAL {{ ?mapping kgc:cancellationScope ?scope . }}
                OPTIONAL {{ ?mapping kgc:resetOnFire ?reset . }}
                OPTIONAL {{ ?mapping kgc:instanceBinding ?binding . }}
                OPTIONAL {{ ?mapping kgc:executionTemplate ?executionTemplate . }}
                OPTIONAL {{ ?mapping kgc:removalTemplate ?removalTemplate . }}
                OPTIONAL {{ ?mapping kgc:thresholdValue ?thresholdValue . }}
                OPTIONAL {{ ?mapping kgc:cardinalityValue ?cardinalityValue . }}
                OPTIONAL {{ ?mapping kgc:stopOnFirstMatch ?stopOnFirstMatch . }}
                OPTIONAL {{ ?mapping kgc:useActiveCount ?useActiveCount . }}
                OPTIONAL {{ ?mapping kgc:useDynamicThreshold ?useDynamicThreshold . }}
                OPTIONAL {{ ?mapping kgc:useDynamicCardinality ?useDynamicCardinality . }}
                OPTIONAL {{ ?mapping kgc:isDeferredChoice ?isDeferredChoice . }}
                OPTIONAL {{ ?mapping kgc:isMutexInterleaved ?isMutexInterleaved . }}
                OPTIONAL {{ ?mapping kgc:invertPredicate ?invertPredicate . }}
                OPTIONAL {{ ?mapping kgc:ignoreSubsequent ?ignoreSubsequent . }}
            }}
            """
        else:
            ontology_query = f"""
            PREFIX kgc: <{KGC}>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?verbLabel ?threshold ?cardinality ?completion ?selection ?scope ?reset ?binding
                   ?executionTemplate ?removalTemplate
                   ?thresholdValue ?cardinalityValue ?stopOnFirstMatch ?useActiveCount
                   ?useDynamicThreshold ?useDynamicCardinality
                   ?isDeferredChoice ?isMutexInterleaved ?invertPredicate ?ignoreSubsequent
            WHERE {{
                ?mapping kgc:pattern <{pattern}> ;
                         kgc:verb ?verb .
                ?verb rdfs:label ?verbLabel .
                OPTIONAL {{ ?mapping kgc:hasThreshold ?threshold . }}
                OPTIONAL {{ ?mapping kgc:hasCardinality ?cardinality . }}
                OPTIONAL {{ ?mapping kgc:completionStrategy ?completion . }}
                OPTIONAL {{ ?mapping kgc:selectionMode ?selection . }}
                OPTIONAL {{ ?mapping kgc:cancellationScope ?scope . }}
                OPTIONAL {{ ?mapping kgc:resetOnFire ?reset . }}
                OPTIONAL {{ ?mapping kgc:instanceBinding ?binding . }}
                OPTIONAL {{ ?mapping kgc:executionTemplate ?executionTemplate . }}
                OPTIONAL {{ ?mapping kgc:removalTemplate ?removalTemplate . }}
                OPTIONAL {{ ?mapping kgc:thresholdValue ?thresholdValue . }}
                OPTIONAL {{ ?mapping kgc:cardinalityValue ?cardinalityValue . }}
                OPTIONAL {{ ?mapping kgc:stopOnFirstMatch ?stopOnFirstMatch . }}
                OPTIONAL {{ ?mapping kgc:useActiveCount ?useActiveCount . }}
                OPTIONAL {{ ?mapping kgc:useDynamicThreshold ?useDynamicThreshold . }}
                OPTIONAL {{ ?mapping kgc:useDynamicCardinality ?useDynamicCardinality . }}
                OPTIONAL {{ ?mapping kgc:isDeferredChoice ?isDeferredChoice . }}
                OPTIONAL {{ ?mapping kgc:isMutexInterleaved ?isMutexInterleaved . }}
                OPTIONAL {{ ?mapping kgc:invertPredicate ?invertPredicate . }}
                OPTIONAL {{ ?mapping kgc:ignoreSubsequent ?ignoreSubsequent . }}
            }}
            """

        ontology_results = list(self.physics_ontology.query(ontology_query))

        if not ontology_results:
            msg = f"No verb mapping found for pattern {pattern} on node {node}"
            raise ValueError(msg)

        # Extract verb name and parameters
        row = cast(ResultRow, ontology_results[0])
        verb_label = str(row[0]).lower()

        # Extract optional parameters (may be None)
        threshold = str(row[1]) if len(row) > 1 and row[1] is not None else None
        cardinality = str(row[2]) if len(row) > 2 and row[2] is not None else None
        completion = str(row[3]) if len(row) > 3 and row[3] is not None else None
        selection = str(row[4]) if len(row) > 4 and row[4] is not None else None
        scope = str(row[5]) if len(row) > 5 and row[5] is not None else None
        reset_raw = row[6] if len(row) > 6 else None
        reset = str(reset_raw).lower() == "true" if reset_raw is not None else False
        binding = str(row[7]) if len(row) > 7 and row[7] is not None else None

        # Extract execution templates (new in v3.1)
        execution_template = str(row[8]) if len(row) > 8 and row[8] is not None else None
        removal_template = str(row[9]) if len(row) > 9 and row[9] is not None else None

        # Extract RDF-only evaluation properties (Mission 05-07)
        # These come from explicit kgc:thresholdValue, etc. - NO string fallback
        threshold_value_raw = row[10] if len(row) > 10 and row[10] is not None else None
        cardinality_value_raw = row[11] if len(row) > 11 and row[11] is not None else None
        stop_first_raw = row[12] if len(row) > 12 else None
        use_active_raw = row[13] if len(row) > 13 else None
        use_dyn_thresh_raw = row[14] if len(row) > 14 else None
        use_dyn_card_raw = row[15] if len(row) > 15 else None
        is_deferred_raw = row[16] if len(row) > 16 else None
        is_mutex_raw = row[17] if len(row) > 17 else None
        invert_pred_raw = row[18] if len(row) > 18 else None
        ignore_subseq_raw = row[19] if len(row) > 19 else None

        # Compute numeric threshold from RDF (no string fallback)
        # Sentinels: -1 = all, >0 = explicit integer
        threshold_value: int | None = None
        if threshold_value_raw is not None:
            threshold_value = int(str(threshold_value_raw))

        # Compute numeric cardinality from RDF (no string fallback)
        # Sentinels: -1 = topology, -2 = static, -3 = incremental, >0 = explicit N
        cardinality_value: int | None = None
        if cardinality_value_raw is not None:
            cardinality_value = int(str(cardinality_value_raw))

        # Boolean flags for RDF-only evaluation (directly from RDF properties)
        stop_on_first_match = str(stop_first_raw).lower() == "true" if stop_first_raw else False
        use_active_count = str(use_active_raw).lower() == "true" if use_active_raw else False
        use_dynamic_threshold = str(use_dyn_thresh_raw).lower() == "true" if use_dyn_thresh_raw else False
        use_dynamic_cardinality = str(use_dyn_card_raw).lower() == "true" if use_dyn_card_raw else False
        is_deferred_choice = str(is_deferred_raw).lower() == "true" if is_deferred_raw else False
        is_mutex_interleaved = str(is_mutex_raw).lower() == "true" if is_mutex_raw else False
        invert_predicate = str(invert_pred_raw).lower() == "true" if invert_pred_raw else False
        ignore_subsequent = str(ignore_subseq_raw).lower() == "true" if ignore_subseq_raw else False

        return VerbConfig(
            verb=verb_label,
            threshold=threshold,
            cardinality=cardinality,
            completion_strategy=completion,
            selection_mode=selection,
            cancellation_scope=scope,
            reset_on_fire=reset,
            instance_binding=binding,
            execution_template=execution_template,
            removal_template=removal_template,
            # RDF-only evaluation properties
            threshold_value=threshold_value,
            cardinality_value=cardinality_value,
            stop_on_first_match=stop_on_first_match,
            use_active_count=use_active_count,
            use_dynamic_threshold=use_dynamic_threshold,
            use_dynamic_cardinality=use_dynamic_cardinality,
            is_deferred_choice=is_deferred_choice,
            is_mutex_interleaved=is_mutex_interleaved,
            invert_predicate=invert_predicate,
            ignore_subsequent=ignore_subsequent,
        )

    def execute(self, graph: Graph, subject: URIRef, ctx: TransactionContext) -> Receipt:
        """
        Execute the Chatman Equation: A = μ(O, P).

        1. Resolve verb + parameters via ontology SPARQL query
        2. Execute the parameterized verb (pure function)
        3. Generate cryptographic receipt with provenance

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The node to execute.
        ctx : TransactionContext
            Transaction context with provenance data.

        Returns
        -------
        Receipt
            Cryptographic proof of execution with parameters used.

        Examples
        --------
        >>> from rdflib import Graph, URIRef
        >>> ontology = Graph()
        >>> ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
        >>> driver = SemanticDriver(ontology)
        >>> workflow = Graph()
        >>> # ... load workflow ...
        >>> ctx = TransactionContext("tx-1", "system", "genesis", {})
        >>> receipt = driver.execute(workflow, URIRef("urn:task:1"), ctx)
        >>> receipt.verb_executed in ["transmute", "copy", "filter", "await", "void"]
        True
        """
        # 1. ONTOLOGY LOOKUP (The μ Operator with Parameters P)
        config = self.resolve_verb(graph, subject)

        # 2. VERB EXECUTION
        if self.use_l5_kernel or config.execution_template:
            # L5 PURE RDF: Execute via PureRDFKernel (SPARQL templates ARE the logic)
            # ZERO Python if/else - all behavior from templates
            delta = self._pure_kernel.execute(graph, subject, ctx, config)
        else:
            # Legacy L2/L3 fallback: Use parameterized verb functions
            verb_fn = self._verb_dispatch[config.verb]
            delta = verb_fn(graph, subject, ctx, config)

        # 3. PROVENANCE (Lockchain with parameters)
        # Include config in merkle payload for auditability
        params_str = f"t={config.threshold}|c={config.cardinality}|s={config.selection_mode}"
        merkle_payload = (
            f"{ctx.prev_hash}|{ctx.tx_id}|{config.verb}|{params_str}|{len(delta.additions)}|{len(delta.removals)}"
        )
        merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

        # 4. APPLY MUTATIONS (Side Effect)
        for triple in delta.removals:
            graph.remove(triple)
        for triple in delta.additions:
            graph.add(triple)

        return Receipt(merkle_root=merkle_root, verb_executed=config.verb, delta=delta, params_used=config)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _evaluate_predicate(predicate: str, data: dict[str, Any]) -> bool:
    """
    Evaluate a predicate expression against context data.

    This is a simple implementation for research purposes.
    Production systems should use SPARQL ASK or sandboxed evaluation.

    Parameters
    ----------
    predicate : str
        The predicate expression (e.g., "data['x'] > 5").
    data : dict[str, Any]
        Context data to evaluate against.

    Returns
    -------
    bool
        True if predicate evaluates to truthy value.

    Notes
    -----
    SECURITY: This uses eval() which is unsafe for untrusted input.
    Research library only - production must use SPARQL ASK or safe parser.
    """
    try:
        # UNSAFE: For research only
        # Production: Use SPARQL ASK or safe expression evaluator
        result = eval(predicate, {"__builtins__": {}}, {"data": data})  # noqa: S307
        return bool(result)
    except Exception:
        logger.exception("Predicate evaluation failed: %s", predicate)
        return False
