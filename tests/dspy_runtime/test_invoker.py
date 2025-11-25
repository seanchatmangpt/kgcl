"""
Unit tests for DSPy signature invoker.
"""

import json
from unittest.mock import Mock, patch

import pytest

from kgcl.dspy_runtime.invoker import DSPY_AVAILABLE, InvocationResult, SignatureInvoker


@pytest.fixture
def sample_signature_module(tmp_path):
    """Create a sample signature module for testing."""
    signature_code = '''
import dspy

class TestSignature(dspy.Signature):
    """Test signature for unit tests."""
    input_text = dspy.InputField()
    output_text = dspy.OutputField()
'''

    signature_file = tmp_path / "test_signature.py"
    signature_file.write_text(signature_code)
    return signature_file


class TestInvocationResult:
    """Test InvocationResult dataclass."""

    def test_success_result(self):
        """Test successful invocation result."""
        result = InvocationResult(
            success=True,
            inputs={"input": "test"},
            outputs={"output": "result"},
            metrics={"latency_seconds": 1.5},
        )

        assert result.success is True
        assert result.inputs["input"] == "test"
        assert result.outputs["output"] == "result"
        assert result.error is None

    def test_error_result(self):
        """Test error invocation result."""
        result = InvocationResult(
            success=False, inputs={"input": "test"}, error="Something went wrong"
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.outputs == {}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = InvocationResult(success=True, inputs={"a": 1}, outputs={"b": 2})

        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert "inputs" in result_dict
        assert "outputs" in result_dict

    def test_to_json(self):
        """Test conversion to JSON."""
        result = InvocationResult(
            success=True, inputs={"test": "value"}, outputs={"result": "data"}
        )

        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["inputs"]["test"] == "value"


@pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
class TestSignatureInvoker:
    """Test SignatureInvoker class."""

    def test_init(self):
        """Test invoker initialization."""
        invoker = SignatureInvoker()
        assert invoker._signature_cache == {}

    def test_load_signature_success(self, sample_signature_module):
        """Test loading signature from module."""
        invoker = SignatureInvoker()

        signature = invoker.load_signature(str(sample_signature_module), "TestSignature")

        assert signature.__name__ == "TestSignature"
        assert "input_text" in signature.input_fields
        assert "output_text" in signature.output_fields

    def test_load_signature_caching(self, sample_signature_module):
        """Test signature caching."""
        invoker = SignatureInvoker()

        # Load twice
        sig1 = invoker.load_signature(str(sample_signature_module), "TestSignature")
        sig2 = invoker.load_signature(str(sample_signature_module), "TestSignature")

        assert sig1 is sig2
        assert len(invoker._signature_cache) == 1

    def test_load_signature_file_not_found(self):
        """Test loading from nonexistent file."""
        invoker = SignatureInvoker()

        with pytest.raises(FileNotFoundError):
            invoker.load_signature("/nonexistent/path.py", "TestSignature")

    def test_load_signature_class_not_found(self, sample_signature_module):
        """Test loading nonexistent signature class."""
        invoker = SignatureInvoker()

        with pytest.raises(AttributeError, match="Signature.*not found"):
            invoker.load_signature(str(sample_signature_module), "NonexistentSignature")

    def test_validate_inputs_success(self, sample_signature_module):
        """Test input validation - success."""
        invoker = SignatureInvoker()
        signature = invoker.load_signature(str(sample_signature_module), "TestSignature")

        is_valid, error = invoker.validate_inputs(signature, {"input_text": "test"})

        assert is_valid is True
        assert error is None

    def test_validate_inputs_missing_field(self, sample_signature_module):
        """Test input validation - missing field."""
        invoker = SignatureInvoker()
        signature = invoker.load_signature(str(sample_signature_module), "TestSignature")

        is_valid, error = invoker.validate_inputs(signature, {})

        assert is_valid is False
        assert "Missing required input fields" in error

    def test_validate_inputs_extra_field(self, sample_signature_module):
        """Test input validation - extra field."""
        invoker = SignatureInvoker()
        signature = invoker.load_signature(str(sample_signature_module), "TestSignature")

        is_valid, error = invoker.validate_inputs(
            signature, {"input_text": "test", "extra_field": "value"}
        )

        # Should still be valid, extra fields ignored
        assert is_valid is True

    @patch("dspy.Predict")
    def test_invoke_success(self, mock_predict, sample_signature_module):
        """Test successful signature invocation."""
        # Mock prediction result
        mock_prediction = Mock()
        mock_prediction.output_text = "Generated output"

        mock_predictor = Mock()
        mock_predictor.return_value = mock_prediction
        mock_predict.return_value = mock_predictor

        invoker = SignatureInvoker()
        signature = invoker.load_signature(str(sample_signature_module), "TestSignature")

        result = invoker.invoke(signature, {"input_text": "test input"})

        assert result.success is True
        assert result.inputs["input_text"] == "test input"
        assert "latency_seconds" in result.metrics

    @patch("dspy.Predict")
    def test_invoke_error(self, mock_predict, sample_signature_module):
        """Test invocation with error."""
        mock_predict.side_effect = RuntimeError("Prediction failed")

        invoker = SignatureInvoker()
        signature = invoker.load_signature(str(sample_signature_module), "TestSignature")

        result = invoker.invoke(signature, {"input_text": "test"})

        assert result.success is False
        assert result.error is not None
        assert "Prediction failed" in result.error

    @patch("dspy.Predict")
    def test_invoke_from_module(self, mock_predict, sample_signature_module):
        """Test invoking from module path."""
        mock_prediction = Mock()
        mock_prediction.output_text = "result"

        mock_predictor = Mock()
        mock_predictor.return_value = mock_prediction
        mock_predict.return_value = mock_predictor

        invoker = SignatureInvoker()

        result = invoker.invoke_from_module(
            str(sample_signature_module), "TestSignature", {"input_text": "test"}
        )

        assert result.success is True

    def test_invoke_from_module_load_error(self):
        """Test invoke_from_module with load error."""
        invoker = SignatureInvoker()

        result = invoker.invoke_from_module(
            "/nonexistent/module.py", "TestSignature", {"input_text": "test"}
        )

        assert result.success is False
        assert result.error is not None


@pytest.mark.skipif(DSPY_AVAILABLE, reason="Test DSPy unavailable case")
class TestInvokerWithoutDSPy:
    """Test invoker behavior when DSPy not available."""

    def test_init_without_dspy(self):
        """Test initialization without DSPy raises error."""
        with pytest.raises(RuntimeError, match="DSPy is not installed"):
            SignatureInvoker()
