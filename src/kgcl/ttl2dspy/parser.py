"""Ontology parser for TTL/RDF files with SHACL shape extraction."""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SH, XSD

logger = logging.getLogger(__name__)

# Common namespaces
KGCL = Namespace("http://kgcl.io/ontology/")
DSPY = Namespace("http://dspy.ai/ontology/")
UNRDF = Namespace("http://unrdf.org/ontology/")

DESCRIPTION_PREDICATES: tuple[URIRef, ...] = (
    RDFS.comment,
    SH.description,
    RDFS.label,
    KGCL.description,
    DSPY.description,
    UNRDF.description,
)


@dataclass
class PropertyShape:
    """Represents a SHACL property shape (input/output field)."""

    path: URIRef | None = None
    name: str = ""
    datatype: URIRef | None = None
    node_kind: URIRef | None = None
    min_count: int = 0
    max_count: int | None = None
    description: str | None = None
    field_role: str | None = None
    default_value: str | None = None
    pattern: str | None = None
    in_values: list[str] = field(default_factory=list)
    is_required: bool | None = None

    def __post_init__(self) -> None:
        """Normalize derived field metadata."""
        if not self.name and self.path is not None:
            self.name = str(self.path).split("/")[-1].split("#")[-1]

        if self.is_required is None:
            self.is_required = self.min_count > 0
        else:
            self.min_count = 1 if self.is_required else 0

    @property
    def is_list(self) -> bool:
        """Check if this property is a list.

        A property is considered a list if:
        - max_count is None (unlimited cardinality), OR
        - max_count is explicitly > 1 (multiple values allowed)
        """
        return self.max_count is None or self.max_count > 1

    def get_python_type(self) -> str:
        """Map SHACL datatype to Python type hint."""
        if self.datatype:
            datatype_map = {
                str(XSD.string): "str",
                str(XSD.integer): "int",
                str(XSD.int): "int",
                str(XSD.float): "float",
                str(XSD.double): "float",
                str(XSD.boolean): "bool",
                str(XSD.dateTime): "str",  # ISO format string
                str(XSD.date): "str",
                str(XSD.time): "str",
            }
            base_type = datatype_map.get(str(self.datatype), "str")
        else:
            base_type = "str"  # Default to string

        # Handle lists
        if self.is_list:
            base_type = f"List[{base_type}]"

        # Handle optional
        if not self.is_required:
            base_type = f"Optional[{base_type}]"

        return base_type


@dataclass
class SHACLShape:
    """Represents a SHACL node shape (feature template)."""

    uri: URIRef
    name: str | None = None
    target_class: URIRef | None = None
    description: str | None = None
    properties: list[PropertyShape] = field(default_factory=list)
    closed: bool = False

    # Categorization
    input_properties: list[PropertyShape] = field(default_factory=list)
    output_properties: list[PropertyShape] = field(default_factory=list)
    signature_name: str | None = None

    def __post_init__(self) -> None:
        """Ensure signature name is populated."""
        local_name = str(self.uri).split("/")[-1].split("#")[-1]
        if not self.name:
            self.name = local_name
        if not self.signature_name:
            local_name = str(self.uri).split("/")[-1].split("#")[-1]
            local_name = local_name.removesuffix("Shape")
            self.signature_name = f"{local_name}Signature"

    def categorize_properties(self):
        """Categorize properties into inputs and outputs based on SHACL annotations."""
        for prop in self.properties:
            role = (prop.field_role or "").lower()
            if role == "input":
                self.input_properties.append(prop)
                continue
            if role == "output":
                self.output_properties.append(prop)
                continue
            # Check for explicit input/output markers
            # Heuristic: properties with sh:defaultValue are likely inputs
            # Properties without default and with descriptions are likely outputs
            if prop.default_value or prop.min_count > 0:
                self.input_properties.append(prop)
            else:
                self.output_properties.append(prop)

        # If no categorization, treat first properties as inputs, last as output
        if not self.input_properties and not self.output_properties:
            if len(self.properties) > 1:
                self.input_properties = self.properties[:-1]
                self.output_properties = [self.properties[-1]]
            elif len(self.properties) == 1:
                self.output_properties = self.properties


class OntologyParser:
    """Parse TTL/RDF files and extract SHACL shapes."""

    def __init__(self, cache_enabled: bool = True):
        """Initialize parser.

        Args:
            cache_enabled: Enable in-memory caching of parsed graphs
        """
        self.cache_enabled = cache_enabled
        self._graph_cache: dict[str, Graph] = {}
        self._shape_cache: dict[str, list[SHACLShape]] = {}

    def parse_file(self, ttl_path: str | Path) -> Graph:
        """Load and parse a TTL/RDF file.

        Args:
            ttl_path: Path to TTL file

        Returns
        -------
            RDFLib Graph object
        """
        ttl_path = Path(ttl_path)
        if not ttl_path.exists():
            raise FileNotFoundError(f"TTL file not found: {ttl_path}")

        # Check cache
        cache_key = self._get_cache_key(ttl_path)
        if self.cache_enabled and cache_key in self._graph_cache:
            logger.debug(f"Using cached graph for {ttl_path}")
            return self._graph_cache[cache_key]

        logger.info(f"Parsing TTL file: {ttl_path}")
        graph = Graph()

        # Parse with format detection
        try:
            graph.parse(str(ttl_path), format="turtle")
        except Exception as e:
            # Try other formats
            logger.warning(f"Failed to parse as Turtle, trying RDF/XML: {e}")
            try:
                graph.parse(str(ttl_path), format="xml")
            except Exception as e2:
                logger.error(f"Failed to parse TTL file: {e2}")
                raise

        # Cache the graph
        if self.cache_enabled:
            self._graph_cache[cache_key] = graph

        logger.info(f"Loaded {len(graph)} triples from {ttl_path}")
        return graph

    def extract_shapes(self, graph: Graph) -> list[SHACLShape]:
        """Extract all SHACL NodeShapes from a graph.

        Args:
            graph: RDFLib Graph containing SHACL shapes

        Returns
        -------
            List of SHACLShape objects
        """
        # Check cache
        graph_hash = self._hash_graph(graph)
        if self.cache_enabled and graph_hash in self._shape_cache:
            logger.debug(f"Using cached shapes for graph {graph_hash[:8]}")
            return self._shape_cache[graph_hash]

        shapes = []

        # Find all NodeShapes
        for shape_uri in graph.subjects(RDF.type, SH.NodeShape):
            shape = self._parse_node_shape(graph, shape_uri)
            if shape:
                shapes.append(shape)

        logger.info(f"Extracted {len(shapes)} SHACL shapes")

        # Cache the shapes
        if self.cache_enabled:
            self._shape_cache[graph_hash] = shapes

        return shapes

    def _parse_node_shape(self, graph: Graph, shape_uri: URIRef) -> SHACLShape | None:
        """Parse a single SHACL NodeShape.

        Args:
            graph: RDFLib Graph
            shape_uri: URI of the NodeShape

        Returns
        -------
            SHACLShape object or None if invalid
        """
        # Extract basic info
        name = str(shape_uri).split("/")[-1].split("#")[-1]
        description = self._get_description(graph, shape_uri) or self._humanize_identifier(name)
        target_class = graph.value(shape_uri, SH.targetClass)
        closed = self._get_boolean(graph, shape_uri, SH.closed)

        # Extract property shapes
        properties = []
        for prop_uri in graph.objects(shape_uri, SH.property):
            prop = self._parse_property_shape(graph, prop_uri)
            if prop:
                properties.append(prop)

        if not properties:
            logger.warning(f"Shape {name} has no properties, skipping")
            return None

        shape = SHACLShape(
            uri=shape_uri,
            name=name,
            target_class=target_class,
            description=description,
            properties=properties,
            closed=closed,
        )

        # Categorize properties
        shape.categorize_properties()

        return shape

    def _parse_property_shape(self, graph: Graph, prop_uri: URIRef) -> PropertyShape | None:
        """Parse a SHACL PropertyShape.

        Args:
            graph: RDFLib Graph
            prop_uri: URI of the PropertyShape

        Returns
        -------
            PropertyShape object or None if invalid
        """
        # Get the path
        path = graph.value(prop_uri, SH.path)
        if not path:
            logger.warning(f"PropertyShape {prop_uri} has no sh:path, skipping")
            return None

        # Extract property metadata
        name = str(path).split("/")[-1].split("#")[-1]
        datatype = graph.value(prop_uri, SH.datatype)
        node_kind = graph.value(prop_uri, SH.nodeKind)
        min_count = self._get_integer(graph, prop_uri, SH.minCount, default=0)
        max_count = self._get_integer(graph, prop_uri, SH.maxCount)
        description = self._get_description(graph, prop_uri) or self._humanize_identifier(name)
        field_role = self._get_literal(graph, prop_uri, UNRDF.fieldType)
        default_value = self._get_literal(graph, prop_uri, SH.defaultValue)
        pattern = self._get_literal(graph, prop_uri, SH.pattern)

        # Get sh:in values
        in_values = []
        in_list = graph.value(prop_uri, SH["in"])
        if in_list:
            in_values = [str(item) for item in graph.items(in_list)]

        return PropertyShape(
            path=path,
            name=name,
            datatype=datatype,
            node_kind=node_kind,
            min_count=min_count,
            max_count=max_count,
            description=description,
            field_role=field_role,
            default_value=default_value,
            pattern=pattern,
            in_values=in_values,
        )

    def _get_literal(self, graph: Graph, subject: URIRef, predicate: URIRef) -> str | None:
        """Get a literal value from the graph."""
        value = graph.value(subject, predicate)
        return str(value) if value else None

    def _get_description(self, graph: Graph, subject: URIRef) -> str | None:
        """Get a human-readable description from standard predicates."""
        for predicate in DESCRIPTION_PREDICATES:
            text = self._get_literal(graph, subject, predicate)
            if text:
                return text
        return None

    def _get_integer(self, graph: Graph, subject: URIRef, predicate: URIRef, default: int | None = None) -> int | None:
        """Get an integer value from the graph."""
        value = graph.value(subject, predicate)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _get_boolean(self, graph: Graph, subject: URIRef, predicate: URIRef) -> bool:
        """Get a boolean value from the graph."""
        value = graph.value(subject, predicate)
        if isinstance(value, Literal):
            return bool(value.value)
        return False

    def _get_cache_key(self, path: Path) -> str:
        """Generate cache key for a file path."""
        # Include file mtime to invalidate on changes
        stat = path.stat()
        return f"{path}:{stat.st_mtime}:{stat.st_size}"

    def _hash_graph(self, graph: Graph) -> str:
        """Generate hash for a graph."""
        # Use sorted triples for consistent hashing
        triples = sorted(str(t) for t in graph)
        return hashlib.sha256("".join(triples).encode()).hexdigest()

    def _humanize_identifier(self, identifier: str) -> str:
        """Convert an RDF local name into a readable description."""
        if not identifier:
            return "Field"

        words = identifier.replace("-", " ").replace("_", " ")
        words = re.sub(r"(?<!^)(?=[A-Z])", " ", words)
        humanized = " ".join(words.split())
        return humanized.capitalize()

    def clear_cache(self):
        """Clear all caches."""
        self._graph_cache.clear()
        self._shape_cache.clear()
        logger.info("Cleared parser caches")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {"graph_cache_size": len(self._graph_cache), "shape_cache_size": len(self._shape_cache)}
