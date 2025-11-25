"""Tests for DSPy code generator."""

import pytest
from rdflib import URIRef
from rdflib.namespace import XSD

from kgcl.ttl2dspy.parser import SHACLShape, PropertyShape
from kgcl.ttl2dspy.generator import DSPyGenerator, SignatureDefinition


@pytest.fixture
def sample_shape():
    """Create a sample SHACL shape."""
    shape = SHACLShape(
        uri=URIRef("http://example.org/PersonShape"),
        name="PersonShape",
        description="Generate a person description",
        properties=[
            PropertyShape(
                path=URIRef("http://example.org/name"),
                name="name",
                datatype=XSD.string,
                min_count=1,
                description="Person's name",
            ),
            PropertyShape(
                path=URIRef("http://example.org/age"),
                name="age",
                datatype=XSD.integer,
                min_count=0,
                description="Person's age",
            ),
            PropertyShape(
                path=URIRef("http://example.org/description"),
                name="description",
                datatype=XSD.string,
                description="Generated description",
            ),
        ],
    )
    shape.categorize_properties()
    return shape


class TestSignatureDefinition:
    """Tests for SignatureDefinition class."""

    def test_generate_code_basic(self):
        """Test basic code generation."""
        sig = SignatureDefinition(
            class_name="TestSignature",
            docstring="Test signature",
            inputs=[
                PropertyShape(
                    path=URIRef("http://example.org/input"),
                    name="input_text",
                    datatype=XSD.string,
                    min_count=1,
                ),
            ],
            outputs=[
                PropertyShape(
                    path=URIRef("http://example.org/output"),
                    name="output_text",
                    datatype=XSD.string,
                ),
            ],
        )

        code = sig.generate_code()

        assert "class TestSignature(dspy.Signature):" in code
        assert "Test signature" in code
        assert "input_text: str = dspy.InputField" in code
        assert "output_text: Optional[str] = dspy.OutputField" in code

    def test_generate_code_with_descriptions(self):
        """Test code generation with field descriptions."""
        sig = SignatureDefinition(
            class_name="TestSignature",
            inputs=[
                PropertyShape(
                    path=URIRef("http://example.org/input"),
                    name="query",
                    datatype=XSD.string,
                    min_count=1,
                    description="User query to process",
                ),
            ],
            outputs=[
                PropertyShape(
                    path=URIRef("http://example.org/output"),
                    name="answer",
                    datatype=XSD.string,
                    description="Generated answer",
                ),
            ],
        )

        code = sig.generate_code()

        assert 'desc="User query to process"' in code
        assert 'desc="Generated answer"' in code

    def test_get_imports_basic(self):
        """Test import generation."""
        sig = SignatureDefinition(
            class_name="TestSignature",
            inputs=[
                PropertyShape(
                    path=URIRef("http://example.org/input"),
                    name="text",
                    datatype=XSD.string,
                    min_count=1,
                ),
            ],
        )

        imports = sig.get_imports()

        assert "import dspy" in imports
        assert len(imports) == 1  # Only dspy, no typing needed

    def test_get_imports_with_typing(self):
        """Test import generation with typing."""
        sig = SignatureDefinition(
            class_name="TestSignature",
            inputs=[
                PropertyShape(
                    path=URIRef("http://example.org/input"),
                    name="tags",
                    datatype=XSD.string,
                    max_count=None,
                ),
            ],
            outputs=[
                PropertyShape(
                    path=URIRef("http://example.org/output"),
                    name="result",
                    datatype=XSD.string,
                ),
            ],
        )

        imports = sig.get_imports()

        assert "import dspy" in imports
        assert any("from typing import" in imp for imp in imports)
        assert any("List" in imp for imp in imports)
        assert any("Optional" in imp for imp in imports)


class TestDSPyGenerator:
    """Tests for DSPyGenerator class."""

    def test_generate_signature(self, sample_shape):
        """Test signature generation from shape."""
        generator = DSPyGenerator()
        sig = generator.generate_signature(sample_shape)

        assert sig.class_name == "PersonSignature"
        assert sig.docstring == "Generate a person description"
        assert len(sig.inputs) == 2
        assert len(sig.outputs) == 1

    def test_generate_signature_caching(self, sample_shape):
        """Test signature caching."""
        generator = DSPyGenerator()

        sig1 = generator.generate_signature(sample_shape)
        sig2 = generator.generate_signature(sample_shape)

        assert sig1 is sig2  # Same object from cache

        stats = generator.get_cache_stats()
        assert stats["generated_signatures"] == 1

    def test_generate_module(self, sample_shape):
        """Test module generation."""
        generator = DSPyGenerator()
        code = generator.generate_module([sample_shape])

        # Check for required elements
        assert "import dspy" in code
        assert "from typing import" in code
        assert "class PersonSignature(dspy.Signature):" in code
        assert "__all__ = [" in code
        assert '"PersonSignature"' in code

        # Check for fields
        assert "name: str = dspy.InputField" in code
        assert "age: Optional[int] = dspy.InputField" in code
        assert "description: Optional[str] = dspy.OutputField" in code

    def test_generate_module_multiple_shapes(self):
        """Test module generation with multiple shapes."""
        shape1 = SHACLShape(
            uri=URIRef("http://example.org/Shape1"),
            name="Shape1",
            properties=[
                PropertyShape(
                    path=URIRef("http://example.org/input1"),
                    name="input1",
                    datatype=XSD.string,
                    min_count=1,
                ),
                PropertyShape(
                    path=URIRef("http://example.org/output1"),
                    name="output1",
                    datatype=XSD.string,
                ),
            ],
        )
        shape1.categorize_properties()

        shape2 = SHACLShape(
            uri=URIRef("http://example.org/Shape2"),
            name="Shape2",
            properties=[
                PropertyShape(
                    path=URIRef("http://example.org/input2"),
                    name="input2",
                    datatype=XSD.integer,
                    min_count=1,
                ),
                PropertyShape(
                    path=URIRef("http://example.org/output2"),
                    name="output2",
                    datatype=XSD.boolean,
                ),
            ],
        )
        shape2.categorize_properties()

        generator = DSPyGenerator()
        code = generator.generate_module([shape1, shape2])

        assert "class Shape1Signature(dspy.Signature):" in code
        assert "class Shape2Signature(dspy.Signature):" in code
        assert '"Shape1Signature"' in code
        assert '"Shape2Signature"' in code

    def test_clear_cache(self):
        """Test cache clearing."""
        generator = DSPyGenerator()

        shape = SHACLShape(
            uri=URIRef("http://example.org/Test"),
            name="Test",
        )
        generator.generate_signature(shape)

        assert len(generator._generated) == 1

        generator.clear_cache()

        assert len(generator._generated) == 0
