"""Pytest fixtures for YAWL workflow pattern tests.

This module provides comprehensive fixtures for testing all 43 W3C YAWL workflow
patterns against the YAWL ontology files.

Fixtures are organized into:
- Graph loading (session-scoped for performance)
- Pattern registry (structured pattern definitions)
- Permutation matrix (valid split-join combinations)
- SPARQL queries (pattern extraction)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

# ============================================================================
# CONSTANTS
# ============================================================================

ONTOLOGY_DIR = Path(__file__).parent.parent.parent / "ontology"
YAWL_CORE = ONTOLOGY_DIR / "yawl.ttl"
YAWL_EXTENDED = ONTOLOGY_DIR / "yawl-extended.ttl"
YAWL_PERMUTATIONS = ONTOLOGY_DIR / "yawl-pattern-permutations.ttl"

# Namespaces from actual ontology files
YAWL_FOUNDATION = Namespace("http://www.yawlfoundation.org/yawlschema#")
YAWL_V2 = Namespace("http://bitflow.ai/ontology/yawl/v2#")
YAWL_EXEC = Namespace("http://bitflow.ai/ontology/yawl/execution/v1#")
YAWL_PATTERN = Namespace("http://bitflow.ai/ontology/yawl/patterns/v1#")


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass(frozen=True)
class PatternDefinition:
    """Structured definition of a YAWL workflow pattern.

    Attributes
    ----------
    pattern_id : int
        W3C pattern identifier (1-43)
    name : str
        Pattern name (e.g., "Sequence", "Parallel Split")
    description : str
        Detailed pattern description
    required_split : str | None
        Required split type (XOR, AND, OR, or None)
    required_join : str | None
        Required join type (XOR, AND, OR, or None)
    requires_predicate : bool
        Whether pattern requires condition evaluation
    requires_quorum : bool
        Whether pattern requires quorum/threshold counting
    uri : str
        RDF URI of the pattern
    """

    pattern_id: int
    name: str
    description: str
    required_split: str | None
    required_join: str | None
    requires_predicate: bool
    requires_quorum: bool
    uri: str


@dataclass(frozen=True)
class PermutationEntry:
    """Valid combination of split and join types.

    Attributes
    ----------
    split_type : str
        Split type (XOR, AND, OR)
    join_type : str
        Join type (XOR, AND, OR, Discriminator)
    is_valid : bool
        Whether this combination is valid in YAWL
    generates_patterns : list[str]
        Pattern names this combination can generate
    uri : str
        RDF URI of the permutation
    """

    split_type: str
    join_type: str
    is_valid: bool
    generates_patterns: tuple[str, ...]
    uri: str


@dataclass
class WorkflowNode:
    """Single node in a workflow graph.

    Attributes
    ----------
    node_id : str
        Unique node identifier
    node_type : str
        Type (Task, ANDSplit, ORSplit, XORSplit, ANDJoin, ORJoin, XORJoin)
    label : str
        Human-readable label
    properties : dict[str, Any]
        Additional node properties
    """

    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SESSION-SCOPED FIXTURES (Expensive Operations)
# ============================================================================


@pytest.fixture(scope="session")
def yawl_graph() -> Graph:
    """Load all YAWL ontology files into a unified RDF graph.

    Returns
    -------
    Graph
        Combined graph with YAWL core, extended patterns, and permutations

    Raises
    ------
    FileNotFoundError
        If any ontology file is missing
    """
    graph = Graph()

    # Load all ontology files (yawl.ttl, yawl-extended.ttl, yawl-pattern-permutations.ttl)
    for ontology_path in [YAWL_CORE, YAWL_EXTENDED, YAWL_PERMUTATIONS]:
        if not ontology_path.exists():
            msg = f"Missing YAWL ontology: {ontology_path}"
            raise FileNotFoundError(msg)
        graph.parse(ontology_path, format="turtle")

    return graph


@pytest.fixture(scope="session")
def pattern_registry(yawl_graph: Graph) -> dict[int, PatternDefinition]:
    """Extract all 43 W3C patterns as structured Python objects.

    Parameters
    ----------
    yawl_graph : Graph
        Unified YAWL graph with all ontologies

    Returns
    -------
    dict[int, PatternDefinition]
        Mapping from pattern ID to structured definition
    """
    registry: dict[int, PatternDefinition] = {}

    # Query for patterns from yawl-extended.ttl
    query = """
        PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>
        PREFIX yawl: <http://bitflow.ai/ontology/yawl/v2#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?pattern ?id ?name ?description ?split ?join ?predicate ?quorum
        WHERE {
            ?pattern a yawl-pattern:WorkflowPattern ;
                     yawl-pattern:patternId ?id ;
                     yawl-pattern:patternName ?name .
            OPTIONAL { ?pattern rdfs:comment ?description }
            OPTIONAL { ?pattern yawl:requiredSplitType ?split }
            OPTIONAL { ?pattern yawl:requiredJoinType ?join }
            OPTIONAL { ?pattern yawl:requiresFlowPredicate ?predicate }
            OPTIONAL { ?pattern yawl:requiresQuorum ?quorum }
        }
        ORDER BY ?id
    """

    for row in yawl_graph.query(query):
        pattern_id = int(row.id)  # type: ignore[attr-defined]
        split_str = None
        join_str = None

        if row.split:  # type: ignore[attr-defined]
            split_uri = str(row.split)  # type: ignore[attr-defined]
            split_str = split_uri.split("#")[-1] if "#" in split_uri else split_uri

        if row.join:  # type: ignore[attr-defined]
            join_uri = str(row.join)  # type: ignore[attr-defined]
            join_str = join_uri.split("#")[-1] if "#" in join_uri else join_uri

        registry[pattern_id] = PatternDefinition(
            pattern_id=pattern_id,
            name=str(row.name),  # type: ignore[attr-defined]
            description=str(row.description) if row.description else "",  # type: ignore[attr-defined]
            required_split=split_str,
            required_join=join_str,
            requires_predicate=bool(row.predicate) if row.predicate else False,  # type: ignore[attr-defined]
            requires_quorum=bool(row.quorum) if row.quorum else False,  # type: ignore[attr-defined]
            uri=str(row.pattern),  # type: ignore[attr-defined]
        )

    return registry


@pytest.fixture(scope="session")
def permutation_matrix(yawl_graph: Graph) -> list[PermutationEntry]:
    """Extract valid split-join combinations from permutation ontology.

    Parameters
    ----------
    yawl_graph : Graph
        Unified YAWL graph with permutation definitions

    Returns
    -------
    list[PermutationEntry]
        All valid and invalid split-join combinations
    """
    permutations: list[PermutationEntry] = []

    # Query from yawl-pattern-permutations.ttl
    query = """
        PREFIX yawl: <http://bitflow.ai/ontology/yawl/v2#>
        PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>

        SELECT ?combo ?split ?join ?valid
        WHERE {
            ?combo a yawl:SplitJoinCombination ;
                   yawl:splitType ?split ;
                   yawl:joinType ?join ;
                   yawl:isValid ?valid .
        }
        ORDER BY ?split ?join
    """

    for row in yawl_graph.query(query):
        split_uri = str(row.split)  # type: ignore[attr-defined]
        join_uri = str(row.join)  # type: ignore[attr-defined]

        split_type = split_uri.split("#")[-1] if "#" in split_uri else split_uri
        join_type = join_uri.split("#")[-1] if "#" in join_uri else join_uri

        # Query for generated patterns
        patterns_query = f"""
            PREFIX yawl: <http://bitflow.ai/ontology/yawl/v2#>
            PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?patternName
            WHERE {{
                <{row.combo}> yawl:generatesPattern ?pattern .
                ?pattern rdfs:label ?patternName .
            }}
        """  # type: ignore[attr-defined]

        pattern_names: list[str] = []
        for pattern_row in yawl_graph.query(patterns_query):
            pattern_names.append(str(pattern_row.patternName))  # type: ignore[attr-defined]

        permutations.append(
            PermutationEntry(
                split_type=split_type,
                join_type=join_type,
                is_valid=str(row.valid).lower() == "true",  # type: ignore[attr-defined]
                generates_patterns=tuple(pattern_names),
                uri=str(row.combo),  # type: ignore[attr-defined]
            )
        )

    return permutations


# ============================================================================
# SPARQL QUERY FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def pattern_count_query() -> str:
    """SPARQL query to count patterns in ontology.

    Returns
    -------
    str
        SPARQL SELECT query for counting patterns
    """
    return """
        PREFIX yawl-pattern: <http://bitflow.ai/ontology/yawl/patterns/v1#>

        SELECT (COUNT(?pattern) AS ?count)
        WHERE {
            ?pattern a yawl-pattern:WorkflowPattern .
        }
    """


@pytest.fixture(scope="session")
def split_types_query() -> str:
    """SPARQL query to get all split types.

    Returns
    -------
    str
        SPARQL SELECT query for split types
    """
    return """
        PREFIX yawl: <http://bitflow.ai/ontology/yawl/v2#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?split ?label
        WHERE {
            ?split a yawl:SplitType .
            OPTIONAL { ?split rdfs:label ?label }
        }
    """


@pytest.fixture(scope="session")
def join_types_query() -> str:
    """SPARQL query to get all join types.

    Returns
    -------
    str
        SPARQL SELECT query for join types
    """
    return """
        PREFIX yawl: <http://bitflow.ai/ontology/yawl/v2#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?join ?label
        WHERE {
            ?join a yawl:JoinType .
            OPTIONAL { ?join rdfs:label ?label }
        }
    """


# ============================================================================
# WORKFLOW BUILDER
# ============================================================================


class WorkflowBuilder:
    """Fluent builder for creating YAWL workflow graphs.

    Parameters
    ----------
    base_uri : str
        Base URI for workflow elements
    """

    def __init__(self, base_uri: str = "http://example.org/workflow/") -> None:
        """Initialize workflow builder."""
        self.base_uri = base_uri
        self.graph = Graph()
        self.graph.bind("yawl", YAWL_V2)
        self.graph.bind("yawl-pattern", YAWL_PATTERN)
        self.nodes: list[WorkflowNode] = []
        self.edges: list[tuple[str, str, dict[str, Any]]] = []

    def add_task(self, task_id: str, label: str, **properties: Any) -> WorkflowBuilder:
        """Add atomic task node to workflow.

        Parameters
        ----------
        task_id : str
            Unique task identifier
        label : str
            Human-readable task label
        **properties : Any
            Additional task properties

        Returns
        -------
        WorkflowBuilder
            Self for method chaining
        """
        node = WorkflowNode(
            node_id=task_id, node_type="Task", label=label, properties=properties
        )
        self.nodes.append(node)

        task_uri = URIRef(f"{self.base_uri}{task_id}")
        self.graph.add((task_uri, RDF.type, YAWL_V2.Task))
        self.graph.add((task_uri, RDFS.label, Literal(label)))

        for key, value in properties.items():
            self.graph.add((task_uri, YAWL_V2[key], Literal(value)))

        return self

    def add_split(
        self, split_id: str, split_type: str, label: str, **properties: Any
    ) -> WorkflowBuilder:
        """Add split node (XOR, AND, OR) to workflow.

        Parameters
        ----------
        split_id : str
            Unique split identifier
        split_type : str
            Split type (XOR, AND, OR)
        label : str
            Human-readable split label
        **properties : Any
            Additional split properties

        Returns
        -------
        WorkflowBuilder
            Self for method chaining
        """
        node = WorkflowNode(
            node_id=split_id,
            node_type=f"{split_type}Split",
            label=label,
            properties=properties,
        )
        self.nodes.append(node)

        split_uri = URIRef(f"{self.base_uri}{split_id}")
        self.graph.add((split_uri, RDF.type, YAWL_V2.Split))
        self.graph.add((split_uri, YAWL_V2.splitType, YAWL_V2[split_type]))
        self.graph.add((split_uri, RDFS.label, Literal(label)))

        for key, value in properties.items():
            self.graph.add((split_uri, YAWL_V2[key], Literal(value)))

        return self

    def add_join(
        self, join_id: str, join_type: str, label: str, **properties: Any
    ) -> WorkflowBuilder:
        """Add join node (XOR, AND, OR, Discriminator) to workflow.

        Parameters
        ----------
        join_id : str
            Unique join identifier
        join_type : str
            Join type (XOR, AND, OR, Discriminator)
        label : str
            Human-readable join label
        **properties : Any
            Additional join properties

        Returns
        -------
        WorkflowBuilder
            Self for method chaining
        """
        node = WorkflowNode(
            node_id=join_id,
            node_type=f"{join_type}Join",
            label=label,
            properties=properties,
        )
        self.nodes.append(node)

        join_uri = URIRef(f"{self.base_uri}{join_id}")
        self.graph.add((join_uri, RDF.type, YAWL_V2.Join))
        self.graph.add((join_uri, YAWL_V2.joinType, YAWL_V2[join_type]))
        self.graph.add((join_uri, RDFS.label, Literal(label)))

        for key, value in properties.items():
            self.graph.add((join_uri, YAWL_V2[key], Literal(value)))

        return self

    def connect(self, from_id: str, to_id: str, **properties: Any) -> WorkflowBuilder:
        """Connect two nodes with a control flow edge.

        Parameters
        ----------
        from_id : str
            Source node identifier
        to_id : str
            Target node identifier
        **properties : Any
            Edge properties (e.g., condition, probability)

        Returns
        -------
        WorkflowBuilder
            Self for method chaining
        """
        self.edges.append((from_id, to_id, properties))

        from_uri = URIRef(f"{self.base_uri}{from_id}")
        to_uri = URIRef(f"{self.base_uri}{to_id}")
        self.graph.add((from_uri, YAWL_V2.flowsTo, to_uri))

        if properties:
            edge_uri = URIRef(f"{self.base_uri}edge_{from_id}_{to_id}")
            self.graph.add((edge_uri, RDF.type, YAWL_V2.Flow))
            self.graph.add((edge_uri, YAWL_V2.source, from_uri))
            self.graph.add((edge_uri, YAWL_V2.target, to_uri))
            for key, value in properties.items():
                self.graph.add((edge_uri, YAWL_V2[key], Literal(value)))

        return self

    def build(self) -> Graph:
        """Build final workflow graph.

        Returns
        -------
        Graph
            Complete workflow graph with all nodes and edges
        """
        return self.graph

    def get_nodes(self) -> list[WorkflowNode]:
        """Get all nodes in workflow.

        Returns
        -------
        list[WorkflowNode]
            All workflow nodes
        """
        return self.nodes.copy()

    def get_edges(self) -> list[tuple[str, str, dict[str, Any]]]:
        """Get all edges in workflow.

        Returns
        -------
        list[tuple[str, str, dict[str, Any]]]
            All workflow edges as (from, to, properties) tuples
        """
        return self.edges.copy()


@pytest.fixture
def workflow_builder() -> WorkflowBuilder:
    """Create fresh workflow builder for each test.

    Returns
    -------
    WorkflowBuilder
        Fresh builder instance
    """
    return WorkflowBuilder()


# ============================================================================
# SAMPLE WORKFLOW FIXTURES (Patterns 1-10)
# ============================================================================


@pytest.fixture
def sequence_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 1: Sequence (A -> B).

    Returns
    -------
    Graph
        Workflow with sequential task execution
    """
    return (
        workflow_builder.add_task("A", "Task A")
        .add_task("B", "Task B")
        .connect("A", "B")
        .build()
    )


@pytest.fixture
def parallel_split_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 2: Parallel Split (A -> [B, C, D]).

    Returns
    -------
    Graph
        Workflow with AND-split diverging to multiple branches
    """
    return (
        workflow_builder.add_task("A", "Task A")
        .add_split("split1", "AND", "Parallel Split")
        .add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_task("D", "Task D")
        .connect("A", "split1")
        .connect("split1", "B")
        .connect("split1", "C")
        .connect("split1", "D")
        .build()
    )


@pytest.fixture
def synchronization_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 3: Synchronization ([B, C] -> D).

    Returns
    -------
    Graph
        Workflow with AND-join merging multiple branches
    """
    return (
        workflow_builder.add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_join("join1", "AND", "Synchronization")
        .add_task("D", "Task D")
        .connect("B", "join1")
        .connect("C", "join1")
        .connect("join1", "D")
        .build()
    )


@pytest.fixture
def exclusive_choice_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 4: Exclusive Choice (A -> XOR -> [B, C]).

    Returns
    -------
    Graph
        Workflow with XOR-split based on condition
    """
    return (
        workflow_builder.add_task("A", "Task A")
        .add_split("split1", "XOR", "Exclusive Choice")
        .add_task("B", "Task B")
        .add_task("C", "Task C")
        .connect("A", "split1")
        .connect("split1", "B", condition="x > 5")
        .connect("split1", "C", condition="x <= 5")
        .build()
    )


@pytest.fixture
def simple_merge_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 5: Simple Merge ([B, C] -> XOR -> D).

    Returns
    -------
    Graph
        Workflow with XOR-join merging alternative branches
    """
    return (
        workflow_builder.add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_join("join1", "XOR", "Simple Merge")
        .add_task("D", "Task D")
        .connect("B", "join1")
        .connect("C", "join1")
        .connect("join1", "D")
        .build()
    )


@pytest.fixture
def multi_choice_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 6: Multi-Choice (A -> OR -> [B, C, D]).

    Returns
    -------
    Graph
        Workflow with OR-split enabling multiple branches
    """
    return (
        workflow_builder.add_task("A", "Task A")
        .add_split("split1", "OR", "Multi-Choice")
        .add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_task("D", "Task D")
        .connect("A", "split1")
        .connect("split1", "B", condition="cond_b")
        .connect("split1", "C", condition="cond_c")
        .connect("split1", "D", condition="cond_d")
        .build()
    )


@pytest.fixture
def sync_merge_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 7: Synchronizing Merge (OR-split -> OR-join).

    Returns
    -------
    Graph
        Workflow with balanced OR-split and OR-join
    """
    return (
        workflow_builder.add_task("A", "Task A")
        .add_split("split1", "OR", "Multi-Choice")
        .add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_join("join1", "OR", "Sync Merge")
        .add_task("D", "Task D")
        .connect("A", "split1")
        .connect("split1", "B", condition="cond_b")
        .connect("split1", "C", condition="cond_c")
        .connect("B", "join1")
        .connect("C", "join1")
        .connect("join1", "D")
        .build()
    )


@pytest.fixture
def multi_merge_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 8: Multiple Merge ([B, C] -> D without sync).

    Returns
    -------
    Graph
        Workflow where task D executes multiple times
    """
    return (
        workflow_builder.add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_task("D", "Task D")
        .connect("B", "D")
        .connect("C", "D")
        .build()
    )


@pytest.fixture
def discriminator_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 9: Discriminator ([B, C, D] -> first -> E).

    Returns
    -------
    Graph
        Workflow where E executes on first completion
    """
    return (
        workflow_builder.add_task("B", "Task B")
        .add_task("C", "Task C")
        .add_task("D", "Task D")
        .add_join("join1", "Discriminator", "Discriminator", quorum=1)
        .add_task("E", "Task E")
        .connect("B", "join1")
        .connect("C", "join1")
        .connect("D", "join1")
        .connect("join1", "E")
        .build()
    )


@pytest.fixture
def arbitrary_cycles_workflow(workflow_builder: WorkflowBuilder) -> Graph:
    """Pattern 10: Arbitrary Cycles (A -> B -> C -> B loop).

    Returns
    -------
    Graph
        Workflow with arbitrary looping structure
    """
    return (
        workflow_builder.add_task("A", "Task A")
        .add_task("B", "Task B")
        .add_task("C", "Task C")
        .connect("A", "B")
        .connect("B", "C")
        .connect("C", "B", condition="retry")
        .build()
    )


# ============================================================================
# HELPER FIXTURES
# ============================================================================


@pytest.fixture
def empty_graph() -> Graph:
    """Create empty RDF graph for custom workflow construction.

    Returns
    -------
    Graph
        Fresh empty graph
    """
    return Graph()


@pytest.fixture(scope="session")
def all_43_pattern_ids() -> list[int]:
    """All 43 W3C pattern IDs.

    Returns
    -------
    list[int]
        List of pattern IDs from 1 to 43
    """
    return list(range(1, 44))
