"""
KGC OS Graph Agent Ontology Package.

Complete RDF/SHACL ontology for the Knowledge Graph Comprehension OS Graph Agent system.

This package contains W3C-compliant Turtle (.ttl) files defining:
- Core ontology with class hierarchy and properties
- SHACL validation shapes for data quality
- Feature template catalog for behavioral analysis
- Capability registry with PyObjC bindings
- Example instance data demonstrating usage

Files:
    core.ttl: Main ontology (22 classes, 40 properties)
    shapes.ttl: SHACL validation (22 node shapes)
    features.ttl: Feature templates (10 templates)
    capabilities.ttl: Capability registry (12 capabilities, 5 frameworks)
    examples.ttl: Instance data examples (9 feature instances)

Usage:
    from pathlib import Path
    from rdflib import Graph

    ontology_dir = Path(__file__).parent

    # Load core ontology
    g = Graph()
    g.parse(ontology_dir / "core.ttl", format="turtle")

    # Load all ontology files
    for ttl_file in ontology_dir.glob("*.ttl"):
        g.parse(ttl_file, format="turtle")

For TTL2DSPy integration:
    from ttl2dspy import TTLParser

    parser = TTLParser()
    parser.parse_file(ontology_dir / "core.ttl")
    parser.parse_file(ontology_dir / "shapes.ttl")

    classes = parser.generate_python_classes()

Statistics:
    - Total triples: 1,458
    - Classes: 22
    - Properties: 40 (15 object, 25 datatype)
    - SHACL shapes: 22
    - Feature templates: 10
    - Capabilities: 12
    - W3C compliant: Yes
    - TTL2DSPy ready: Yes

Version: 1.0.0
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rdflib import Graph

__version__ = "1.0.0"
__all__ = [
    "CAPABILITIES_TTL",
    "CORE_TTL",
    "EXAMPLES_TTL",
    "FEATURES_TTL",
    "ONTOLOGY_DIR",
    "SHAPES_TTL",
    "load_ontology",
]

# Directory paths
ONTOLOGY_DIR = Path(__file__).parent

# Individual file paths
CORE_TTL = ONTOLOGY_DIR / "core.ttl"
SHAPES_TTL = ONTOLOGY_DIR / "shapes.ttl"
FEATURES_TTL = ONTOLOGY_DIR / "features.ttl"
CAPABILITIES_TTL = ONTOLOGY_DIR / "capabilities.ttl"
EXAMPLES_TTL = ONTOLOGY_DIR / "examples.ttl"


def load_ontology(include_examples: bool = False) -> "Graph":
    """
    Load the complete KGC ontology into an rdflib Graph.

    Args:
        include_examples: If True, include example instance data

    Returns
    -------
        rdflib.Graph containing the ontology

    Raises
    ------
        ImportError: If rdflib is not installed
        FileNotFoundError: If ontology files are missing

    Example:
        >>> from kgcl.ontology import load_ontology
        >>> g = load_ontology()
        >>> print(f"Loaded {len(g)} triples")
        Loaded 1158 triples
    """
    try:
        from rdflib import Graph
    except ImportError:
        raise ImportError("rdflib is required to load the ontology. Install with: pip install rdflib")

    g = Graph()

    # Load core ontology files
    ontology_files = [CORE_TTL, SHAPES_TTL, FEATURES_TTL, CAPABILITIES_TTL]

    if include_examples:
        ontology_files.append(EXAMPLES_TTL)

    for ttl_file in ontology_files:
        if not ttl_file.exists():
            raise FileNotFoundError(f"Ontology file not found: {ttl_file}")
        g.parse(ttl_file, format="turtle")

    return g


def validate_instance_data(data_graph: "Graph", shapes_graph: "Graph | None" = None) -> tuple[bool, "Graph", str]:
    """
    Validate instance data against SHACL shapes.

    Args:
        data_graph: rdflib.Graph containing instance data to validate
        shapes_graph: Optional Graph containing SHACL shapes (loads shapes.ttl if not provided)

    Returns
    -------
        Tuple of (conforms: bool, results_graph: Graph, results_text: str)

    Raises
    ------
        ImportError: If pyshacl is not installed

    Example:
        >>> from rdflib import Graph
        >>> from kgcl.ontology import validate_instance_data
        >>>
        >>> data = Graph()
        >>> data.parse("my_data.ttl", format="turtle")
        >>> conforms, results_graph, results_text = validate_instance_data(data)
        >>> if not conforms:
        ...     print("Validation errors:")
        ...     print(results_text)
    """
    try:
        from pyshacl import validate
    except ImportError:
        raise ImportError("pyshacl is required for SHACL validation. Install with: pip install pyshacl")

    if shapes_graph is None:
        from rdflib import Graph

        shapes_graph = Graph()
        shapes_graph.parse(SHAPES_TTL, format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
    )

    return conforms, results_graph, results_text


def get_ontology_statistics() -> dict[str, int]:
    """
    Get statistics about the ontology.

    Returns
    -------
        Dictionary containing counts of classes, properties, shapes, etc.

    Example:
        >>> from kgcl.ontology import get_ontology_statistics
        >>> stats = get_ontology_statistics()
        >>> print(f"Classes: {stats['classes']}")
        Classes: 22
    """
    try:
        from rdflib import OWL, RDF, Graph, Namespace
        from rdflib.namespace import RDFS
    except ImportError:
        raise ImportError("rdflib is required. Install with: pip install rdflib")

    g = load_ontology(include_examples=False)

    CORE = Namespace("http://kgcl.dev/ontology/core#")
    SHACL = Namespace("http://www.w3.org/ns/shacl#")

    stats = {
        "total_triples": len(g),
        "classes": len(list(g.subjects(RDF.type, OWL.Class))),
        "object_properties": len(list(g.subjects(RDF.type, OWL.ObjectProperty))),
        "datatype_properties": len(list(g.subjects(RDF.type, OWL.DatatypeProperty))),
        "shacl_shapes": len(list(g.subjects(RDF.type, SHACL.NodeShape))),
        "feature_templates": len(list(g.subjects(RDF.type, CORE.FeatureTemplate))),
        "capabilities": len(list(g.subjects(RDF.type, CORE.Capability))),
    }

    stats["total_properties"] = stats["object_properties"] + stats["datatype_properties"]

    return stats


# Namespace URIs for convenience
NAMESPACE_CORE = "http://kgcl.dev/ontology/core#"
NAMESPACE_SHAPES = "http://kgcl.dev/ontology/shapes#"
NAMESPACE_FEATURES = "http://kgcl.dev/ontology/features#"
NAMESPACE_CAPABILITIES = "http://kgcl.dev/ontology/capabilities#"
NAMESPACE_EXAMPLES = "http://kgcl.dev/ontology/examples#"
