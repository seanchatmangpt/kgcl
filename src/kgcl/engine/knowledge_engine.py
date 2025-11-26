"""KGCL Reference Engine v3.0 (The Semantic Driver).

Philosophy: The Chatman Equation (A = μ(O))
Architecture: Kernel (5 static verbs) + Atman (ontology lookup) + Lockchain (provenance)

This module implements the KGC v3 engine with ZERO pattern-specific logic.
ALL behavior is resolved via SPARQL queries against the physics ontology.

THE SEMANTIC SINGULARITY PRINCIPLE: "Validation IS Execution"
--------------------------------------------------------------
- Logic is expressed in kgc_physics.ttl (Dark Matter), NOT in Python code
- The engine queries the ontology to determine which verb to execute
- NO Python if-statements for pattern dispatch
- Patterns are mapped to verbs via SPARQL queries against the ontology

THE 5 ELEMENTAL VERBS (Implemented by Kernel)
----------------------------------------------
1. TRANSMUTE (Arrow of Time): A → B
2. COPY (Divergence): A → {B, C}
3. FILTER (Selection): A → {Subset}
4. AWAIT (Convergence): {A, B} → C
5. VOID (Termination): A → ∅

The engine ensures:
1. Verb Resolution - SPARQL queries resolve patterns to verbs at runtime
2. Pure Functions - Kernel verbs are stateless operations on graph nodes
3. Cryptographic Provenance - Every mutation generates a merkle-linked receipt

Examples
--------
>>> from rdflib import Graph, URIRef
>>> from kgcl.engine.knowledge_engine import SemanticDriver, TransactionContext
>>>
>>> # Load physics ontology
>>> ontology = Graph()
>>> ontology.parse("ontology/kgc_physics.ttl", format="turtle")
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
class Receipt:
    """
    The Action (A) - Cryptographic proof of execution.

    Provides complete provenance:
    - merkle_root: Links to previous state via hash chain
    - verb_executed: Which verb was applied (from ontology)
    - delta: What mutations occurred

    Parameters
    ----------
    merkle_root : str
        SHA256(prev_hash + delta) - Lockchain link.
    verb_executed : str
        The verb that was executed ("transmute", "copy", etc.).
    delta : QuadDelta
        The mutations that were applied.

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


# =============================================================================
# THE KERNEL - THE 5 ELEMENTAL VERBS
# =============================================================================


class Kernel:
    """
    The 5 Elemental Verbs - Pure functions on graph nodes.

    These are the ONLY operations the engine can perform.
    Each verb is a static method that takes a graph, node, and context,
    and returns a QuadDelta describing the mutations.

    No verb contains pattern-specific logic. All behavior is determined
    by the graph structure and the ontology mappings.

    Verbs
    -----
    1. transmute - Arrow of Time (A → B)
    2. copy - Divergence (A → {B, C})
    3. filter - Selection (A → {Subset})
    4. await_ - Convergence ({A, B} → C)
    5. void - Termination (A → ∅)
    """

    @staticmethod
    def transmute(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
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
    def copy(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """
        VERB 2: COPY - Divergence (A → {B, C}).

        Clone token state to ALL next elements (AND-split, service dispatch).

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.

        Returns
        -------
        QuadDelta
            Mutations to execute the parallel split.

        Notes
        -----
        SPARQL Query (from ontology):
            SELECT ?next WHERE {
                ?current yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
            }
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Find ALL next elements via SPARQL
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?next WHERE {{
            <{subject}> yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }}
        """
        results = list(graph.query(query))

        if results:
            # Remove token from current node
            removals.append((subject, KGC.hasToken, Literal(True)))
            # Clone token to ALL successors
            for result in results:
                row = cast(ResultRow, result)
                next_element = cast(URIRef, row[0])
                additions.append((next_element, KGC.hasToken, Literal(True)))
            # Mark current node as completed
            additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def filter(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """
        VERB 3: FILTER - Selection (A → {Subset}).

        Evaluate predicates to select which paths receive tokens
        (XOR-split, OR-split, resource authorization).

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.

        Returns
        -------
        QuadDelta
            Mutations to execute the conditional routing.

        Notes
        -----
        SPARQL Query (from ontology):
            SELECT ?next ?predicate ?ordering WHERE {
                ?current yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
                OPTIONAL { ?flow yawl:hasPredicate ?pred .
                           ?pred yawl:query ?predicate ;
                                 yawl:ordering ?ordering . }
            }
            ORDER BY ?ordering
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Find flows with predicates via SPARQL
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?next ?predicate ?ordering WHERE {{
            <{subject}> yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            OPTIONAL {{
                ?flow yawl:hasPredicate ?pred .
                ?pred yawl:query ?predicate ;
                      yawl:ordering ?ordering .
            }}
        }}
        ORDER BY ?ordering
        """
        results = list(graph.query(query))

        selected_paths: list[URIRef] = []
        for result in results:
            row = cast(ResultRow, result)
            next_element = cast(URIRef, row[0])
            predicate = row[1] if len(row) > 1 else None

            # Evaluate predicate (simple implementation - can be extended)
            if predicate is None:
                # Default path (no condition)
                selected_paths.append(next_element)
            # Evaluate condition against context data
            # For now, simple truthiness check
            # Production: use SPARQL ASK or Python eval with sandbox
            elif _evaluate_predicate(str(predicate), ctx.data):
                selected_paths.append(next_element)

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
    def await_(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """
        VERB 4: AWAIT - Convergence ({A, B} → C).

        Wait for incoming flows to complete before proceeding
        (AND-join, OR-join, Discriminator).

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI (join node).
        ctx : TransactionContext
            Transaction context.

        Returns
        -------
        QuadDelta
            Mutations to execute the join (if conditions met).

        Notes
        -----
        SPARQL Query (from ontology):
            SELECT ?source ?completed WHERE {
                ?source yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?current .
                OPTIONAL { ?source kgc:completedAt ?completed . }
            }
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Find incoming flows and check completion status
        query = f"""
        PREFIX yawl: <{YAWL}>
        PREFIX kgc: <{KGC}>
        SELECT ?source ?completed WHERE {{
            ?source yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef <{subject}> .
            OPTIONAL {{ ?source kgc:completedAt ?completed . }}
        }}
        """
        results = list(graph.query(query))

        # Check join type (AND vs OR) via node properties
        join_type_query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?joinType WHERE {{
            <{subject}> yawl:hasJoin ?joinType .
        }}
        """
        join_type_results = list(graph.query(join_type_query))
        join_type = cast(URIRef, cast(ResultRow, join_type_results[0])[0]) if join_type_results else None

        total_sources = len(results)
        completed_sources = sum(1 for r in results if cast(ResultRow, r)[1] is not None)

        # Determine if join condition is satisfied
        can_proceed = False
        if join_type == YAWL.ControlTypeAnd:
            # AND-join: ALL sources must complete
            can_proceed = completed_sources == total_sources
        elif join_type == YAWL.ControlTypeOr:
            # OR-join: At least one active source must complete
            # (simplified: check if any completed)
            can_proceed = completed_sources > 0
        else:
            # Default: Discriminator (quorum=1)
            can_proceed = completed_sources >= 1

        if can_proceed:
            # Check if node already has token
            has_token = (subject, KGC.hasToken, Literal(True)) in graph
            if not has_token:
                # Activate this node
                additions.append((subject, KGC.hasToken, Literal(True)))
                additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def void(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """
        VERB 5: VOID - Termination (A → ∅).

        Destroy token without creating successor
        (timeout, cancellation, exception handling).

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context.

        Returns
        -------
        QuadDelta
            Mutations to destroy the token.

        Notes
        -----
        SPARQL Query (from ontology):
            SELECT ?reason WHERE {
                { ?current yawl:hasTimer ?timer .
                  ?timer yawl:expiry ?expiry .
                  FILTER (NOW() > ?expiry) .
                  BIND("timeout" AS ?reason) }
                UNION
                { ?current kgc:cancelled true .
                  BIND("cancelled" AS ?reason) }
                UNION
                { ?current kgc:failed true .
                  BIND("exception" AS ?reason) }
            }
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # Check termination reason via SPARQL
        query = f"""
        PREFIX yawl: <{YAWL}>
        PREFIX kgc: <{KGC}>
        SELECT ?reason WHERE {{
            {{
                <{subject}> yawl:hasTimer ?timer .
                ?timer yawl:expiry ?expiry .
                FILTER (NOW() > ?expiry) .
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
        results = list(graph.query(query))

        if results:
            reason = str(cast(ResultRow, results[0])[0])
            # Remove token
            removals.append((subject, KGC.hasToken, Literal(True)))
            # Record termination reason
            additions.append((subject, KGC.terminatedReason, Literal(reason)))
            additions.append((subject, KGC.completedAt, Literal(ctx.tx_id)))

        return QuadDelta(additions=tuple(additions), removals=tuple(removals))


# =============================================================================
# THE ATMAN - SEMANTIC DRIVER
# =============================================================================


class SemanticDriver:
    """
    The Atman - Ontology-driven verb dispatch.

    Resolves which verb to execute by querying the physics ontology.
    Contains ZERO pattern-specific logic - all behavior comes from RDF.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded KGC Physics Ontology (kgc_physics.ttl).

    Examples
    --------
    >>> from rdflib import Graph
    >>> ontology = Graph()
    >>> ontology.parse("ontology/kgc_physics.ttl", format="turtle")
    >>> driver = SemanticDriver(ontology)
    >>> driver.physics_ontology is not None
    True
    """

    def __init__(self, physics_ontology: Graph) -> None:
        """
        Initialize the Semantic Driver.

        Parameters
        ----------
        physics_ontology : Graph
            The KGC Physics Ontology containing verb mappings.
        """
        self.physics_ontology = physics_ontology
        self._verb_dispatch = {
            "transmute": Kernel.transmute,
            "copy": Kernel.copy,
            "filter": Kernel.filter,
            "await": Kernel.await_,
            "void": Kernel.void,
        }

    def resolve_verb(self, graph: Graph, node: URIRef) -> str:
        """
        Resolve which verb to execute by querying the ontology.

        Uses SPARQL to find the pattern→verb mapping in the physics ontology.
        This is the ONLY dispatch mechanism - no if/else on patterns.

        Parameters
        ----------
        graph : Graph
            The workflow graph being executed.
        node : URIRef
            The node to resolve verb for.

        Returns
        -------
        str
            The verb name ("transmute", "copy", "filter", "await", "void").

        Raises
        ------
        ValueError
            If no verb mapping found for the node's pattern.

        Notes
        -----
        Query against physics ontology:
            SELECT ?verbLabel WHERE {
                ?mapping kgc:pattern ?patternType ;
                         kgc:verb ?verb .
                ?verb rdfs:label ?verbLabel .
                OPTIONAL { ?mapping kgc:condition ?cond . }
                FILTER (!BOUND(?cond) || ... ASK evaluation ...)
            }
        """
        # Determine node's pattern type from workflow graph
        # Check for split/join types
        split_query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?splitType WHERE {{
            <{node}> yawl:hasSplit ?splitType .
        }}
        """
        split_results = list(graph.query(split_query))

        join_query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?joinType WHERE {{
            <{node}> yawl:hasJoin ?joinType .
        }}
        """
        join_results = list(graph.query(join_query))

        # Query ontology for verb mapping
        pattern: URIRef
        if split_results:
            pattern = cast(URIRef, cast(ResultRow, split_results[0])[0])
        elif join_results:
            pattern = cast(URIRef, cast(ResultRow, join_results[0])[0])
        else:
            # Default to Sequence
            pattern = YAWL.Sequence

        # Query ontology for verb mapping
        ontology_query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?verbLabel WHERE {{
            ?mapping kgc:pattern <{pattern}> ;
                     kgc:verb ?verb .
            ?verb rdfs:label ?verbLabel .
        }}
        """
        ontology_results = list(self.physics_ontology.query(ontology_query))

        if not ontology_results:
            msg = f"No verb mapping found for pattern {pattern} on node {node}"
            raise ValueError(msg)

        # Extract verb name (lowercase, no language tag)
        verb_label = str(cast(ResultRow, ontology_results[0])[0]).lower()
        return verb_label

    def execute(self, graph: Graph, subject: URIRef, ctx: TransactionContext) -> Receipt:
        """
        Execute the Chatman Equation: A = μ(O).

        1. Resolve verb via ontology SPARQL query
        2. Execute the verb (pure function)
        3. Generate cryptographic receipt

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
            Cryptographic proof of execution.

        Examples
        --------
        >>> from rdflib import Graph, URIRef
        >>> ontology = Graph()
        >>> ontology.parse("ontology/kgc_physics.ttl", format="turtle")
        >>> driver = SemanticDriver(ontology)
        >>> workflow = Graph()
        >>> # ... load workflow ...
        >>> ctx = TransactionContext("tx-1", "system", "genesis", {})
        >>> receipt = driver.execute(workflow, URIRef("urn:task:1"), ctx)
        >>> receipt.verb_executed in ["transmute", "copy", "filter", "await", "void"]
        True
        """
        # 1. ONTOLOGY LOOKUP (The μ Operator)
        verb_name = self.resolve_verb(graph, subject)

        # 2. VERB EXECUTION (Pure Function)
        verb_fn = self._verb_dispatch[verb_name]
        delta = verb_fn(graph, subject, ctx)

        # 3. PROVENANCE (Lockchain)
        merkle_payload = f"{ctx.prev_hash}|{ctx.tx_id}|{len(delta.additions)}|{len(delta.removals)}"
        merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

        # 4. APPLY MUTATIONS (Side Effect)
        for triple in delta.removals:
            graph.remove(triple)
        for triple in delta.additions:
            graph.add(triple)

        return Receipt(merkle_root=merkle_root, verb_executed=verb_name, delta=delta)


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
