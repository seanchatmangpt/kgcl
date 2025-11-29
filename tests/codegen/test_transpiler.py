"""Tests for kgcl.codegen.transpiler module.

Chicago School TDD tests verifying transpilation behavior with real RDF graphs.
"""

import tempfile
from pathlib import Path

import pytest
from rdflib import Graph, Namespace
from rdflib.namespace import RDFS, SH, XSD

from kgcl.codegen.transpiler import UltraOptimizedTTL2DSPyTranspiler

EX = Namespace("http://example.org/")


@pytest.fixture
def simple_ontology_file() -> Path:
    """Create a simple ontology file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
        f.write(
            """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:nameShape .

ex:nameShape
    sh:path ex:name ;
    sh:datatype xsd:string ;
    rdfs:comment "Person's name" .
"""
        )
        return Path(f.name)


def test_transpiler_initialization() -> None:
    """Test transpiler initializes with correct defaults."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler(cache_size=50, enable_parallel=False)

    assert transpiler.max_workers == 4
    assert not transpiler.enable_parallel
    assert transpiler.metrics.signatures_generated == 0


def test_parse_ontology_returns_graph_and_index(simple_ontology_file: Path) -> None:
    """Test parse_ontology returns graph, index, and URI."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    graph, index, uri = transpiler.parse_ontology(simple_ontology_file)

    assert graph is not None
    assert index is not None
    assert len(graph) > 0


def test_parse_ontology_caches_result(simple_ontology_file: Path) -> None:
    """Test parse_ontology caches graphs for repeated calls."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    graph1, _, _ = transpiler.parse_ontology(simple_ontology_file)
    graph2, _, _ = transpiler.parse_ontology(simple_ontology_file)

    assert transpiler.metrics.cache_hits >= 1


def test_ultra_build_signatures_empty_file_list() -> None:
    """Test ultra_build_signatures handles empty file list."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    signatures = transpiler.ultra_build_signatures([])

    assert signatures == {}


def test_ultra_build_signatures_generates_code(simple_ontology_file: Path) -> None:
    """Test ultra_build_signatures generates signature code."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    signatures = transpiler.ultra_build_signatures([simple_ontology_file])

    assert len(signatures) > 0
    assert any("Signature" in name for name in signatures.keys())


def test_ultra_build_signatures_updates_metrics(simple_ontology_file: Path) -> None:
    """Test ultra_build_signatures updates performance metrics."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    transpiler.ultra_build_signatures([simple_ontology_file])

    assert transpiler.metrics.processing_time > 0
    assert transpiler.metrics.signatures_generated > 0


def test_generate_ultra_module_with_no_signatures() -> None:
    """Test generate_ultra_module handles empty signatures."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    module = transpiler.generate_ultra_module({})

    assert "import dspy" in module
    assert "SIGNATURES = {" in module


def test_generate_ultra_module_includes_signatures() -> None:
    """Test generate_ultra_module includes all signatures."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    signatures = {"TestSignature": "class TestSignature(dspy.Signature): pass"}
    module = transpiler.generate_ultra_module(signatures)

    assert "class TestSignature(dspy.Signature): pass" in module
    assert "TestSignature" in module


def test_generate_ultra_module_includes_performance_metrics() -> None:
    """Test generated module includes performance metrics."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()
    transpiler.metrics.processing_time = 1.5

    module = transpiler.generate_ultra_module({})

    assert "Performance Metrics" in module or "performance metrics" in module.lower()
    assert "processing" in module.lower()


def test_map_xsd_to_dtype_string() -> None:
    """Test XSD string maps to dtype=str."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    result = transpiler._map_xsd_to_dtype(str(XSD.string))

    assert result == "dtype=str"


def test_map_xsd_to_dtype_integer() -> None:
    """Test XSD integer maps to dtype=int."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    result = transpiler._map_xsd_to_dtype(str(XSD.integer))

    assert result == "dtype=int"


def test_map_xsd_to_dtype_float() -> None:
    """Test XSD float maps to dtype=float."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    result = transpiler._map_xsd_to_dtype(str(XSD.float))

    assert result == "dtype=float"


def test_map_xsd_to_dtype_boolean() -> None:
    """Test XSD boolean maps to dtype=bool."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    result = transpiler._map_xsd_to_dtype(str(XSD.boolean))

    assert result == "dtype=bool"


def test_map_xsd_to_dtype_unknown() -> None:
    """Test unknown XSD type defaults to dtype=str."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    result = transpiler._map_xsd_to_dtype("http://unknown.org/UnknownType")

    assert result == "dtype=str"


def test_check_field_collision_avoids_reserved_names() -> None:
    """Test field collision checking avoids reserved names."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    result = transpiler._check_field_collision("metadata")

    assert result == "custom_metadata"


def test_check_field_collision_handles_duplicates() -> None:
    """Test field collision checking handles duplicate names."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    first = transpiler._check_field_collision("name")
    second = transpiler._check_field_collision("name")

    assert first == "name"
    assert second == "name_1"


def test_parallel_processing_with_multiple_files() -> None:
    """Test parallel processing handles multiple files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = []
        for i in range(3):
            file = Path(tmpdir) / f"ontology{i}.ttl"
            file.write_text(
                f"""
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

ex:Class{i}Shape sh:targetClass ex:Class{i} .
"""
            )
            files.append(file)

        transpiler = UltraOptimizedTTL2DSPyTranspiler(enable_parallel=True, max_workers=2)

        signatures = transpiler.ultra_build_signatures(files)

        assert transpiler.metrics.parallel_workers == 2


def test_extract_ontology_uri_with_ontology() -> None:
    """Test extracting ontology URI from graph with ontology declaration."""
    from rdflib.namespace import OWL, RDF

    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    graph = Graph()
    graph.add((EX.myOntology, RDF.type, OWL.Ontology))

    uri = transpiler._extract_ontology_uri(graph)

    assert uri == str(EX.myOntology)


def test_extract_ontology_uri_without_ontology() -> None:
    """Test extracting ontology URI returns empty string when no ontology."""
    transpiler = UltraOptimizedTTL2DSPyTranspiler()

    graph = Graph()

    uri = transpiler._extract_ontology_uri(graph)

    assert uri == ""
