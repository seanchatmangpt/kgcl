"""DSPy invocation integration tests.

Tests loading generated signatures, invoking with materialized features,
and receipt generation/storage.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kgcl.dspy_runtime import DSPY_AVAILABLE, UNRDFBridge


@pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
class TestDSPyIntegration:
    """Test DSPy integration with materialized features."""

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    @patch("requests.get")
    def test_invoke_with_materialized_features(
        self, mock_get, mock_ollama, mock_predict
    ):
        """Test invoking DSPy with real feature data."""
        # Mock Ollama
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
        mock_get.return_value = mock_response

        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock prediction
        mock_pred = Mock()
        mock_pred.answer = "Test answer based on features"
        mock_predictor = Mock()
        mock_predictor.return_value = mock_pred
        mock_predict.return_value = mock_predictor

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test signature
            sig_code = '''
import dspy

class TestFeatureSignature(dspy.Signature):
    """Process materialized features."""
    app_usage = dspy.InputField(desc="App usage time")
    answer = dspy.OutputField(desc="Processed result")
'''
            sig_file = Path(tmpdir) / "test_sig.py"
            sig_file.write_text(sig_code)

            bridge = UNRDFBridge()

            # Invoke with feature data
            result = bridge.invoke(
                module_path=str(sig_file),
                signature_name="TestFeatureSignature",
                inputs={"app_usage": "VSCode: 3600s, Safari: 1800s"},
                source_features=["app_usage_VSCode", "app_usage_Safari"],
            )

            assert result["result"]["success"] is True
            assert result["receipt"]["success"] is True
            assert len(result["receipt"]["source_features"]) == 2

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    @patch("requests.get")
    def test_receipt_generation(self, mock_get, mock_ollama, mock_predict):
        """Test receipt generation and RDF storage."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
        mock_get.return_value = mock_response

        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        mock_pred = Mock()
        mock_pred.output = "Result"
        mock_predictor = Mock()
        mock_predictor.return_value = mock_pred
        mock_predict.return_value = mock_predictor

        with tempfile.TemporaryDirectory() as tmpdir:
            sig_code = '''
import dspy
class ReceiptTestSig(dspy.Signature):
    input_text = dspy.InputField()
    output = dspy.OutputField()
'''
            sig_file = Path(tmpdir) / "receipt_sig.py"
            sig_file.write_text(sig_code)

            bridge = UNRDFBridge()

            result = bridge.invoke(
                module_path=str(sig_file),
                signature_name="ReceiptTestSig",
                inputs={"input_text": "test"},
            )

            # Verify receipt structure
            receipt = result["receipt"]
            assert "receipt_id" in receipt
            assert "signature_name" in receipt
            assert "timestamp" in receipt
            assert "model" in receipt
            assert receipt["signature_name"] == "ReceiptTestSig"

            # Verify can retrieve receipt
            receipt_id = receipt["receipt_id"]
            retrieved = bridge.get_receipt(receipt_id)
            assert retrieved is not None
            assert retrieved["receipt_id"] == receipt_id

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    @patch("requests.get")
    def test_error_handling_missing_ollama(
        self, mock_get, mock_ollama, mock_predict
    ):
        """Test error handling when Ollama unavailable."""
        # Mock Ollama not available
        mock_get.side_effect = ConnectionError("Connection refused")

        with tempfile.TemporaryDirectory() as tmpdir:
            sig_code = 'import dspy\nclass TestSig(dspy.Signature): pass'
            sig_file = Path(tmpdir) / "sig.py"
            sig_file.write_text(sig_code)

            bridge = UNRDFBridge()

            # Should handle gracefully
            with pytest.raises(Exception):
                bridge.invoke(
                    module_path=str(sig_file),
                    signature_name="TestSig",
                    inputs={},
                )

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    @patch("requests.get")
    def test_invalid_inputs(self, mock_get, mock_ollama, mock_predict):
        """Test handling of invalid inputs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
        mock_get.return_value = mock_response

        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock prediction to fail
        mock_predict.side_effect = ValueError("Invalid input")

        with tempfile.TemporaryDirectory() as tmpdir:
            sig_code = '''
import dspy
class TestSig(dspy.Signature):
    required_field = dspy.InputField()
    output = dspy.OutputField()
'''
            sig_file = Path(tmpdir) / "sig.py"
            sig_file.write_text(sig_code)

            bridge = UNRDFBridge()

            # Missing required field
            result = bridge.invoke(
                module_path=str(sig_file),
                signature_name="TestSig",
                inputs={},  # Missing required_field
            )

            # Should fail gracefully
            assert result["result"]["success"] is False
            assert result["result"]["error"] is not None

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    @patch("requests.get")
    def test_output_format_validation(self, mock_get, mock_ollama, mock_predict):
        """Test that outputs are correctly formatted."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
        mock_get.return_value = mock_response

        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock with multiple output fields
        mock_pred = Mock()
        mock_pred.field1 = "Output 1"
        mock_pred.field2 = "Output 2"
        mock_predictor = Mock()
        mock_predictor.return_value = mock_pred
        mock_predict.return_value = mock_predictor

        with tempfile.TemporaryDirectory() as tmpdir:
            sig_code = '''
import dspy
class MultiOutputSig(dspy.Signature):
    input = dspy.InputField()
    field1 = dspy.OutputField()
    field2 = dspy.OutputField()
'''
            sig_file = Path(tmpdir) / "sig.py"
            sig_file.write_text(sig_code)

            bridge = UNRDFBridge()

            result = bridge.invoke(
                module_path=str(sig_file),
                signature_name="MultiOutputSig",
                inputs={"input": "test"},
            )

            # Verify outputs
            assert result["result"]["success"] is True
            outputs = result["result"]["outputs"]
            assert "field1" in outputs
            assert "field2" in outputs
            assert outputs["field1"] == "Output 1"
            assert outputs["field2"] == "Output 2"
