"""Tests for YAWL ontology splitting script.

This module tests the split_yawl_ontology.py script to ensure it correctly
splits the monolithic ontology file into modular structure.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from rdflib import Graph
from scripts.split_yawl_ontology import OntologySplitError, OntologySplitter


@pytest.fixture
def sample_ontology_content() -> str:
    """Create a minimal sample ontology for testing.

    Returns
    -------
    str
        Sample ontology content with schema, packages, and classes
    """
    return """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# YAWL Ontology Schema
yawl:Package a owl:Class ;
    rdfs:label "Java Package" .

yawl:Class a owl:Class ;
    rdfs:label "Java Class" .

yawl:Method a owl:Class ;
    rdfs:label "Java Method" .

yawl:hasMethod a owl:ObjectProperty ;
    rdfs:domain yawl:Class ;
    rdfs:range yawl:Method .


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
    .


# Method: TestClass.testMethod
yawl:TestClass_testMethod_1 a yawl:Method ;
    rdfs:label "testMethod" ;
    yawl:returnType "void" ;
    yawl:signature "void testMethod()" ;
    yawl:modifiers "public" ;
    .


# Class: org.yawlfoundation.yawl.test.AnotherClass
yawl:AnotherClass a yawl:Class ;
    rdfs:label "AnotherClass" ;
    yawl:inPackage yawl:org_yawlfoundation_yawl_test ;
    yawl:filePath "test/AnotherClass.java"^^xsd:string ;
    yawl:modifiers "public" ;
    .


# Package: org.yawlfoundation.yawl.other
yawl:org_yawlfoundation_yawl_other a yawl:Package ;
    rdfs:label "org.yawlfoundation.yawl.other" .


# Class: org.yawlfoundation.yawl.other.OtherClass
yawl:OtherClass a yawl:Class ;
    rdfs:label "OtherClass" ;
    yawl:inPackage yawl:org_yawlfoundation_yawl_other ;
    yawl:filePath "test/OtherClass.java"^^xsd:string ;
    yawl:modifiers "public" ;
    .
"""


@pytest.fixture
def sample_ontology_file(sample_ontology_content: str, tmp_path: Path) -> Path:
    """Create a temporary sample ontology file.

    Parameters
    ----------
    sample_ontology_content : str
        Content to write to the file
    tmp_path : Path
        Temporary directory path

    Returns
    -------
    Path
        Path to the created file
    """
    ontology_file = tmp_path / "sample_ontology.ttl"
    ontology_file.write_text(sample_ontology_content, encoding="utf-8")
    return ontology_file


def test_extract_schema(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test schema extraction from ontology file.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    splitter = OntologySplitter(sample_ontology_file, tmp_path / "output")
    schema_lines, data_start = splitter._extract_schema(
        sample_ontology_file.read_text(encoding="utf-8").splitlines(keepends=True)
    )

    # Schema should end before first Package marker
    schema_text = "".join(schema_lines)
    assert "yawl:Package a owl:Class" in schema_text
    assert "yawl:Class a owl:Class" in schema_text
    assert "yawl:Method a owl:Class" in schema_text
    assert "# Package:" not in schema_text
    assert data_start > 0


def test_parse_class_markers(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test class marker detection and parsing.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    splitter = OntologySplitter(sample_ontology_file, tmp_path / "output")
    lines = sample_ontology_file.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find data start
    _, data_start = splitter._extract_schema(lines)

    # Parse classes
    classes = splitter._parse_class_blocks(lines, data_start)

    # Should find 3 classes
    assert len(classes) == 3
    assert "org.yawlfoundation.yawl.test.TestClass" in classes
    assert "org.yawlfoundation.yawl.test.AnotherClass" in classes
    assert "org.yawlfoundation.yawl.other.OtherClass" in classes

    # TestClass should have method definition
    test_class_content = "".join(classes["org.yawlfoundation.yawl.test.TestClass"])
    assert "yawl:TestClass a yawl:Class" in test_class_content
    assert "yawl:TestClass_testMethod_1" in test_class_content


def test_build_directory_structure(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test directory structure creation for class files.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(sample_ontology_file, output_dir)

    # Run split
    stats = splitter.split(dry_run=False)

    # Verify directory structure
    assert (output_dir / "org" / "yawlfoundation" / "yawl" / "test").exists()
    assert (output_dir / "org" / "yawlfoundation" / "yawl" / "other").exists()

    # Verify class files exist
    assert (output_dir / "org" / "yawlfoundation" / "yawl" / "test" / "TestClass.ttl").exists()
    assert (output_dir / "org" / "yawlfoundation" / "yawl" / "test" / "AnotherClass.ttl").exists()
    assert (output_dir / "org" / "yawlfoundation" / "yawl" / "other" / "OtherClass.ttl").exists()


def test_write_class_file(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test individual class file content and format.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(sample_ontology_file, output_dir)

    # Run split
    splitter.split(dry_run=False)

    # Read a class file
    test_class_file = output_dir / "org" / "yawlfoundation" / "yawl" / "test" / "TestClass.ttl"
    content = test_class_file.read_text(encoding="utf-8")

    # Verify prefixes are present
    assert "@prefix rdf:" in content
    assert "@prefix rdfs:" in content
    assert "@prefix yawl:" in content

    # Verify class definition
    assert "yawl:TestClass a yawl:Class" in content
    assert "# Class: org.yawlfoundation.yawl.test.TestClass" in content

    # Verify method is included
    assert "yawl:TestClass_testMethod_1" in content


def test_full_split(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test end-to-end splitting with small sample.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(sample_ontology_file, output_dir)

    # Run split
    stats = splitter.split(dry_run=False)

    # Verify statistics
    assert stats["classes"] == 3
    assert stats["packages"] == 2
    assert stats["schema_lines"] > 0

    # Verify schema file exists
    schema_file = output_dir / "yawl-java-schema.ttl"
    assert schema_file.exists()

    # Verify all class files are valid Turtle
    for class_file in output_dir.rglob("*.ttl"):
        if class_file.name == "yawl-java-schema.ttl":
            continue
        try:
            g = Graph()
            g.parse(str(class_file), format="turtle")
            assert len(g) > 0, f"Empty graph in {class_file}"
        except Exception as e:
            pytest.fail(f"Invalid Turtle syntax in {class_file}: {e}")


def test_preserve_all_triples(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test that no data is lost during splitting (triple count).

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    # Load original file
    original_graph = Graph()
    original_graph.parse(str(sample_ontology_file), format="turtle")
    original_triple_count = len(original_graph)

    # Split
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(sample_ontology_file, output_dir)
    splitter.split(dry_run=False)

    # Load all split files
    combined_graph = Graph()
    for ttl_file in output_dir.rglob("*.ttl"):
        combined_graph.parse(str(ttl_file), format="turtle")

    # Verify triple count matches
    assert len(combined_graph) == original_triple_count, (
        f"Triple count mismatch: original={original_triple_count}, split={len(combined_graph)}"
    )


def test_dry_run_mode(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test dry run mode doesn't write files.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(sample_ontology_file, output_dir)

    # Run in dry-run mode
    stats = splitter.split(dry_run=True)

    # Verify no files were created
    assert not output_dir.exists() or not any(output_dir.iterdir())


def test_invalid_class_name_format(tmp_path: Path) -> None:
    """Test error handling for invalid class name format.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory for output
    """
    # Create file with invalid class name (no package)
    invalid_file = tmp_path / "invalid.ttl"
    invalid_file.write_text(
        """@prefix yawl: <http://yawlfoundation.org/ontology/> .

# Class: InvalidClass
yawl:InvalidClass a yawl:Class .
""",
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    splitter = OntologySplitter(invalid_file, output_dir)

    # Should raise error when trying to write class file
    with pytest.raises(OntologySplitError, match="Invalid class name format"):
        splitter.split(dry_run=False)


def test_missing_input_file(tmp_path: Path) -> None:
    """Test error handling for missing input file.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory for output
    """
    missing_file = tmp_path / "nonexistent.ttl"
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(missing_file, output_dir)

    with pytest.raises(OntologySplitError, match="not found"):
        splitter.split(dry_run=False)


def test_extract_packages(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test package extraction from ontology file.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    splitter = OntologySplitter(sample_ontology_file, tmp_path / "output")
    lines = sample_ontology_file.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find data start
    _, data_start = splitter._extract_schema(lines)

    # Extract packages
    packages = splitter._extract_packages(lines, data_start)

    # Should find 2 packages
    assert len(packages) == 2
    assert "org.yawlfoundation.yawl.test" in packages
    assert "org.yawlfoundation.yawl.other" in packages


def test_validate_output(sample_ontology_file: Path, tmp_path: Path) -> None:
    """Test validation of split output.

    Parameters
    ----------
    sample_ontology_file : Path
        Path to sample ontology file
    tmp_path : Path
        Temporary directory for output
    """
    output_dir = tmp_path / "output"
    splitter = OntologySplitter(sample_ontology_file, output_dir)

    # Run split
    splitter.split(dry_run=False)

    # Validate output
    results = splitter.validate_output()

    # Verify validation results
    assert results["schema_file_exists"] is True
    assert results["class_files_count"] == 3
    assert results["valid_turtle_files"] == 4  # 1 schema + 3 classes
    assert results["invalid_turtle_files"] == 0
    assert results["total_triples"] > 0


def test_validate_output_missing_directory(tmp_path: Path) -> None:
    """Test validation error when output directory doesn't exist.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory for output
    """
    output_dir = tmp_path / "nonexistent"
    splitter = OntologySplitter(tmp_path / "input.ttl", output_dir)

    with pytest.raises(OntologySplitError, match="not found"):
        splitter.validate_output()
