"""SPARQL queries for extracting YAWL pattern information from ontologies.

This module provides SPARQL queries and helper functions to extract:
- All 43 workflow pattern definitions
- Permutation matrix entries (split-join combinations)
- Workflow validation against patterns
- Execution semantics and policies

References
----------
- YAWL Foundation: http://www.yawlfoundation.org/
- Workflow Patterns: http://www.workflowpatterns.com/
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from urllib.parse import quote as url_quote

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.query import ResultRow

if TYPE_CHECKING:
    from collections.abc import Sequence


def escape_sparql_uri(uri: str | URIRef) -> str:
    """Escape a URI for safe SPARQL query interpolation.

    Prevents SPARQL injection by escaping special characters that could break
    out of the <uri> syntax in SPARQL queries.

    Parameters
    ----------
    uri : str | URIRef
        The URI to escape

    Returns
    -------
    str
        The escaped URI safe for SPARQL interpolation

    Raises
    ------
    ValueError
        If URI contains characters that cannot be safely escaped

    Examples
    --------
    >>> escape_sparql_uri("urn:task:test")
    'urn:task:test'
    >>> escape_sparql_uri("urn:task:with space")
    'urn:task:with%20space'
    """
    uri_str = str(uri)

    # Check for injection characters that should never appear in URIs
    injection_chars = {">", "<", '"', "'", "\\", "\n", "\r", "\t"}
    if any(char in uri_str for char in injection_chars):
        # URL-encode the problematic characters
        uri_str = url_quote(uri_str, safe=":/#@!$&()*+,;=?")

    # Validate URI structure (basic RFC 3986 check)
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", uri_str):
        msg = f"Invalid URI scheme: {uri_str[:50]}"
        raise ValueError(msg)

    return uri_str


def sparql_uri(uri: str | URIRef) -> str:
    """Format a URI for SPARQL query with angle brackets.

    Combines escaping and formatting for safe SPARQL URI usage.

    Parameters
    ----------
    uri : str | URIRef
        The URI to format

    Returns
    -------
    str
        The URI wrapped in angle brackets: <uri>

    Examples
    --------
    >>> sparql_uri("urn:task:test")
    '<urn:task:test>'
    """
    return f"<{escape_sparql_uri(uri)}>"


# YAWL Ontology Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
YAWL2 = Namespace("http://bitflow.ai/ontology/yawl/v2#")
YAWL_EXEC = Namespace("http://bitflow.ai/ontology/yawl/execution/v1#")
YAWL_PATTERN = Namespace("http://bitflow.ai/ontology/yawl/patterns/v1#")

# SPARQL Query Constants
PATTERN_EXTRACTION_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?pattern ?id ?name ?description ?split ?join ?predicate ?quorum ?category
WHERE {
    ?pattern a yawl-pattern:WorkflowPattern ;
             yawl-pattern:patternId ?id ;
             yawl-pattern:patternName ?name .
    OPTIONAL { ?pattern rdfs:comment ?description }
    OPTIONAL { ?pattern yawl-pattern:patternCategory ?category }
    OPTIONAL { ?pattern yawl:requiredSplitType ?split }
    OPTIONAL { ?pattern yawl:requiredJoinType ?join }
    OPTIONAL { ?pattern yawl:requiresFlowPredicate ?predicate }
    OPTIONAL { ?pattern yawl:requiresQuorum ?quorum }
}
ORDER BY ?id
"""

PERMUTATION_MATRIX_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

SELECT ?combo ?split ?join ?valid ?patterns ?description
WHERE {
    ?combo a yawl:SplitJoinCombination ;
           yawl:splitType ?split ;
           yawl:joinType ?join ;
           yawl:isValid ?valid .
    OPTIONAL { ?combo yawl:generatesPattern ?patterns }
    OPTIONAL { ?combo rdfs:comment ?description }
}
ORDER BY ?split ?join
"""

TASK_CONFIGURATION_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX yawl-exec: <http://bitflow.ai/ontology/yawl/execution/v1#>

SELECT ?task ?split ?join ?timer ?resourcing ?cancellation
WHERE {
    ?task a yawl:Task .
    OPTIONAL { ?task yawl:hasSplit ?split }
    OPTIONAL { ?task yawl:hasJoin ?join }
    OPTIONAL { ?task yawl:hasTimer ?timer }
    OPTIONAL { ?task yawl:hasResourcing ?resourcing }
    OPTIONAL { ?task yawl:hasCancellationRegion ?cancellation }
}
"""

FLOW_TOPOLOGY_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

SELECT ?source ?flow ?target ?predicate ?default ?priority ?evaluation
WHERE {
    ?source yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
    OPTIONAL { ?flow yawl:hasPredicate ?predicate }
    OPTIONAL { ?flow yawl:isDefaultFlow ?default }
    OPTIONAL { ?flow yawl:hasPriority ?priority }
    OPTIONAL { ?flow yawl:evaluationOrder ?evaluation }
}
"""

PATTERN_VALIDATION_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

ASK {
    # Check if workflow uses valid split-join combination
    ?task yawl:hasSplit ?split ;
          yawl:hasJoin ?join .

    # Find matching permutation entry
    ?combo a yawl:SplitJoinCombination ;
           yawl:splitType ?split ;
           yawl:joinType ?join ;
           yawl:isValid true .
}
"""

EXECUTION_SEMANTICS_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX yawl-exec: <http://bitflow.ai/ontology/yawl/execution/v1#>

SELECT ?task ?mode ?timeout ?retry ?duration ?maxInstances ?threshold
WHERE {
    ?task a yawl:Task .
    OPTIONAL { ?task yawl-exec:executionMode ?mode }
    OPTIONAL { ?task yawl-exec:timeoutPolicy ?timeout }
    OPTIONAL { ?task yawl-exec:retryPolicy ?retry }
    OPTIONAL { ?task yawl-exec:taskDuration ?duration }
    OPTIONAL { ?task yawl:maxInstances ?maxInstances }
    OPTIONAL { ?task yawl:threshold ?threshold }
}
"""

PATTERN_BY_CATEGORY_QUERY = """
PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>

SELECT ?pattern ?id ?name ?category
WHERE {
    ?pattern a yawl-pattern:WorkflowPattern ;
             yawl-pattern:patternId ?id ;
             yawl-pattern:patternName ?name ;
             yawl-pattern:patternCategory ?category .
    FILTER(?category = ?targetCategory)
}
ORDER BY ?id
"""

WORKFLOW_PATTERNS_QUERY = """
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>

SELECT DISTINCT ?pattern ?id ?name
WHERE {
    # Find all tasks in the workflow
    ?workflow yawl:hasTask ?task .

    # Extract split-join configuration
    ?task yawl:hasSplit ?split ;
          yawl:hasJoin ?join .

    # Find matching permutation
    ?combo a yawl:SplitJoinCombination ;
           yawl:splitType ?split ;
           yawl:joinType ?join ;
           yawl:generatesPattern ?patternIds .

    # Match to pattern definitions
    ?pattern a yawl-pattern:WorkflowPattern ;
             yawl-pattern:patternId ?id ;
             yawl-pattern:patternName ?name .

    # Filter patterns present in this workflow
    FILTER(CONTAINS(?patternIds, STR(?id)))
}
ORDER BY ?id
"""


@dataclass(frozen=True)
class PatternDefinition:
    """Workflow pattern definition extracted from ontology.

    Attributes
    ----------
    pattern_uri : str
        URI of the pattern in the ontology
    pattern_id : int
        Numeric pattern identifier (1-43)
    name : str
        Human-readable pattern name
    description : str | None
        Detailed pattern description
    category : str | None
        Pattern category (control-flow, data, resource, exception)
    required_split : str | None
        Required split type (AND, OR, XOR)
    required_join : str | None
        Required join type (AND, OR, XOR)
    requires_predicate : bool
        Whether pattern requires flow predicates
    requires_quorum : bool
        Whether pattern requires quorum value
    """

    pattern_uri: str
    pattern_id: int
    name: str
    description: str | None
    category: str | None
    required_split: str | None
    required_join: str | None
    requires_predicate: bool
    requires_quorum: bool


@dataclass(frozen=True)
class PermutationEntry:
    """Split-join permutation matrix entry.

    Attributes
    ----------
    combination_uri : str
        URI of the combination in the ontology
    split_type : str
        Split type (AND, OR, XOR, NONE)
    join_type : str
        Join type (AND, OR, XOR, NONE)
    is_valid : bool
        Whether this combination is valid in YAWL
    generated_patterns : list[int]
        Pattern IDs generated by this combination
    description : str | None
        Description of the combination
    """

    combination_uri: str
    split_type: str
    join_type: str
    is_valid: bool
    generated_patterns: list[int]
    description: str | None


@dataclass(frozen=True)
class TaskConfiguration:
    """Task configuration extracted from workflow.

    Attributes
    ----------
    task_uri : str
        URI of the task
    split_type : str | None
        Configured split type
    join_type : str | None
        Configured join type
    timer_uri : str | None
        Timer configuration URI
    resourcing_uri : str | None
        Resourcing configuration URI
    cancellation_region : str | None
        Cancellation region URI
    """

    task_uri: str
    split_type: str | None
    join_type: str | None
    timer_uri: str | None
    resourcing_uri: str | None
    cancellation_region: str | None


@dataclass(frozen=True)
class FlowDefinition:
    """Control flow edge definition.

    Attributes
    ----------
    source_uri : str
        Source task/condition URI
    flow_uri : str
        Flow edge URI
    target_uri : str
        Target task/condition URI
    predicate : str | None
        XPath flow predicate
    is_default : bool
        Whether this is the default flow
    priority : int | None
        Flow priority (for ordering)
    evaluation_order : int | None
        Evaluation order for predicates
    """

    source_uri: str
    flow_uri: str
    target_uri: str
    predicate: str | None
    is_default: bool
    priority: int | None
    evaluation_order: int | None


@dataclass(frozen=True)
class ExecutionSemantics:
    """Task execution semantics and policies.

    Attributes
    ----------
    task_uri : str
        URI of the task
    execution_mode : str | None
        Execution mode (automatic, manual, service)
    timeout_policy : str | None
        Timeout policy URI
    retry_policy : str | None
        Retry policy URI
    duration : str | None
        Expected task duration (ISO 8601)
    max_instances : int | None
        Maximum concurrent instances
    threshold : int | None
        Threshold for multiple instance tasks
    """

    task_uri: str
    execution_mode: str | None
    timeout_policy: str | None
    retry_policy: str | None
    duration: str | None
    max_instances: int | None
    threshold: int | None


def extract_all_patterns(graph: Graph) -> list[PatternDefinition]:
    """Extract all 43 workflow patterns from the ontology.

    Parameters
    ----------
    graph : Graph
        RDF graph containing YAWL ontologies

    Returns
    -------
    list[PatternDefinition]
        All pattern definitions sorted by pattern ID
    """
    results = graph.query(PATTERN_EXTRACTION_QUERY)
    patterns: list[PatternDefinition] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        patterns.append(
            PatternDefinition(
                pattern_uri=str(row_typed.pattern),
                pattern_id=int(row_typed.id),
                name=str(row_typed.name),
                description=str(row_typed.description)
                if row_typed.description
                else None,
                category=str(row_typed.category) if row_typed.category else None,
                required_split=str(row_typed.split) if row_typed.split else None,
                required_join=str(row_typed.join) if row_typed.join else None,
                requires_predicate=bool(row_typed.predicate)
                if row_typed.predicate
                else False,
                requires_quorum=bool(row_typed.quorum) if row_typed.quorum else False,
            )
        )

    return patterns


def extract_permutation_matrix(graph: Graph) -> list[PermutationEntry]:
    """Extract the split-join permutation matrix.

    Parameters
    ----------
    graph : Graph
        RDF graph containing YAWL ontologies

    Returns
    -------
    list[PermutationEntry]
        All permutation entries sorted by split and join types
    """
    results = graph.query(PERMUTATION_MATRIX_QUERY)
    entries: list[PermutationEntry] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        # Parse pattern IDs from comma-separated string
        pattern_ids: list[int] = []
        if row_typed.patterns:
            pattern_str = str(row_typed.patterns)
            pattern_ids = [int(pid.strip()) for pid in pattern_str.split(",")]

        entries.append(
            PermutationEntry(
                combination_uri=str(row_typed.combo),
                split_type=str(row_typed.split),
                join_type=str(row_typed.join),
                is_valid=bool(row_typed.valid),
                generated_patterns=pattern_ids,
                description=str(row_typed.description)
                if row_typed.description
                else None,
            )
        )

    return entries


def extract_task_configurations(graph: Graph) -> list[TaskConfiguration]:
    """Extract task configurations from workflow.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow definition

    Returns
    -------
    list[TaskConfiguration]
        All task configurations in the workflow
    """
    results = graph.query(TASK_CONFIGURATION_QUERY)
    configs: list[TaskConfiguration] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        configs.append(
            TaskConfiguration(
                task_uri=str(row_typed.task),
                split_type=str(row_typed.split) if row_typed.split else None,
                join_type=str(row_typed.join) if row_typed.join else None,
                timer_uri=str(row_typed.timer) if row_typed.timer else None,
                resourcing_uri=str(row_typed.resourcing)
                if row_typed.resourcing
                else None,
                cancellation_region=str(row_typed.cancellation)
                if row_typed.cancellation
                else None,
            )
        )

    return configs


def extract_flow_topology(graph: Graph) -> list[FlowDefinition]:
    """Extract control flow topology from workflow.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow definition

    Returns
    -------
    list[FlowDefinition]
        All flow edges in the workflow
    """
    results = graph.query(FLOW_TOPOLOGY_QUERY)
    flows: list[FlowDefinition] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        flows.append(
            FlowDefinition(
                source_uri=str(row_typed.source),
                flow_uri=str(row_typed.flow),
                target_uri=str(row_typed.target),
                predicate=str(row_typed.predicate) if row_typed.predicate else None,
                is_default=bool(row_typed.default) if row_typed.default else False,
                priority=int(row_typed.priority) if row_typed.priority else None,
                evaluation_order=int(row_typed.evaluation)
                if row_typed.evaluation
                else None,
            )
        )

    return flows


def validate_workflow(graph: Graph, workflow_uri: str) -> bool:
    """Validate that workflow uses only valid split-join combinations.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow and ontology
    workflow_uri : str
        URI of the workflow to validate

    Returns
    -------
    bool
        True if all task split-join combinations are valid
    """
    # Bind workflow URI to query
    query_with_binding = f"""
    PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

    ASK {{
        <{workflow_uri}> yawl:hasTask ?task .
        ?task yawl:hasSplit ?split ;
              yawl:hasJoin ?join .

        ?combo a yawl:SplitJoinCombination ;
               yawl:splitType ?split ;
               yawl:joinType ?join ;
               yawl:isValid true .
    }}
    """
    result = graph.query(query_with_binding)
    return bool(result.askAnswer)


def extract_execution_semantics(graph: Graph) -> list[ExecutionSemantics]:
    """Extract task execution semantics and policies.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow definition

    Returns
    -------
    list[ExecutionSemantics]
        Execution semantics for all tasks
    """
    results = graph.query(EXECUTION_SEMANTICS_QUERY)
    semantics: list[ExecutionSemantics] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        semantics.append(
            ExecutionSemantics(
                task_uri=str(row_typed.task),
                execution_mode=str(row_typed.mode) if row_typed.mode else None,
                timeout_policy=str(row_typed.timeout) if row_typed.timeout else None,
                retry_policy=str(row_typed.retry) if row_typed.retry else None,
                duration=str(row_typed.duration) if row_typed.duration else None,
                max_instances=int(row_typed.maxInstances)
                if row_typed.maxInstances
                else None,
                threshold=int(row_typed.threshold) if row_typed.threshold else None,
            )
        )

    return semantics


def extract_patterns_by_category(
    graph: Graph, category: str
) -> list[PatternDefinition]:
    """Extract patterns filtered by category.

    Parameters
    ----------
    graph : Graph
        RDF graph containing YAWL ontologies
    category : str
        Pattern category (control-flow, data, resource, exception)

    Returns
    -------
    list[PatternDefinition]
        Patterns in the specified category
    """
    query = PATTERN_BY_CATEGORY_QUERY.replace("?targetCategory", f'"{category}"')
    results = graph.query(query)
    patterns: list[PatternDefinition] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        patterns.append(
            PatternDefinition(
                pattern_uri=str(row_typed.pattern),
                pattern_id=int(row_typed.id),
                name=str(row_typed.name),
                description=None,
                category=category,
                required_split=None,
                required_join=None,
                requires_predicate=False,
                requires_quorum=False,
            )
        )

    return patterns


def extract_workflow_patterns(
    graph: Graph, workflow_uri: str
) -> list[PatternDefinition]:
    """Extract all patterns used in a specific workflow.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow and ontology
    workflow_uri : str
        URI of the workflow to analyze

    Returns
    -------
    list[PatternDefinition]
        Patterns present in the workflow
    """
    query_with_binding = WORKFLOW_PATTERNS_QUERY.replace(
        "?workflow", sparql_uri(workflow_uri)
    )
    results = graph.query(query_with_binding)
    patterns: list[PatternDefinition] = []

    for row in results:
        row_typed = cast(ResultRow, row)
        patterns.append(
            PatternDefinition(
                pattern_uri=str(row_typed.pattern),
                pattern_id=int(row_typed.id),
                name=str(row_typed.name),
                description=None,
                category=None,
                required_split=None,
                required_join=None,
                requires_predicate=False,
                requires_quorum=False,
            )
        )

    return patterns


def validate_pattern_requirements(
    graph: Graph, task_uri: str, pattern: PatternDefinition
) -> bool:
    """Validate that a task meets all requirements for a specific pattern.

    Parameters
    ----------
    graph : Graph
        RDF graph containing workflow definition
    task_uri : str
        URI of the task to validate
    pattern : PatternDefinition
        Pattern definition with requirements

    Returns
    -------
    bool
        True if task meets all pattern requirements
    """
    # Escape task URI once for all queries
    safe_task = sparql_uri(task_uri)

    # Check split type requirement (compare literals, not URIs)
    if pattern.required_split:
        query = f"""
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {{
            {safe_task} yawl:hasSplit "{pattern.required_split}" .
        }}
        """
        if not bool(graph.query(query).askAnswer):
            return False

    # Check join type requirement (compare literals, not URIs)
    if pattern.required_join:
        query = f"""
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {{
            {safe_task} yawl:hasJoin "{pattern.required_join}" .
        }}
        """
        if not bool(graph.query(query).askAnswer):
            return False

    # Check flow predicate requirement
    if pattern.requires_predicate:
        query = f"""
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {{
            {safe_task} yawl:flowsInto ?flow .
            ?flow yawl:hasPredicate ?pred .
            FILTER(BOUND(?pred))
        }}
        """
        if not bool(graph.query(query).askAnswer):
            return False

    # Check quorum requirement
    if pattern.requires_quorum:
        query = f"""
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {{
            {safe_task} yawl:threshold ?threshold .
            FILTER(BOUND(?threshold))
        }}
        """
        if not bool(graph.query(query).askAnswer):
            return False

    return True
