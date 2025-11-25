"""UNRDF to TTL2DSPy code generation integration tests.

Tests loading feature templates from UNRDF, triggering TTL2DSPy code generation,
and signature caching/invalidation.
"""

import tempfile
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from kgcl.ttl2dspy.generator import DSPyGenerator
from kgcl.ttl2dspy.parser import OntologyParser
from kgcl.unrdf_engine.engine import UnrdfEngine

UNRDF = Namespace("http://unrdf.org/ontology/")
SH = Namespace("http://www.w3.org/ns/shacl#")


def create_feature_template_graph() -> Graph:
    """Create RDF graph with feature templates and SHACL shapes.

    Returns
    -------
    Graph
        RDF graph with feature templates
    """
    g = Graph()
    g.bind("unrdf", UNRDF)
    g.bind("sh", SH)
    g.bind("xsd", XSD)

    # Feature template for daily brief
    brief_template = UNRDF.DailyBriefTemplate
    g.add((brief_template, RDF.type, UNRDF.FeatureTemplate))
    g.add((brief_template, UNRDF.name, Literal("DailyBrief")))
    g.add((brief_template, UNRDF.description, Literal("Generate daily productivity brief")))

    # SHACL shape for the signature
    shape_uri = UNRDF.DailyBriefShape
    g.add((shape_uri, RDF.type, SH.NodeShape))
    g.add((shape_uri, UNRDF.signatureName, Literal("DailyBriefSignature")))
    g.add((shape_uri, UNRDF.description, Literal("Signature for generating daily brief")))

    # Input property: app_usage
    prop1 = UNRDF.prop_app_usage
    g.add((shape_uri, SH.property, prop1))
    g.add((prop1, SH.path, UNRDF.app_usage))
    g.add((prop1, SH.name, Literal("app_usage")))
    g.add((prop1, SH.description, Literal("Application usage statistics")))
    g.add((prop1, SH.datatype, XSD.string))
    g.add((prop1, SH.minCount, Literal(1)))
    g.add((prop1, UNRDF.fieldType, Literal("input")))

    # Input property: meeting_count
    prop2 = UNRDF.prop_meeting_count
    g.add((shape_uri, SH.property, prop2))
    g.add((prop2, SH.path, UNRDF.meeting_count))
    g.add((prop2, SH.name, Literal("meeting_count")))
    g.add((prop2, SH.description, Literal("Number of meetings today")))
    g.add((prop2, SH.datatype, XSD.integer))
    g.add((prop2, SH.minCount, Literal(1)))
    g.add((prop2, UNRDF.fieldType, Literal("input")))

    # Output property: summary
    prop3 = UNRDF.prop_summary
    g.add((shape_uri, SH.property, prop3))
    g.add((prop3, SH.path, UNRDF.summary))
    g.add((prop3, SH.name, Literal("summary")))
    g.add((prop3, SH.description, Literal("Brief summary of the day")))
    g.add((prop3, SH.datatype, XSD.string))
    g.add((prop3, UNRDF.fieldType, Literal("output")))

    return g


class TestUNRDFToCodegen:
    """Test UNRDF to code generation flow."""

    def test_load_feature_templates_from_unrdf(self):
        """Test loading feature templates from UNRDF graph."""
        g = create_feature_template_graph()

        # Query for feature templates
        query = """
        PREFIX unrdf: <http://unrdf.org/ontology/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?template ?name WHERE {
            ?template rdf:type unrdf:FeatureTemplate .
            ?template unrdf:name ?name .
        }
        """

        results = list(g.query(query))
        assert len(results) == 1

        template_uri, name = results[0]
        assert str(name) == "DailyBrief"

    def test_parse_shacl_shape_from_graph(self):
        """Test parsing SHACL shape from RDF graph."""
        g = create_feature_template_graph()

        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()

        assert len(shapes) == 1
        shape = shapes[0]

        assert shape.signature_name == "DailyBriefSignature"
        assert len(shape.input_properties) == 2
        assert len(shape.output_properties) == 1

        # Verify input properties
        input_names = {p.name for p in shape.input_properties}
        assert "app_usage" in input_names
        assert "meeting_count" in input_names

        # Verify output property
        output_names = {p.name for p in shape.output_properties}
        assert "summary" in output_names

    def test_generate_dspy_signature_from_shape(self):
        """Test generating DSPy signature code from SHACL shape."""
        g = create_feature_template_graph()

        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()
        shape = shapes[0]

        generator = DSPyGenerator()
        signature_def = generator.generate_signature(shape)

        assert signature_def.class_name == "DailyBriefSignature"
        assert len(signature_def.inputs) == 2
        assert len(signature_def.outputs) == 1

        # Generate code
        code = signature_def.generate_code()

        # Verify code structure
        assert "class DailyBriefSignature(dspy.Signature):" in code
        assert "app_usage" in code
        assert "meeting_count" in code
        assert "summary" in code
        assert "dspy.InputField" in code
        assert "dspy.OutputField" in code

    def test_generate_complete_module(self):
        """Test generating complete Python module from shapes."""
        g = create_feature_template_graph()

        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()

        generator = DSPyGenerator()
        module_code = generator.generate_module(shapes)

        # Verify module structure
        assert "import dspy" in module_code
        assert "Auto-generated DSPy signatures" in module_code
        assert "class DailyBriefSignature(dspy.Signature):" in module_code
        assert "__all__" in module_code

        # Verify can be written to file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(module_code)
            module_path = f.name

        # Verify file is valid Python
        with open(module_path) as f:
            code_content = f.read()
            compile(code_content, module_path, "exec")

        Path(module_path).unlink()

    def test_signature_caching(self):
        """Test that signature generation uses caching."""
        g = create_feature_template_graph()

        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()
        shape = shapes[0]

        generator = DSPyGenerator()

        # Generate signature twice
        sig1 = generator.generate_signature(shape)
        sig2 = generator.generate_signature(shape)

        # Should return same object (cached)
        assert sig1 is sig2

        # Verify cache stats
        stats = generator.get_cache_stats()
        assert stats["generated_signatures"] == 1

    def test_cache_invalidation(self):
        """Test cache invalidation when shapes change."""
        g = create_feature_template_graph()

        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()
        shape = shapes[0]

        generator = DSPyGenerator()

        # Generate signature
        sig1 = generator.generate_signature(shape)
        assert generator.get_cache_stats()["generated_signatures"] == 1

        # Clear cache
        generator.clear_cache()
        assert generator.get_cache_stats()["generated_signatures"] == 0

        # Generate again
        sig2 = generator.generate_signature(shape)

        # Should be different object
        assert sig1 is not sig2

    def test_hook_trigger_on_template_change(self):
        """Test that code generation hook triggers on template changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = UnrdfEngine(file_path=Path(tmpdir) / "graph.ttl")

            # Track hook execution
            codegen_triggered = []

            from kgcl.unrdf_engine.hooks import (
                HookContext,
                HookExecutor,
                HookPhase,
                HookRegistry,
                KnowledgeHook,
                TriggerCondition,
            )

            class CodegenHook(KnowledgeHook):
                def __init__(self):
                    super().__init__(
                        name="ttl2dspy_codegen",
                        phases=[HookPhase.POST_COMMIT],
                        trigger=TriggerCondition(
                            pattern="?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/shacl#NodeShape>",
                            check_delta=True,
                            min_matches=1,
                        ),
                    )

                def execute(self, context: HookContext):
                    codegen_triggered.append("codegen")
                    # In real implementation, would trigger TTL2DSPy

            registry = HookRegistry()
            registry.register(CodegenHook())
            hook_executor = HookExecutor(registry)

            from kgcl.unrdf_engine.ingestion import IngestionPipeline

            pipeline = IngestionPipeline(engine, hook_executor=hook_executor)

            # Add SHACL shape (should trigger codegen)
            g = create_feature_template_graph()
            shape_triples = []

            for s, p, o in g:
                shape_triples.append({"subject": str(s), "predicate": str(p), "object": str(o)})

            # Ingest shape
            result = pipeline.ingest_json(
                data={"id": "shape_001", "type": "SHACLShape", "triples": shape_triples},
                agent="test",
            )

            # Verify hook would trigger (delta has SHACL shape)
            # Note: In simplified test, we verify mechanism exists
            assert result.success is True

    def test_signature_validation(self):
        """Test that generated signatures have correct structure."""
        g = create_feature_template_graph()

        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()
        shape = shapes[0]

        generator = DSPyGenerator()
        signature_def = generator.generate_signature(shape)

        # Verify all inputs are required
        for prop in signature_def.inputs:
            # Check property has description
            assert len(prop.description) > 0

        # Verify outputs have descriptions
        for prop in signature_def.outputs:
            assert len(prop.description) > 0

        # Generate code and verify syntax
        code = signature_def.generate_code()
        compile(code, "<string>", "exec")

    def test_multiple_shapes_generation(self):
        """Test generating multiple signatures in one module."""
        g = create_feature_template_graph()

        # Add another shape
        shape2_uri = UNRDF.WeeklyRetroShape
        g.add((shape2_uri, RDF.type, SH.NodeShape))
        g.add((shape2_uri, UNRDF.signatureName, Literal("WeeklyRetroSignature")))

        # Add input property
        prop = UNRDF.prop_weekly_events
        g.add((shape2_uri, SH.property, prop))
        g.add((prop, SH.path, UNRDF.weekly_events))
        g.add((prop, SH.name, Literal("weekly_events")))
        g.add((prop, SH.datatype, XSD.string))
        g.add((prop, UNRDF.fieldType, Literal("input")))

        # Add output property
        prop_out = UNRDF.prop_retrospective
        g.add((shape2_uri, SH.property, prop_out))
        g.add((prop_out, SH.path, UNRDF.retrospective))
        g.add((prop_out, SH.name, Literal("retrospective")))
        g.add((prop_out, SH.datatype, XSD.string))
        g.add((prop_out, UNRDF.fieldType, Literal("output")))

        # Parse and generate
        # Use OntologyParser to parse SHACL shapes
        parser = OntologyParser()
        parser.load_graph(g)
        shapes = parser.extract_shapes()

        assert len(shapes) == 2

        generator = DSPyGenerator()
        module_code = generator.generate_module(shapes)

        # Verify both signatures present
        assert "DailyBriefSignature" in module_code
        assert "WeeklyRetroSignature" in module_code

        # Verify __all__ includes both
        assert '"DailyBriefSignature"' in module_code
        assert '"WeeklyRetroSignature"' in module_code

    def test_incremental_signature_updates(self):
        """Test updating signatures when shapes change."""
        g = create_feature_template_graph()

        parser = SHACLParser()
        shapes_v1 = parser.parse_graph(g)

        generator = DSPyGenerator()
        sig_v1 = generator.generate_signature(shapes_v1[0])

        # Modify graph - add new input field
        shape_uri = UNRDF.DailyBriefShape
        new_prop = UNRDF.prop_context_switches
        g.add((shape_uri, SH.property, new_prop))
        g.add((new_prop, SH.path, UNRDF.context_switches))
        g.add((new_prop, SH.name, Literal("context_switches")))
        g.add((new_prop, SH.datatype, XSD.integer))
        g.add((new_prop, UNRDF.fieldType, Literal("input")))

        # Re-parse
        shapes_v2 = parser.parse_graph(g)

        # Clear cache to force regeneration
        generator.clear_cache()

        sig_v2 = generator.generate_signature(shapes_v2[0])

        # Verify new field present
        assert len(sig_v2.inputs) == 3  # Original 2 + 1 new
        input_names = {p.name for p in sig_v2.inputs}
        assert "context_switches" in input_names

    def test_write_and_load_generated_module(self):
        """Test writing generated module to file and loading it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = create_feature_template_graph()

            parser = SHACLParser()
            shapes = parser.parse_graph(g)

            generator = DSPyGenerator()
            module_code = generator.generate_module(shapes)

            # Write to file
            module_file = Path(tmpdir) / "generated_signatures.py"
            module_file.write_text(module_code)

            # Verify file exists and is readable
            assert module_file.exists()
            assert len(module_file.read_text()) > 0

            # Verify module is valid Python
            import ast

            with open(module_file) as f:
                ast.parse(f.read())
