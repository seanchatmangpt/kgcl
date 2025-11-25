"""Tests for SHACL validation system."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SH

from kgcl.unrdf_engine.validation import ShaclValidator, ValidationResult


class TestValidationResult:
    """Test ValidationResult class."""

    def test_creation(self) -> None:
        """Test creating validation result."""
        result = ValidationResult(conforms=True)

        assert result.conforms
        assert len(result.violations) == 0

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = ValidationResult(
            conforms=False, violations=[{"message": "test error"}], report_text="Validation failed"
        )

        result_dict = result.to_dict()

        assert not result_dict["conforms"]
        assert len(result_dict["violations"]) == 1
        assert result_dict["report_text"] == "Validation failed"


class TestShaclValidator:
    """Test ShaclValidator class."""

    def test_initialization(self) -> None:
        """Test validator initialization."""
        validator = ShaclValidator()

        assert not validator.has_shapes()
        assert validator.get_shape_count() == 0

    def test_load_shapes_from_string(self) -> None:
        """Test loading shapes from string."""
        validator = ShaclValidator()

        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
                sh:datatype xsd:string ;
            ] .
        """

        validator.load_shapes_from_string(shapes_ttl)

        assert validator.has_shapes()
        assert validator.get_shape_count() > 0

    def test_load_shapes_from_file(self) -> None:
        """Test loading shapes from file."""
        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .

        ex:PersonShape a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
            ] .
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(shapes_ttl)
            file_path = Path(f.name)

        try:
            validator = ShaclValidator()
            validator.load_shapes(file_path)

            assert validator.has_shapes()
            assert validator.get_shape_count() > 0

        finally:
            file_path.unlink()

    def test_load_shapes_file_not_found(self) -> None:
        """Test loading shapes from nonexistent file."""
        validator = ShaclValidator()

        with pytest.raises(FileNotFoundError):
            validator.load_shapes(Path("/nonexistent/file.ttl"))

    def test_validate_without_shapes_fails(self) -> None:
        """Test that validation without shapes fails."""
        validator = ShaclValidator()
        data_graph = Graph()

        with pytest.raises(ValueError, match="No SHACL shapes loaded"):
            validator.validate(data_graph)

    def test_validate_conforming_data(self) -> None:
        """Test validating conforming data."""
        validator = ShaclValidator()

        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
                sh:datatype xsd:string ;
            ] .
        """

        validator.load_shapes_from_string(shapes_ttl)

        # Create conforming data
        EX = Namespace("http://example.org/")
        data_graph = Graph()
        data_graph.bind("ex", EX)

        person = URIRef("http://example.org/person1")
        data_graph.add((person, RDF.type, EX.Person))
        data_graph.add((person, EX.name, Literal("Alice")))

        result = validator.validate(data_graph)

        assert result.conforms
        assert len(result.violations) == 0

    def test_validate_nonconforming_data(self) -> None:
        """Test validating non-conforming data."""
        validator = ShaclValidator()

        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
                sh:datatype xsd:string ;
            ] .
        """

        validator.load_shapes_from_string(shapes_ttl)

        # Create non-conforming data (missing name)
        EX = Namespace("http://example.org/")
        data_graph = Graph()
        data_graph.bind("ex", EX)

        person = URIRef("http://example.org/person1")
        data_graph.add((person, RDF.type, EX.Person))
        # Missing name property

        result = validator.validate(data_graph)

        assert not result.conforms
        assert len(result.violations) > 0

    def test_validate_with_custom_shapes(self) -> None:
        """Test validating with custom shapes."""
        validator = ShaclValidator()

        # Load default shapes
        default_shapes = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .

        ex:DefaultShape a sh:NodeShape ;
            sh:targetClass ex:Default .
        """
        validator.load_shapes_from_string(default_shapes)

        # Create custom shapes
        custom_shapes = Graph()
        EX = Namespace("http://example.org/")
        custom_shapes.bind("ex", EX)
        custom_shapes.bind("sh", SH)

        shape = URIRef("http://example.org/CustomShape")
        custom_shapes.add((shape, RDF.type, SH.NodeShape))
        custom_shapes.add((shape, SH.targetClass, EX.Custom))

        # Create data
        data_graph = Graph()
        data_graph.add((URIRef("http://example.org/item1"), RDF.type, EX.Custom))

        # Validate with custom shapes
        result = validator.validate_with_custom_shapes(data_graph, custom_shapes)

        # Should validate against custom shapes, not default
        assert result is not None

    def test_parse_violations(self) -> None:
        """Test parsing violations from report."""
        validator = ShaclValidator()

        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:age ;
                sh:minInclusive 0 ;
                sh:maxInclusive 150 ;
                sh:datatype xsd:integer ;
            ] .
        """

        validator.load_shapes_from_string(shapes_ttl)

        # Create invalid data
        EX = Namespace("http://example.org/")
        data_graph = Graph()
        data_graph.bind("ex", EX)

        person = URIRef("http://example.org/person1")
        data_graph.add((person, RDF.type, EX.Person))
        data_graph.add((person, EX.age, Literal(200)))  # Exceeds max

        result = validator.validate(data_graph)

        assert not result.conforms
        assert len(result.violations) > 0

        violation = result.violations[0]
        assert "focus_node" in violation
        assert "message" in violation

    def test_validation_with_inference(self) -> None:
        """Test validation with inference enabled."""
        validator = ShaclValidator()

        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:EmployeeShape a sh:NodeShape ;
            sh:targetClass ex:Employee ;
            sh:property [
                sh:path ex:hasManager ;
                sh:minCount 1 ;
            ] .
        """

        validator.load_shapes_from_string(shapes_ttl)

        # Create data that requires inference
        EX = Namespace("http://example.org/")
        data_graph = Graph()
        data_graph.bind("ex", EX)

        person = URIRef("http://example.org/person1")
        data_graph.add((person, RDF.type, EX.Employee))
        data_graph.add((person, EX.hasManager, URIRef("http://example.org/manager1")))

        # Validate with RDFS inference
        result = validator.validate(data_graph, inference="rdfs")

        assert result.conforms

    def test_abort_on_first(self) -> None:
        """Test abort on first violation."""
        validator = ShaclValidator()

        shapes_ttl = """
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:name ;
                sh:minCount 1 ;
            ] ;
            sh:property [
                sh:path ex:age ;
                sh:minCount 1 ;
            ] .
        """

        validator.load_shapes_from_string(shapes_ttl)

        # Create data with multiple violations
        EX = Namespace("http://example.org/")
        data_graph = Graph()
        data_graph.bind("ex", EX)

        person = URIRef("http://example.org/person1")
        data_graph.add((person, RDF.type, EX.Person))
        # Missing both name and age

        # With abort_on_first, should stop after first violation
        result = validator.validate(data_graph, abort_on_first=True)

        assert not result.conforms
        # Should have at least one violation
        assert len(result.violations) >= 1
