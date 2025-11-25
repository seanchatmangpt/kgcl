"""Integration tests for ttl2dspy."""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Final

import pytest
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SH, XSD

from kgcl.ttl2dspy.hooks import TTL2DSpyHook
from kgcl.ttl2dspy.ultra import CacheConfig, UltraOptimizer
from kgcl.ttl2dspy.writer import ModuleWriter

TEXT_ANALYSIS_SHAPE_COUNT: Final[int] = 2
BATCH_FILE_COUNT: Final[int] = 3


@pytest.fixture
def text_analysis_ttl(tmp_path: Path) -> Path:
    """Create a realistic text analysis SHACL ontology."""
    g = Graph()
    kgcl_ns = Namespace("http://kgcl.io/ontology/")

    # Text classification shape definition.
    classify_shape = kgcl_ns.TextClassificationShape
    g.add((classify_shape, RDF.type, SH.NodeShape))
    g.add((classify_shape, SH.targetClass, kgcl_ns.TextClassification))
    g.add((classify_shape, RDFS.comment, Literal("Classify text into predefined categories")))

    # Input text property.
    prop1 = kgcl_ns.TextClassificationShape_text
    g.add((classify_shape, SH.property, prop1))
    g.add((prop1, SH.path, kgcl_ns.text))
    g.add((prop1, SH.datatype, XSD.string))
    g.add((prop1, SH.minCount, Literal(1)))
    g.add((prop1, RDFS.comment, Literal("Input text to classify")))

    # Input categories property.
    prop2 = kgcl_ns.TextClassificationShape_categories
    g.add((classify_shape, SH.property, prop2))
    g.add((prop2, SH.path, kgcl_ns.categories))
    g.add((prop2, SH.datatype, XSD.string))
    g.add((prop2, SH.minCount, Literal(1)))
    g.add((prop2, RDFS.comment, Literal("Possible categories (comma-separated)")))

    # Output category property.
    prop3 = kgcl_ns.TextClassificationShape_category
    g.add((classify_shape, SH.property, prop3))
    g.add((prop3, SH.path, kgcl_ns.category))
    g.add((prop3, SH.datatype, XSD.string))
    g.add((prop3, RDFS.comment, Literal("Predicted category")))

    # Output confidence property.
    prop4 = kgcl_ns.TextClassificationShape_confidence
    g.add((classify_shape, SH.property, prop4))
    g.add((prop4, SH.path, kgcl_ns.confidence))
    g.add((prop4, SH.datatype, XSD.float))
    g.add((prop4, RDFS.comment, Literal("Confidence score (0-1)")))

    # Entity extraction shape definition.
    extract_shape = kgcl_ns.EntityExtractionShape
    g.add((extract_shape, RDF.type, SH.NodeShape))
    g.add((extract_shape, SH.targetClass, kgcl_ns.EntityExtraction))
    g.add((extract_shape, RDFS.comment, Literal("Extract named entities from text")))

    # Input text for extraction.
    prop5 = kgcl_ns.EntityExtractionShape_text
    g.add((extract_shape, SH.property, prop5))
    g.add((prop5, SH.path, kgcl_ns.text))
    g.add((prop5, SH.datatype, XSD.string))
    g.add((prop5, SH.minCount, Literal(1)))
    g.add((prop5, RDFS.comment, Literal("Input text for entity extraction")))

    # Output entities property.
    prop6 = kgcl_ns.EntityExtractionShape_entities
    g.add((extract_shape, SH.property, prop6))
    g.add((prop6, SH.path, kgcl_ns.entities))
    g.add((prop6, SH.datatype, XSD.string))
    g.add((prop6, RDFS.comment, Literal("Extracted entities as JSON")))

    ttl_file = tmp_path / "text_analysis.ttl"
    g.serialize(str(ttl_file), format="turtle")

    return ttl_file


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_parse_and_generate(self, text_analysis_ttl: Path, tmp_path: Path) -> None:
        """Test complete workflow: parse -> generate -> write."""
        optimizer = UltraOptimizer()
        writer = ModuleWriter()

        # Parse
        shapes = optimizer.parse_with_cache(text_analysis_ttl)
        assert len(shapes) == TEXT_ANALYSIS_SHAPE_COUNT

        # Generate
        code = optimizer.generate_with_cache(shapes)
        assert "class TextClassificationSignature(dspy.Signature):" in code
        assert "class EntityExtractionSignature(dspy.Signature):" in code

        # Write
        output_path = tmp_path / "signatures.py"
        result = writer.write_module(
            code=code,
            output_path=output_path,
            shapes_count=len(shapes),
            ttl_source=text_analysis_ttl,
            format_code=False,
        )

        assert result.signatures_count == TEXT_ANALYSIS_SHAPE_COUNT
        assert output_path.exists()

        # Verify the generated file is valid Python
        content = output_path.read_text()
        assert "import dspy" in content
        assert "text: str = dspy.InputField" in content
        assert "category: Optional[str] = dspy.OutputField" in content

    def test_caching_workflow(self, text_analysis_ttl: Path, tmp_path: Path) -> None:
        """Test that caching works across the workflow."""
        config = CacheConfig(
            memory_cache_enabled=True, disk_cache_enabled=True, disk_cache_dir=tmp_path / "cache"
        )

        # First run
        optimizer1 = UltraOptimizer(config)
        shapes1 = optimizer1.parse_with_cache(text_analysis_ttl)
        code1 = optimizer1.generate_with_cache(shapes1)

        # Verify cache misses on first run
        assert optimizer1.stats.memory_misses > 0

        # Second run with same optimizer
        shapes2 = optimizer1.parse_with_cache(text_analysis_ttl)
        code2 = optimizer1.generate_with_cache(shapes2)

        # Verify cache hits
        assert optimizer1.stats.memory_hits > 0
        assert code1 == code2

        # Third run with new optimizer (should use disk cache)
        optimizer2 = UltraOptimizer(config)
        shapes3 = optimizer2.parse_with_cache(text_analysis_ttl)

        assert len(shapes3) == len(shapes1)

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Test processing multiple TTL files."""
        files: list[str | Path] = []

        # Create multiple ontology files
        for i in range(BATCH_FILE_COUNT):
            g = Graph()
            shape_ns = Namespace(f"http://example.org/{i}/")

            shape = shape_ns.TestShape
            g.add((shape, RDF.type, SH.NodeShape))
            g.add((shape, RDFS.comment, Literal(f"Test shape {i}")))

            prop = shape_ns.TestShape_prop
            g.add((shape, SH.property, prop))
            g.add((prop, SH.path, shape_ns.prop))
            g.add((prop, SH.datatype, XSD.string))
            g.add((prop, SH.minCount, Literal(1)))

            ttl_file = tmp_path / f"ontology{i}.ttl"
            g.serialize(str(ttl_file), format="turtle")
            files.append(ttl_file)

        # Parse all files
        optimizer = UltraOptimizer()
        results = optimizer.batch_parse(files)

        assert len(results) == BATCH_FILE_COUNT
        for shapes in results.values():
            assert len(shapes) == 1

    def test_generated_module_is_importable(self, text_analysis_ttl: Path, tmp_path: Path) -> None:
        """Test that generated module can be imported."""
        optimizer = UltraOptimizer()
        writer = ModuleWriter()

        shapes = optimizer.parse_with_cache(text_analysis_ttl)
        code = optimizer.generate_with_cache(shapes)

        output_path = tmp_path / "test_signatures.py"
        writer.write_module(code=code, output_path=output_path, format_code=False)

        # Add to path and import
        sys.path.insert(0, str(tmp_path))

        try:
            # This will fail if the generated code has syntax errors
            spec = importlib.util.spec_from_file_location("test_signatures", output_path)
            assert spec is not None, "Failed to create module spec"
            loader = spec.loader
            assert loader is not None, "Spec loader missing"
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)

            # Verify classes exist
            assert hasattr(module, "TextClassificationSignature")
            assert hasattr(module, "EntityExtractionSignature")

        finally:
            sys.path.pop(0)


class TestHooks:
    """Tests for UNRDF hooks integration."""

    def test_hook_parse_action(self, text_analysis_ttl: Path) -> None:
        """Test hook with parse action."""
        hook = TTL2DSpyHook()

        request = {"action": "parse", "ttl_path": str(text_analysis_ttl)}

        receipt = hook.process_stdin(json.dumps(request))

        assert receipt["success"] is True
        assert receipt["action"] == "parse"
        assert receipt["shapes_count"] == TEXT_ANALYSIS_SHAPE_COUNT
        assert len(receipt["shapes"]) == TEXT_ANALYSIS_SHAPE_COUNT

    def test_hook_validate_action(self, text_analysis_ttl: Path) -> None:
        """Test hook with validate action."""
        hook = TTL2DSpyHook()

        request = {"action": "validate", "ttl_path": str(text_analysis_ttl)}

        receipt = hook.process_stdin(json.dumps(request))

        assert receipt["success"] is True
        assert receipt["action"] == "validate"
        assert receipt["valid"] is True

    def test_hook_list_action(self, text_analysis_ttl: Path) -> None:
        """Test hook with list action."""
        hook = TTL2DSpyHook()

        request = {"action": "list", "ttl_path": str(text_analysis_ttl)}

        receipt = hook.process_stdin(json.dumps(request))

        assert receipt["success"] is True
        assert receipt["action"] == "list"
        assert len(receipt["shapes"]) == TEXT_ANALYSIS_SHAPE_COUNT

        # Verify shape details
        for shape in receipt["shapes"]:
            assert "name" in shape
            assert "inputs" in shape
            assert "outputs" in shape

    def test_hook_generate_action(self, text_analysis_ttl: Path, tmp_path: Path) -> None:
        """Test hook with generate action."""
        hook = TTL2DSpyHook()

        request = {
            "action": "generate",
            "ttl_path": str(text_analysis_ttl),
            "output_dir": str(tmp_path),
            "module_name": "test_signatures",
        }

        receipt = hook.process_stdin(json.dumps(request))

        assert receipt["success"] is True
        assert receipt["action"] == "generate"
        assert receipt["signatures_count"] == TEXT_ANALYSIS_SHAPE_COUNT
        assert Path(receipt["output_path"]).exists()
        assert Path(receipt["receipt_path"]).exists()

    def test_hook_with_inline_ttl(self, tmp_path: Path) -> None:
        """Test hook with inline TTL content."""
        hook = TTL2DSpyHook()

        ttl_content = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:TestShape a sh:NodeShape ;
    rdfs:comment "Test shape" ;
    sh:property [
        sh:path ex:input ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        rdfs:comment "Input field"
    ] ;
    sh:property [
        sh:path ex:output ;
        sh:datatype xsd:string ;
        rdfs:comment "Output field"
    ] .
"""

        request = {
            "action": "generate",
            "ttl_content": ttl_content,
            "output_dir": str(tmp_path),
            "module_name": "inline_signatures",
        }

        receipt = hook.process_stdin(json.dumps(request))

        assert receipt["success"] is True
        assert receipt["signatures_count"] == 1

    def test_hook_error_handling(self) -> None:
        """Test hook error handling."""
        hook = TTL2DSpyHook()

        # Invalid request
        request = {
            "action": "generate"
            # Missing required fields
        }

        receipt = hook.process_stdin(json.dumps(request))

        assert receipt["success"] is False
        assert "error" in receipt
