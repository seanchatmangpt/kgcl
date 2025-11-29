"""Tests for codebase ontology index.

Tests the index builder and query helper for the codebase ontology.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from rdflib import Graph
from scripts.build_codebase_index import CodebaseIndexBuilder

from kgcl.ontology.codebase_index import CodebaseIndex


@pytest.fixture
def sample_codebase(tmp_path: Path) -> Path:
    """Create a sample codebase structure for testing.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory

    Returns
    -------
    Path
        Path to the sample codebase directory
    """
    codebase_dir = tmp_path / "codebase"
    codebase_dir.mkdir()

    # Create sample class files
    test_package_dir = codebase_dir / "org" / "yawlfoundation" / "yawl" / "test"
    test_package_dir.mkdir(parents=True)

    # Class 1: TestClass
    test_class_file = test_package_dir / "TestClass.ttl"
    test_class_file.write_text(
        """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# Package: org.yawlfoundation.yawl.test
yawl:org_yawlfoundation_yawl_test a yawl:Package ;
    rdfs:label "org.yawlfoundation.yawl.test" .

# Class: org.yawlfoundation.yawl.test.TestClass
yawl:TestClass a yawl:Class ;
    rdfs:label "TestClass" ;
    yawl:inPackage yawl:org_yawlfoundation_yawl_test ;
    yawl:filePath "test/TestClass.java"^^xsd:string ;
    yawl:modifiers "public" ;
    yawl:hasMethod yawl:TestClass_testMethod_1 ;
    yawl:hasField yawl:TestClass_testField ;
    .

# Method: TestClass.testMethod
yawl:TestClass_testMethod_1 a yawl:Method ;
    rdfs:label "testMethod" ;
    yawl:returnType "void" ;
    yawl:signature "void testMethod()" ;
    yawl:modifiers "public" ;
    .

yawl:TestClass_testField a yawl:Field ;
    rdfs:label "testField" .
""",
        encoding="utf-8",
    )

    # Class 2: AnotherClass extends TestClass
    another_class_file = test_package_dir / "AnotherClass.ttl"
    another_class_file.write_text(
        """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# Package: org.yawlfoundation.yawl.test
yawl:org_yawlfoundation_yawl_test a yawl:Package ;
    rdfs:label "org.yawlfoundation.yawl.test" .

# Class: org.yawlfoundation.yawl.test.AnotherClass
yawl:AnotherClass a yawl:Class ;
    rdfs:label "AnotherClass" ;
    yawl:inPackage yawl:org_yawlfoundation_yawl_test ;
    yawl:filePath "test/AnotherClass.java"^^xsd:string ;
    yawl:extends yawl:TestClass ;
    yawl:modifiers "public" ;
    yawl:hasMethod yawl:AnotherClass_toString_1 ;
    .
""",
        encoding="utf-8",
    )

    return codebase_dir


def test_build_index(sample_codebase: Path, tmp_path: Path) -> None:
    """Test index building from codebase files.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)

    builder.build_index()

    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Verify index is valid Turtle
    graph = Graph()
    graph.parse(str(output_file), format="turtle")
    assert len(graph) > 0


def test_find_class(sample_codebase: Path, tmp_path: Path) -> None:
    """Test finding a class by name.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    class_info = index.find_class("TestClass")

    assert class_info is not None
    assert class_info["class_name"] == "TestClass"
    assert "org.yawlfoundation.yawl.test" in class_info["package_name"]


def test_find_classes_in_package(sample_codebase: Path, tmp_path: Path) -> None:
    """Test finding all classes in a package.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    classes = index.find_classes_in_package("org.yawlfoundation.yawl.test")

    assert len(classes) == 2
    assert any("TestClass" in c for c in classes)
    assert any("AnotherClass" in c for c in classes)


def test_get_inheritance_hierarchy(sample_codebase: Path, tmp_path: Path) -> None:
    """Test getting inheritance hierarchy.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    hierarchy = index.get_inheritance_hierarchy("AnotherClass")

    assert hierarchy["extends"] == "TestClass"


def test_find_classes_with_method(sample_codebase: Path, tmp_path: Path) -> None:
    """Test finding classes with a specific method.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    classes = index.find_classes_with_method("toString")

    assert len(classes) > 0
    assert any("AnotherClass" in c for c in classes)


def test_find_classes_with_field(sample_codebase: Path, tmp_path: Path) -> None:
    """Test finding classes with a specific field.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    classes = index.find_classes_with_field("testField")

    assert len(classes) > 0
    assert any("TestClass" in c for c in classes)


def test_find_references(sample_codebase: Path, tmp_path: Path) -> None:
    """Test finding classes that reference another class.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    refs = index.find_references("TestClass")

    assert len(refs) > 0
    assert any("AnotherClass" in r for r in refs)


def test_search(sample_codebase: Path, tmp_path: Path) -> None:
    """Test full-text search.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    results = index.search("test")

    assert len(results) > 0


def test_query(sample_codebase: Path, tmp_path: Path) -> None:
    """Test custom SPARQL query.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    results = index.query(
        """
        PREFIX index: <http://yawlfoundation.org/ontology/index#>
        SELECT ?className WHERE {
            ?idx index:className ?className .
        } LIMIT 5
        """
    )

    assert len(results) > 0
    assert "className" in results[0]


def test_stats(sample_codebase: Path, tmp_path: Path) -> None:
    """Test index statistics.

    Parameters
    ----------
    sample_codebase : Path
        Sample codebase directory
    tmp_path : Path
        Temporary directory
    """
    output_file = tmp_path / "index.ttl"
    builder = CodebaseIndexBuilder(sample_codebase, output_file)
    builder.build_index()

    index = CodebaseIndex(output_file)
    stats = index.stats()

    assert stats["classes"] > 0
    assert stats["packages"] > 0
    assert stats["triples"] > 0
