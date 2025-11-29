"""Tests for kgcl.codegen.indexing module.

Chicago School TDD tests verifying SHACL indexing for O(1) lookups.
"""

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import SH, XSD

from kgcl.codegen.indexing import SHACLIndex

EX = Namespace("http://example.org/")


@pytest.fixture
def simple_shacl_graph() -> Graph:
    """Create a simple SHACL graph for testing."""
    graph = Graph()
    graph.bind("ex", EX)
    graph.bind("sh", SH)

    prop_shape = EX.nameShape
    graph.add((prop_shape, SH.path, EX.name))
    graph.add((prop_shape, SH.targetClass, EX.Person))
    graph.add((prop_shape, SH.datatype, XSD.string))

    return graph


def test_index_initialization_with_empty_graph() -> None:
    """Test index initializes correctly with empty graph."""
    graph = Graph()

    index = SHACLIndex(graph)

    assert len(index.target_class_index) == 0
    assert len(index.property_shape_index) == 0
    assert len(index.datatype_index) == 0


def test_index_builds_target_class_index(simple_shacl_graph: Graph) -> None:
    """Test index builds target class to property shape mapping."""
    index = SHACLIndex(simple_shacl_graph)

    person_uri = str(EX.Person)

    assert person_uri in index.target_class_index
    assert str(EX.nameShape) in index.target_class_index[person_uri]


def test_index_builds_datatype_index(simple_shacl_graph: Graph) -> None:
    """Test index builds property shape to datatype mapping."""
    index = SHACLIndex(simple_shacl_graph)

    name_shape_uri = str(EX.nameShape)

    assert name_shape_uri in index.datatype_index
    assert index.datatype_index[name_shape_uri] == str(XSD.string)


def test_get_property_shapes_for_class(simple_shacl_graph: Graph) -> None:
    """Test getting property shapes for a class."""
    index = SHACLIndex(simple_shacl_graph)

    shapes = index.get_property_shapes_for_class(str(EX.Person))

    assert len(shapes) > 0
    assert str(EX.nameShape) in shapes


def test_get_property_shapes_for_nonexistent_class() -> None:
    """Test getting shapes for class that doesn't exist."""
    graph = Graph()
    index = SHACLIndex(graph)

    shapes = index.get_property_shapes_for_class("http://example.org/NonExistent")

    assert shapes == []


def test_get_datatype_for_shape(simple_shacl_graph: Graph) -> None:
    """Test getting datatype for property shape."""
    index = SHACLIndex(simple_shacl_graph)

    datatype = index.get_datatype_for_shape(str(EX.nameShape))

    assert datatype == str(XSD.string)


def test_get_datatype_for_nonexistent_shape() -> None:
    """Test getting datatype for shape that doesn't exist."""
    graph = Graph()
    index = SHACLIndex(graph)

    datatype = index.get_datatype_for_shape("http://example.org/NonExistent")

    assert datatype is None


def test_index_with_node_shapes() -> None:
    """Test index handles node shapes with properties."""
    graph = Graph()

    node_shape = EX.PersonShape
    prop_shape = EX.nameShape

    graph.add((node_shape, SH.targetClass, EX.Person))
    graph.add((node_shape, SH.property, prop_shape))
    graph.add((prop_shape, SH.path, EX.name))

    index = SHACLIndex(graph)

    shapes = index.get_property_shapes_for_class(str(EX.Person))

    assert str(prop_shape) in shapes


def test_index_deduplicates_property_shapes() -> None:
    """Test index removes duplicate property shapes."""
    graph = Graph()

    graph.add((EX.nameShape, SH.path, EX.name))
    graph.add((EX.nameShape, SH.targetClass, EX.Person))

    node_shape = EX.PersonShape
    graph.add((node_shape, SH.targetClass, EX.Person))
    graph.add((node_shape, SH.property, EX.nameShape))

    index = SHACLIndex(graph)

    shapes = index.get_property_shapes_for_class(str(EX.Person))

    assert shapes.count(str(EX.nameShape)) == 1


def test_stats_returns_index_counts(simple_shacl_graph: Graph) -> None:
    """Test stats returns accurate index statistics."""
    index = SHACLIndex(simple_shacl_graph)

    stats = index.stats()

    assert stats["target_classes"] >= 1
    assert stats["datatype_mappings"] >= 1


def test_index_with_multiple_classes() -> None:
    """Test index handles multiple classes."""
    graph = Graph()

    person_shape = EX.personNameShape
    graph.add((person_shape, SH.path, EX.name))
    graph.add((person_shape, SH.targetClass, EX.Person))
    graph.add((person_shape, SH.datatype, XSD.string))

    org_shape = EX.orgNameShape
    graph.add((org_shape, SH.path, EX.name))
    graph.add((org_shape, SH.targetClass, EX.Organization))
    graph.add((org_shape, SH.datatype, XSD.string))

    index = SHACLIndex(graph)

    person_shapes = index.get_property_shapes_for_class(str(EX.Person))
    org_shapes = index.get_property_shapes_for_class(str(EX.Organization))

    assert str(person_shape) in person_shapes
    assert str(org_shape) in org_shapes
    assert str(person_shape) not in org_shapes


def test_index_ignores_shapes_without_path() -> None:
    """Test index ignores property shapes without sh:path."""
    graph = Graph()

    node_shape = EX.PersonShape
    invalid_prop = EX.invalidShape

    graph.add((node_shape, SH.targetClass, EX.Person))
    graph.add((node_shape, SH.property, invalid_prop))

    index = SHACLIndex(graph)

    shapes = index.get_property_shapes_for_class(str(EX.Person))

    assert str(invalid_prop) not in shapes
