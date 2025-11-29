"""Tests for RDF/Turtle ontology generator.

Chicago School TDD - tests assert on real RDF generation and validation.
"""

from pathlib import Path
from textwrap import dedent

import pytest
from rdflib import RDF, Graph, Namespace

from kgcl.yawl_ontology.generator import YawlOntologyGenerator


@pytest.fixture
def sample_java_dir(tmp_path: Path) -> Path:
    """Create sample Java source directory."""
    src_dir = tmp_path / "src" / "org" / "example"
    src_dir.mkdir(parents=True)

    # Create a sample Java file
    java_file = src_dir / "Sample.java"
    content = dedent("""
        package org.example;

        /**
         * Sample class for testing.
         */
        public class Sample {
            private String value;

            /**
             * Get the value.
             * @return the value
             */
            public String getValue() {
                return value;
            }

            /**
             * Set the value.
             * @param newValue the new value
             */
            public void setValue(String newValue) {
                value = newValue;
            }
        }
    """)
    java_file.write_text(content)

    return tmp_path / "src"


def test_generator_creates_valid_turtle(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generator creates syntactically valid Turtle."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    assert output_file.exists()
    # Validation happens internally - if we get here, Turtle is valid


def test_generator_includes_owl_schema(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generated ontology includes OWL schema definitions."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    content = output_file.read_text()
    assert "@prefix owl:" in content
    assert "yawl:Package a owl:Class" in content
    assert "yawl:Class a owl:Class" in content
    assert "yawl:Method a owl:Class" in content


def test_generator_creates_package_triples(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generator creates RDF triples for packages."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    g = Graph()
    g.parse(output_file, format="turtle")

    YAWL = Namespace("http://yawlfoundation.org/ontology/")

    # Check package exists
    packages = list(g.subjects(RDF.type, YAWL.Package))
    assert len(packages) > 0


def test_generator_creates_class_triples(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generator creates RDF triples for classes."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    content = output_file.read_text()
    assert "yawl:Sample a yawl:Class" in content
    assert 'rdfs:label "Sample"' in content


def test_generator_creates_method_triples(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generator creates RDF triples for methods."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    content = output_file.read_text()
    assert "getValue" in content
    assert "setValue" in content
    assert "yawl:returnType" in content
    assert "yawl:signature" in content


def test_generator_links_classes_to_packages(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generator links classes to their packages."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    content = output_file.read_text()
    assert "yawl:inPackage" in content


def test_generator_links_methods_to_classes(sample_java_dir: Path, tmp_path: Path) -> None:
    """Test that generator links methods to their classes."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    content = output_file.read_text()
    assert "yawl:hasMethod" in content


def test_generator_raises_on_nonexistent_directory(tmp_path: Path) -> None:
    """Test that generator raises error for nonexistent source directory."""
    generator = YawlOntologyGenerator()
    nonexistent = tmp_path / "does_not_exist"
    output_file = tmp_path / "ontology.ttl"

    with pytest.raises(ValueError, match="does not exist"):
        generator.generate_from_directory(nonexistent, output_file)


def test_generator_raises_on_file_not_directory(tmp_path: Path) -> None:
    """Test that generator raises error when source path is a file."""
    generator = YawlOntologyGenerator()
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("not a directory")
    output_file = tmp_path / "ontology.ttl"

    with pytest.raises(ValueError, match="not a directory"):
        generator.generate_from_directory(not_a_dir, output_file)


def test_generator_counts_triples(sample_java_dir: Path, tmp_path: Path, capsys) -> None:
    """Test that generator reports triple count."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    captured = capsys.readouterr()
    assert "triples" in captured.out.lower()


def test_generator_reports_file_count(sample_java_dir: Path, tmp_path: Path, capsys) -> None:
    """Test that generator reports number of Java files processed."""
    output_file = tmp_path / "ontology.ttl"
    generator = YawlOntologyGenerator()

    generator.generate_from_directory(sample_java_dir, output_file)

    captured = capsys.readouterr()
    assert "1 Java files" in captured.out or "Found 1 Java" in captured.out


def test_real_yawl_mailsender_ontology() -> None:
    """Integration test - verify real YAWL mailSender ontology is valid."""
    ontology_file = Path("docs/yawl_mailsender_ontology.ttl")

    if not ontology_file.exists():
        pytest.skip("YAWL mailSender ontology not generated yet")

    # Should parse without errors
    g = Graph()
    g.parse(ontology_file, format="turtle")

    # Should have meaningful content
    assert len(g) > 50  # At least 50 triples
