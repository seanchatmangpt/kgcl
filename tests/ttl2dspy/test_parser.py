"""Tests for ontology parser."""

import pytest
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SH, XSD

from kgcl.ttl2dspy.parser import OntologyParser, SHACLShape, PropertyShape


@pytest.fixture
def sample_graph():
    """Create a sample SHACL graph."""
    g = Graph()
    EX = Namespace("http://example.org/")

    # Define a NodeShape
    shape_uri = EX.PersonShape
    g.add((shape_uri, RDF.type, SH.NodeShape))
    g.add((shape_uri, SH.targetClass, EX.Person))
    g.add((shape_uri, RDFS.comment, Literal("A person entity")))

    # Add property shape for name (required string)
    prop1 = EX.PersonShape_name
    g.add((shape_uri, SH.property, prop1))
    g.add((prop1, SH.path, EX.name))
    g.add((prop1, SH.datatype, XSD.string))
    g.add((prop1, SH.minCount, Literal(1)))
    g.add((prop1, RDFS.comment, Literal("Person's name")))

    # Add property shape for age (optional integer)
    prop2 = EX.PersonShape_age
    g.add((shape_uri, SH.property, prop2))
    g.add((prop2, SH.path, EX.age))
    g.add((prop2, SH.datatype, XSD.integer))
    g.add((prop2, RDFS.comment, Literal("Person's age")))

    # Add property shape for description (output)
    prop3 = EX.PersonShape_description
    g.add((shape_uri, SH.property, prop3))
    g.add((prop3, SH.path, EX.description))
    g.add((prop3, SH.datatype, XSD.string))
    g.add((prop3, RDFS.comment, Literal("Generated description")))

    return g


class TestPropertyShape:
    """Tests for PropertyShape class."""

    def test_is_required(self):
        """Test required property detection."""
        prop = PropertyShape(
            path=URIRef("http://example.org/name"),
            name="name",
            min_count=1,
        )
        assert prop.is_required is True

        prop2 = PropertyShape(
            path=URIRef("http://example.org/age"),
            name="age",
            min_count=0,
        )
        assert prop2.is_required is False

    def test_is_list(self):
        """Test list property detection."""
        prop = PropertyShape(
            path=URIRef("http://example.org/tags"),
            name="tags",
            max_count=None,
        )
        assert prop.is_list is True

        prop2 = PropertyShape(
            path=URIRef("http://example.org/name"),
            name="name",
            max_count=1,
        )
        assert prop2.is_list is False

    def test_get_python_type_string(self):
        """Test Python type generation for strings."""
        prop = PropertyShape(
            path=URIRef("http://example.org/name"),
            name="name",
            datatype=XSD.string,
            min_count=1,
        )
        assert prop.get_python_type() == "str"

    def test_get_python_type_integer(self):
        """Test Python type generation for integers."""
        prop = PropertyShape(
            path=URIRef("http://example.org/age"),
            name="age",
            datatype=XSD.integer,
            min_count=0,
        )
        assert prop.get_python_type() == "Optional[int]"

    def test_get_python_type_list(self):
        """Test Python type generation for lists."""
        prop = PropertyShape(
            path=URIRef("http://example.org/tags"),
            name="tags",
            datatype=XSD.string,
            max_count=None,
        )
        assert prop.get_python_type() == "Optional[List[str]]"

    def test_get_python_type_boolean(self):
        """Test Python type generation for booleans."""
        prop = PropertyShape(
            path=URIRef("http://example.org/active"),
            name="active",
            datatype=XSD.boolean,
            min_count=1,
        )
        assert prop.get_python_type() == "bool"


class TestSHACLShape:
    """Tests for SHACLShape class."""

    def test_signature_name(self):
        """Test signature name generation."""
        shape = SHACLShape(
            uri=URIRef("http://example.org/PersonShape"),
            name="PersonShape",
        )
        assert shape.signature_name == "PersonSignature"

        shape2 = SHACLShape(
            uri=URIRef("http://example.org/TextAnalysis"),
            name="TextAnalysis",
        )
        assert shape2.signature_name == "TextAnalysisSignature"

    def test_categorize_properties(self):
        """Test property categorization."""
        shape = SHACLShape(
            uri=URIRef("http://example.org/PersonShape"),
            name="PersonShape",
            properties=[
                PropertyShape(
                    path=URIRef("http://example.org/name"),
                    name="name",
                    min_count=1,
                ),
                PropertyShape(
                    path=URIRef("http://example.org/age"),
                    name="age",
                    default_value="0",
                ),
                PropertyShape(
                    path=URIRef("http://example.org/description"),
                    name="description",
                ),
            ],
        )

        shape.categorize_properties()

        assert len(shape.input_properties) == 2
        assert len(shape.output_properties) == 1
        assert shape.output_properties[0].name == "description"


class TestOntologyParser:
    """Tests for OntologyParser class."""

    def test_parse_node_shape(self, sample_graph):
        """Test parsing of NodeShape."""
        parser = OntologyParser(cache_enabled=False)
        shapes = parser.extract_shapes(sample_graph)

        assert len(shapes) == 1
        shape = shapes[0]

        assert shape.name == "PersonShape"
        assert len(shape.properties) == 3
        assert shape.description == "A person entity"

    def test_parse_property_shapes(self, sample_graph):
        """Test parsing of PropertyShapes."""
        parser = OntologyParser(cache_enabled=False)
        shapes = parser.extract_shapes(sample_graph)

        shape = shapes[0]

        # Find name property
        name_prop = next((p for p in shape.properties if p.name == "name"), None)
        assert name_prop is not None
        assert name_prop.is_required is True
        assert name_prop.datatype == XSD.string

        # Find age property
        age_prop = next((p for p in shape.properties if p.name == "age"), None)
        assert age_prop is not None
        assert age_prop.is_required is False
        assert age_prop.datatype == XSD.integer

    def test_caching(self, sample_graph, tmp_path):
        """Test graph caching."""
        # Create a temp TTL file
        ttl_file = tmp_path / "test.ttl"
        sample_graph.serialize(str(ttl_file), format="turtle")

        parser = OntologyParser(cache_enabled=True)

        # First parse
        graph1 = parser.parse_file(ttl_file)
        assert len(graph1) == len(sample_graph)

        # Second parse (should use cache)
        graph2 = parser.parse_file(ttl_file)
        assert graph1 is graph2  # Same object from cache

        stats = parser.get_cache_stats()
        assert stats["graph_cache_size"] == 1

    def test_clear_cache(self):
        """Test cache clearing."""
        parser = OntologyParser(cache_enabled=True)

        # Add some data to cache
        parser._graph_cache["test"] = Graph()
        parser._shape_cache["test"] = []

        assert len(parser._graph_cache) == 1
        assert len(parser._shape_cache) == 1

        parser.clear_cache()

        assert len(parser._graph_cache) == 0
        assert len(parser._shape_cache) == 0

    def test_invalid_shape(self):
        """Test handling of invalid shapes."""
        g = Graph()
        EX = Namespace("http://example.org/")

        # Shape without properties
        shape_uri = EX.EmptyShape
        g.add((shape_uri, RDF.type, SH.NodeShape))

        parser = OntologyParser(cache_enabled=False)
        shapes = parser.extract_shapes(g)

        assert len(shapes) == 0  # Should skip invalid shape
