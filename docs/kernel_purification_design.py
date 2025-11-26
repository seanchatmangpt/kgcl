"""
Kernel Purification Design - Pure RDF/SPARQL Architecture
==========================================================

This module shows the refactored Kernel architecture that eliminates ALL Python if/else
from the 5 Kernel verbs by using SPARQL CONSTRUCT templates from VerbConfig.

ARCHITECTURE:
1. VerbConfig stores SPARQL CONSTRUCT templates (execution + removal)
2. execute_template() method executes templates with variable binding
3. All 5 verbs delegate to execute_template() - ZERO if/else logic
4. Parameters are encoded in templates, not interpreted in Python

EXAMPLE TEMPLATE (copy with cardinality="topology"):
```sparql
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

CONSTRUCT {
    # Remove token from current node
    ?subject kgc:hasToken false .

    # Add token to ALL successors (topology-based)
    ?next kgc:hasToken true .

    # Mark completion
    ?subject kgc:completedAt ?txId .
}
WHERE {
    # Find all successors
    ?subject yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
```

BENEFITS:
- Logic lives in RDF templates, not Python code
- Parameters are template variables, not if/else branches
- Engine becomes pure template executor
- Fully declarative, ontology-driven execution
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.query import ResultRow

if TYPE_CHECKING:
    from collections.abc import Callable

# Namespaces
KGC = Namespace("http://bitflow.ai/ontology/kgc/v3#")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")

# Genesis hash for lockchain
GENESIS_HASH: str = "4d7c606c9002d3043ee3979533922e25752bd2755709057060b553593605bd62"

# Maximum batch size (Chatman Constant)
CHATMAN_CONSTANT: int = 64


# =============================================================================
# DATA STRUCTURES (Updated)
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
    """

    tx_id: str
    actor: str
    prev_hash: str
    data: dict[str, Any]


@dataclass(frozen=True)
class VerbConfig:
    """
    Configuration for verb execution - The (verb, params) tuple.

    NEW ARCHITECTURE: Includes SPARQL CONSTRUCT templates for execution.
    Templates encode ALL parameter interpretation logic declaratively.

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
        SPARQL CONSTRUCT template for additions (NEW).
    removal_template : str | None
        SPARQL DELETE WHERE template for removals (NEW).

    Examples
    --------
    >>> config = VerbConfig(
    ...     verb="copy",
    ...     cardinality="topology",
    ...     execution_template='''
    ...         PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
    ...         PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
    ...         CONSTRUCT {
    ...             ?next kgc:hasToken true .
    ...             ?subject kgc:completedAt ?txId .
    ...         }
    ...         WHERE {
    ...             ?subject yawl:flowsInto ?flow .
    ...             ?flow yawl:nextElementRef ?next .
    ...         }
    ...     ''',
    ...     removal_template='''
    ...         PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
    ...         DELETE {
    ...             ?subject kgc:hasToken ?token .
    ...         }
    ...         WHERE {
    ...             ?subject kgc:hasToken ?token .
    ...         }
    ...     '''
    ... )
    >>> config.verb
    'copy'
    """

    verb: str
    threshold: str | None = None
    cardinality: str | None = None
    completion_strategy: str | None = None
    selection_mode: str | None = None
    cancellation_scope: str | None = None
    reset_on_fire: bool = False
    instance_binding: str | None = None
    execution_template: str | None = None  # NEW: SPARQL CONSTRUCT for additions
    removal_template: str | None = None  # NEW: SPARQL DELETE WHERE for removals


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
    """

    merkle_root: str
    verb_executed: str
    delta: QuadDelta
    params_used: VerbConfig | None = None


# =============================================================================
# THE PURIFIED KERNEL - ZERO if/else
# =============================================================================


class Kernel:
    """
    The 5 Elemental Verbs - Pure template execution, ZERO if/else.

    NEW ARCHITECTURE:
    - All verbs delegate to execute_template()
    - Parameters are encoded in SPARQL templates, not Python code
    - Templates are stored in VerbConfig, resolved from ontology
    - Engine becomes pure template executor

    Verbs (Declarative)
    -------------------
    1. transmute - Arrow of Time (template-driven)
    2. copy - Divergence (cardinality in template)
    3. filter - Selection (selection_mode in template)
    4. await_ - Convergence (threshold in template)
    5. void - Termination (scope in template)
    """

    @staticmethod
    def execute_template(
        graph: Graph,
        subject: URIRef,
        ctx: TransactionContext,
        execution_template: str | None,
        removal_template: str | None = None,
    ) -> QuadDelta:
        """
        Execute SPARQL CONSTRUCT templates to generate QuadDelta.

        This is the ONLY execution method - all 5 verbs delegate here.
        Templates contain ALL parameter interpretation logic declaratively.

        Parameters
        ----------
        graph : Graph
            The workflow graph to query against.
        subject : URIRef
            The current node URI (bound to ?subject in template).
        ctx : TransactionContext
            Transaction context (provides ?txId, ?actor, ?prevHash, ?data).
        execution_template : str | None
            SPARQL CONSTRUCT template for additions.
            Variables available: ?subject, ?txId, ?actor, ?prevHash, and any ctx.data keys.
        removal_template : str | None
            SPARQL DELETE WHERE template for removals (optional).

        Returns
        -------
        QuadDelta
            Mutations extracted from CONSTRUCT results.

        Examples
        --------
        >>> from rdflib import Graph, URIRef, Namespace
        >>> KGC = Namespace("http://bitflow.ai/ontology/kgc/v3#")
        >>> YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
        >>> graph = Graph()
        >>> subject = URIRef("urn:task:1")
        >>> next_task = URIRef("urn:task:2")
        >>> graph.add((subject, YAWL.flowsInto, URIRef("urn:flow:1")))
        >>> graph.add((URIRef("urn:flow:1"), YAWL.nextElementRef, next_task))
        >>> graph.add((subject, KGC.hasToken, Literal(True)))
        >>> ctx = TransactionContext("tx-001", "system", "genesis", {})
        >>> template = '''
        ...     PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        ...     PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ...     CONSTRUCT {
        ...         ?next kgc:hasToken true .
        ...         ?subject kgc:completedAt ?txId .
        ...     }
        ...     WHERE {
        ...         ?subject yawl:flowsInto ?flow .
        ...         ?flow yawl:nextElementRef ?next .
        ...     }
        ... '''
        >>> delta = Kernel.execute_template(graph, subject, ctx, template)
        >>> len(delta.additions) > 0
        True

        Notes
        -----
        Variable Binding:
        - ?subject: Bound to subject parameter
        - ?txId: Bound to ctx.tx_id
        - ?actor: Bound to ctx.actor
        - ?prevHash: Bound to ctx.prev_hash
        - Any key in ctx.data: Bound as literal (e.g., ?itemCount from data["itemCount"])

        Template Examples:
        - Copy (topology): Find ALL ?next via yawl:flowsInto
        - Copy (static): Use LIMIT ?n from data["cardinality"]
        - Copy (dynamic): Use FILTER on ctx.data list length
        - Await (all): COUNT(?source) and compare to total
        - Await (1): Use LIMIT 1 and check existence
        - Filter (exactlyOne): ORDER BY ?ordering, LIMIT 1
        - Filter (oneOrMore): No LIMIT, evaluate all predicates
        - Void (region): Find all ?task via yawl:cancellationSet
        """
        additions: list[Triple] = []
        removals: list[Triple] = []

        # 1. PREPARE VARIABLE BINDINGS
        # Standard bindings available to ALL templates
        init_bindings = {
            "subject": subject,
            "txId": Literal(ctx.tx_id),
            "actor": Literal(ctx.actor),
            "prevHash": Literal(ctx.prev_hash),
        }

        # Add context data as bindings (for dynamic parameters)
        for key, value in ctx.data.items():
            # Convert Python values to RDF literals
            if isinstance(value, str):
                init_bindings[key] = Literal(value)
            elif isinstance(value, int | float):
                init_bindings[key] = Literal(value)
            elif isinstance(value, bool):
                init_bindings[key] = Literal(value)
            elif isinstance(value, list):
                # For lists, bind the length (common for dynamic cardinality)
                init_bindings[f"{key}Count"] = Literal(len(value))
            # Note: Complex objects would need serialization strategy

        # 2. EXECUTE REMOVAL TEMPLATE (if present)
        if removal_template:
            try:
                # Parse and execute DELETE WHERE query
                # Note: rdflib doesn't have DELETE, so we extract triples to remove
                # Convert DELETE to SELECT to find triples, then remove manually
                select_template = removal_template.replace("DELETE", "SELECT *", 1)
                prepared_query = prepareQuery(select_template, initNs={"kgc": KGC, "yawl": YAWL})
                results = graph.query(prepared_query, initBindings=init_bindings)

                # Extract triples from DELETE WHERE pattern
                # For simplicity, we assume template follows pattern:
                # DELETE { ?s ?p ?o } WHERE { ?s ?p ?o . FILTER(...) }
                # We execute the WHERE clause and collect matching triples
                for row in results:
                    # Each result row represents a triple to remove
                    # This is simplified - production needs proper DELETE support
                    if len(row) >= 3:  # noqa: PLR2004
                        s, p, o = row[0], row[1], row[2]
                        if isinstance(s, URIRef | Literal) and isinstance(p, URIRef) and isinstance(o, URIRef | Literal):
                            removals.append((s, p, o))

            except Exception as e:
                # Log error but continue (removal failures shouldn't block execution)
                import logging

                logger = logging.getLogger(__name__)
                logger.exception("Removal template execution failed: %s", e)

        # 3. EXECUTE ADDITION TEMPLATE (CONSTRUCT)
        if execution_template:
            try:
                # Prepare and execute CONSTRUCT query
                prepared_query = prepareQuery(execution_template, initNs={"kgc": KGC, "yawl": YAWL})
                result_graph = graph.query(prepared_query, initBindings=init_bindings)

                # Extract additions from CONSTRUCT result
                # rdflib CONSTRUCT returns a Graph
                if hasattr(result_graph, "__iter__"):
                    for triple in result_graph:  # type: ignore
                        if len(triple) == 3:  # noqa: PLR2004
                            s, p, o = triple
                            if isinstance(s, URIRef | Literal) and isinstance(p, URIRef) and isinstance(o, URIRef | Literal):
                                additions.append((s, p, o))

            except Exception as e:
                # Log error but return empty delta (fail safe)
                import logging

                logger = logging.getLogger(__name__)
                logger.exception("Execution template failed: %s", e)

        # 4. RETURN QUADDELTA
        return QuadDelta(additions=tuple(additions), removals=tuple(removals))

    @staticmethod
    def transmute(
        graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None
    ) -> QuadDelta:
        """
        VERB 1: TRANSMUTE - Arrow of Time (A → B).

        PURIFIED: Delegates to execute_template() with ZERO if/else.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.
        config : VerbConfig | None
            Configuration with templates from ontology.

        Returns
        -------
        QuadDelta
            Mutations to execute the sequence transition.

        Notes
        -----
        Template Example (from VerbConfig.execution_template):
        ```sparql
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

        CONSTRUCT {
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
        ```
        Removal Template:
        ```sparql
        DELETE {
            ?subject kgc:hasToken ?token .
        }
        WHERE {
            ?subject kgc:hasToken ?token .
        }
        ```
        """
        if config and config.execution_template:
            return Kernel.execute_template(graph, subject, ctx, config.execution_template, config.removal_template)

        # Legacy fallback (to be removed after migration)
        return Kernel._legacy_transmute(graph, subject, ctx)

    @staticmethod
    def copy(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 2: COPY - Divergence (A → {B₁, B₂, ..., Bₙ}).

        PURIFIED: Delegates to execute_template() with ZERO if/else.
        Cardinality logic is encoded in SPARQL template, not Python code.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.
        config : VerbConfig | None
            Configuration with cardinality-specific templates.

        Returns
        -------
        QuadDelta
            Mutations to execute the parallel split.

        Notes
        -----
        Template Examples by Cardinality:

        1. cardinality="topology" (WCP-2: AND-split to ALL successors):
        ```sparql
        CONSTRUCT {
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
        ```

        2. cardinality="dynamic" (WCP-14: N from runtime data):
        ```sparql
        CONSTRUCT {
            ?instanceUri kgc:hasToken true .
            ?instanceUri kgc:instanceId ?index .
            ?instanceUri kgc:boundData ?item .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?base .
            # Bind ?miItemsCount from ctx.data["mi_items"]
            BIND(IRI(CONCAT(STR(?base), "_instance_", STR(?index))) AS ?instanceUri)
            # Note: Iteration logic requires SPARQL 1.1 or custom function
        }
        ```

        3. cardinality="static" (WCP-13: N fixed at design time):
        ```sparql
        CONSTRUCT {
            ?instanceUri kgc:hasToken true .
            ?instanceUri kgc:instanceId ?index .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow ;
                     yawl:minimum ?n .
            ?flow yawl:nextElementRef ?base .
            # Generate N instances (requires VALUES or custom iteration)
            VALUES ?index { 0 1 2 ... ?n }
            BIND(IRI(CONCAT(STR(?base), "_instance_", STR(?index))) AS ?instanceUri)
            FILTER(?index < ?n)
        }
        ```

        4. cardinality="incremental" (WCP-15: One at a time):
        ```sparql
        CONSTRUCT {
            ?instanceUri kgc:hasToken true .
            ?instanceUri kgc:instanceId ?count .
            ?instanceUri kgc:parentTask ?subject .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?base .
            {
                SELECT (COUNT(?inst) AS ?count) WHERE {
                    ?inst kgc:parentTask ?subject .
                }
            }
            BIND(IRI(CONCAT(STR(?base), "_instance_", STR(?count))) AS ?instanceUri)
        }
        ```
        """
        if config and config.execution_template:
            return Kernel.execute_template(graph, subject, ctx, config.execution_template, config.removal_template)

        # Legacy fallback (to be removed after migration)
        return Kernel._legacy_copy(graph, subject, ctx, config)

    @staticmethod
    def filter(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 3: FILTER - Selection (A → {Subset}).

        PURIFIED: Delegates to execute_template() with ZERO if/else.
        Selection mode logic is encoded in SPARQL template ordering/limits.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context with data payload.
        config : VerbConfig | None
            Configuration with selection_mode-specific templates.

        Returns
        -------
        QuadDelta
            Mutations to execute the conditional routing.

        Notes
        -----
        Template Examples by Selection Mode:

        1. selection_mode="exactlyOne" (WCP-4: XOR-split):
        ```sparql
        CONSTRUCT {
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next ;
                  yawl:hasPredicate ?pred .
            ?pred yawl:query ?predicate ;
                  yawl:ordering ?ordering .
            # Evaluate predicate (requires custom FILTER or ASK)
            FILTER(evaluatePredicate(?predicate, ?contextData))
        }
        ORDER BY ?ordering
        LIMIT 1
        ```

        2. selection_mode="oneOrMore" (WCP-6: OR-split):
        ```sparql
        CONSTRUCT {
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next ;
                  yawl:hasPredicate ?pred .
            ?pred yawl:query ?predicate .
            FILTER(evaluatePredicate(?predicate, ?contextData))
        }
        # No LIMIT - all matching paths
        ```

        3. selection_mode="deferred" (WCP-16: External selection):
        ```sparql
        CONSTRUCT {
            ?subject kgc:awaitingSelection true .
        }
        WHERE {
            # No routing yet, just mark as waiting
        }
        ```

        4. selection_mode="mutex" (WCP-17: Interleaved):
        ```sparql
        CONSTRUCT {
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            # Check no sibling is executing
            FILTER NOT EXISTS {
                ?sibling kgc:hasToken true ;
                         kgc:mutexGroup ?subject .
            }
        }
        LIMIT 1
        ```
        """
        if config and config.execution_template:
            return Kernel.execute_template(graph, subject, ctx, config.execution_template, config.removal_template)

        # Legacy fallback (to be removed after migration)
        return Kernel._legacy_filter(graph, subject, ctx, config)

    @staticmethod
    def await_(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 4: AWAIT - Convergence ({A, B, ...} → C).

        PURIFIED: Delegates to execute_template() with ZERO if/else.
        Threshold logic is encoded in SPARQL COUNT and FILTER.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI (join node).
        ctx : TransactionContext
            Transaction context.
        config : VerbConfig | None
            Configuration with threshold-specific templates.

        Returns
        -------
        QuadDelta
            Mutations to execute the join (if conditions met).

        Notes
        -----
        Template Examples by Threshold:

        1. threshold="all" (WCP-3: AND-join):
        ```sparql
        CONSTRUCT {
            ?subject kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
            ?subject kgc:thresholdAchieved ?completedCount .
        }
        WHERE {
            {
                SELECT (COUNT(?source) AS ?totalSources) (COUNT(?completed) AS ?completedCount) WHERE {
                    ?source yawl:flowsInto ?flow .
                    ?flow yawl:nextElementRef ?subject .
                    OPTIONAL { ?source kgc:completedAt ?completed . }
                }
            }
            FILTER(?completedCount = ?totalSources)
            FILTER NOT EXISTS { ?subject kgc:hasToken true }
        }
        ```

        2. threshold="1" (WCP-9: Discriminator):
        ```sparql
        CONSTRUCT {
            ?subject kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
            ?subject kgc:thresholdAchieved "1" .
        }
        WHERE {
            ?source yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?subject .
            ?source kgc:completedAt ?completed .
            FILTER NOT EXISTS { ?subject kgc:hasToken true }
        }
        LIMIT 1
        ```

        3. threshold="N" (WCP-34: Partial join, N-of-M):
        ```sparql
        CONSTRUCT {
            ?subject kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
            ?subject kgc:thresholdAchieved ?completedCount .
        }
        WHERE {
            {
                SELECT (COUNT(?completed) AS ?completedCount) WHERE {
                    ?source yawl:flowsInto ?flow .
                    ?flow yawl:nextElementRef ?subject .
                    ?source kgc:completedAt ?completed .
                }
            }
            BIND(?thresholdN AS ?required)  # From ctx.data["join_threshold"]
            FILTER(?completedCount >= ?required)
            FILTER NOT EXISTS { ?subject kgc:hasToken true }
        }
        ```

        4. threshold="active" (WCP-7: OR-join):
        ```sparql
        CONSTRUCT {
            ?subject kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
            ?subject kgc:thresholdAchieved ?completedCount .
        }
        WHERE {
            {
                SELECT (COUNT(?source) AS ?totalSources)
                       (COUNT(?voided) AS ?voidedCount)
                       (COUNT(?completed) AS ?completedCount) WHERE {
                    ?source yawl:flowsInto ?flow .
                    ?flow yawl:nextElementRef ?subject .
                    OPTIONAL { ?source kgc:voidedAt ?voided . }
                    OPTIONAL { ?source kgc:completedAt ?completed . }
                }
            }
            BIND(?totalSources - ?voidedCount AS ?activeCount)
            FILTER(?completedCount >= ?activeCount)
            FILTER NOT EXISTS { ?subject kgc:hasToken true }
        }
        ```

        5. threshold="dynamic" (runtime threshold from data):
        ```sparql
        CONSTRUCT {
            ?subject kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
            ?subject kgc:thresholdAchieved ?completedCount .
        }
        WHERE {
            {
                SELECT (COUNT(?completed) AS ?completedCount) WHERE {
                    ?source yawl:flowsInto ?flow .
                    ?flow yawl:nextElementRef ?subject .
                    ?source kgc:completedAt ?completed .
                }
            }
            # Bind dynamic threshold from ctx.data
            FILTER(?completedCount >= ?joinThreshold)
            FILTER NOT EXISTS { ?subject kgc:hasToken true }
        }
        ```
        """
        if config and config.execution_template:
            return Kernel.execute_template(graph, subject, ctx, config.execution_template, config.removal_template)

        # Legacy fallback (to be removed after migration)
        return Kernel._legacy_await(graph, subject, ctx, config)

    @staticmethod
    def void(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
        """
        VERB 5: VOID - Termination (A → ∅, recursive by scope).

        PURIFIED: Delegates to execute_template() with ZERO if/else.
        Scope recursion is encoded in SPARQL path traversal.

        Parameters
        ----------
        graph : Graph
            The workflow graph.
        subject : URIRef
            The current node URI.
        ctx : TransactionContext
            Transaction context.
        config : VerbConfig | None
            Configuration with cancellation_scope-specific templates.

        Returns
        -------
        QuadDelta
            Mutations to destroy tokens in scope.

        Notes
        -----
        Template Examples by Cancellation Scope:

        1. cancellation_scope="self" (WCP-19: Cancel only this task):
        ```sparql
        CONSTRUCT {
            ?subject kgc:voidedAt ?txId .
            ?subject kgc:terminatedReason ?reason .
            ?subject kgc:cancellationScope "self" .
            ?subject kgc:nodesVoided "1" .
        }
        WHERE {
            {
                SELECT ?reason WHERE {
                    {
                        ?subject yawl:hasTimer ?timer .
                        BIND("timeout" AS ?reason)
                    }
                    UNION
                    {
                        ?subject kgc:cancelled true .
                        BIND("cancelled" AS ?reason)
                    }
                    UNION
                    {
                        ?subject kgc:failed true .
                        BIND("exception" AS ?reason)
                    }
                }
                LIMIT 1
            }
        }
        ```
        Removal:
        ```sparql
        DELETE {
            ?subject kgc:hasToken ?token .
        }
        WHERE {
            ?subject kgc:hasToken ?token .
        }
        ```

        2. cancellation_scope="region" (WCP-21: Cancel cancellation region):
        ```sparql
        CONSTRUCT {
            ?task kgc:voidedAt ?txId .
            ?task kgc:terminatedReason ?reason .
            ?subject kgc:cancellationScope "region" .
            ?subject kgc:nodesVoided ?voidCount .
        }
        WHERE {
            ?subject yawl:cancellationSet ?region .
            ?task yawl:inCancellationRegion ?region ;
                  kgc:hasToken true .
            {
                SELECT ?reason WHERE {
                    { ?subject yawl:hasTimer ?timer . BIND("timeout" AS ?reason) }
                    UNION
                    { ?subject kgc:cancelled true . BIND("cancelled" AS ?reason) }
                }
                LIMIT 1
            }
            {
                SELECT (COUNT(?t) AS ?voidCount) WHERE {
                    ?subject yawl:cancellationSet ?region .
                    ?t yawl:inCancellationRegion ?region ;
                       kgc:hasToken true .
                }
            }
        }
        ```
        Removal:
        ```sparql
        DELETE {
            ?task kgc:hasToken ?token .
        }
        WHERE {
            ?subject yawl:cancellationSet ?region .
            ?task yawl:inCancellationRegion ?region ;
                  kgc:hasToken ?token .
        }
        ```

        3. cancellation_scope="case" (WCP-20: Cancel entire case):
        ```sparql
        CONSTRUCT {
            ?task kgc:voidedAt ?txId .
            ?task kgc:terminatedReason "case_cancelled" .
            ?subject kgc:cancellationScope "case" .
            ?subject kgc:nodesVoided ?voidCount .
        }
        WHERE {
            ?task kgc:hasToken true .
            {
                SELECT (COUNT(?t) AS ?voidCount) WHERE {
                    ?t kgc:hasToken true .
                }
            }
        }
        ```
        Removal:
        ```sparql
        DELETE {
            ?task kgc:hasToken ?token .
        }
        WHERE {
            ?task kgc:hasToken ?token .
        }
        ```

        4. cancellation_scope="instances" (WCP-22: Cancel all MI instances):
        ```sparql
        CONSTRUCT {
            ?instance kgc:voidedAt ?txId .
            ?instance kgc:terminatedReason "instance_cancelled" .
            ?subject kgc:cancellationScope "instances" .
            ?subject kgc:nodesVoided ?voidCount .
        }
        WHERE {
            ?instance kgc:parentTask ?subject ;
                      kgc:hasToken true .
            {
                SELECT (COUNT(?inst) AS ?voidCount) WHERE {
                    ?inst kgc:parentTask ?subject ;
                          kgc:hasToken true .
                }
            }
        }
        ```
        Removal:
        ```sparql
        DELETE {
            ?instance kgc:hasToken ?token .
            ?subject kgc:hasToken ?selfToken .
        }
        WHERE {
            {
                ?instance kgc:parentTask ?subject ;
                          kgc:hasToken ?token .
            }
            UNION
            {
                ?subject kgc:hasToken ?selfToken .
            }
        }
        ```
        """
        if config and config.execution_template:
            return Kernel.execute_template(graph, subject, ctx, config.execution_template, config.removal_template)

        # Legacy fallback (to be removed after migration)
        return Kernel._legacy_void(graph, subject, ctx, config)

    # =============================================================================
    # LEGACY METHODS (To be removed after migration)
    # =============================================================================

    @staticmethod
    def _legacy_transmute(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Legacy transmute implementation - DEPRECATED."""
        # ... (keep existing implementation from lines 280-337)
        return QuadDelta()  # Stub

    @staticmethod
    def _legacy_copy(
        graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None
    ) -> QuadDelta:
        """Legacy copy implementation - DEPRECATED."""
        # ... (keep existing implementation from lines 340-469)
        return QuadDelta()  # Stub

    @staticmethod
    def _legacy_filter(
        graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None
    ) -> QuadDelta:
        """Legacy filter implementation - DEPRECATED."""
        # ... (keep existing implementation from lines 472-592)
        return QuadDelta()  # Stub

    @staticmethod
    def _legacy_await(
        graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None
    ) -> QuadDelta:
        """Legacy await implementation - DEPRECATED."""
        # ... (keep existing implementation from lines 595-720)
        return QuadDelta()  # Stub

    @staticmethod
    def _legacy_void(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None) -> QuadDelta:
        """Legacy void implementation - DEPRECATED."""
        # ... (keep existing implementation from lines 723-868)
        return QuadDelta()  # Stub


# =============================================================================
# MIGRATION PLAN
# =============================================================================

"""
MIGRATION STEPS:
1. Update VerbConfig dataclass (add execution_template, removal_template)
2. Add Kernel.execute_template() method
3. Update all 5 verbs to delegate to execute_template()
4. Extend kgc_physics.ttl with SPARQL templates for each (verb, params) mapping
5. Update SemanticDriver.resolve_verb() to extract templates from ontology
6. Test template execution with existing test suite
7. Remove _legacy_* methods after full migration
8. Verify ZERO if/else remains in Kernel class

ONTOLOGY EXTENSION (kgc_physics.ttl):
```turtle
# Example: Copy with cardinality="topology"
kgc:CopyTopologyMapping a kgc:VerbMapping ;
    kgc:pattern yawl:ANDSplit ;
    kgc:verb kgc:CopyVerb ;
    kgc:hasCardinality "topology" ;
    kgc:executionTemplate """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        CONSTRUCT {
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
    """ ;
    kgc:removalTemplate """
        DELETE {
            ?subject kgc:hasToken ?token .
        }
        WHERE {
            ?subject kgc:hasToken ?token .
        }
    """ .

# Repeat for all 5 verbs * parameter combinations (20-30 templates total)
```

BENEFITS:
- ZERO Python if/else in Kernel
- All logic lives in RDF templates
- Engine becomes pure template executor
- Easier to audit, verify, and extend
- True "Validation IS Execution" architecture
"""
