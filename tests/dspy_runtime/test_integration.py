"""
Integration tests for DSPy runtime.

Tests end-to-end workflows including signature loading, invocation,
receipt generation, and RDF storage.
"""

from unittest.mock import Mock, patch

import pytest

from kgcl.dspy_runtime import DSPY_AVAILABLE, ReceiptGenerator, SignatureInvoker, UNRDFBridge


@pytest.fixture
def test_signature_module(tmp_path):
    """Create test signature module."""
    signature_code = '''
import dspy

class IntegrationTestSignature(dspy.Signature):
    """Integration test signature."""
    context = dspy.InputField(desc="Context for the question")
    question = dspy.InputField(desc="Question to answer")
    answer = dspy.OutputField(desc="Answer to the question")

class SimpleSignature(dspy.Signature):
    """Simple signature for testing."""
    text = dspy.InputField()
    summary = dspy.OutputField()
'''

    sig_file = tmp_path / "integration_sigs.py"
    sig_file.write_text(signature_code)
    return sig_file


@pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    def test_simple_invocation_workflow(self, mock_ollama, mock_predict, test_signature_module):
        """Test simple invocation from module to receipt."""
        # Mock LM
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock prediction
        mock_prediction = Mock()
        mock_prediction.summary = "This is a summary"

        mock_predictor = Mock()
        mock_predictor.return_value = mock_prediction
        mock_predict.return_value = mock_predictor

        # Mock Ollama availability
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
            mock_get.return_value = mock_response

            # Create bridge
            bridge = UNRDFBridge()
            bridge.initialize()

            # Invoke
            result = bridge.invoke(
                module_path=str(test_signature_module),
                signature_name="SimpleSignature",
                inputs={"text": "This is a long text that needs summarizing."},
            )

            # Verify result
            assert result["result"]["success"] is True
            assert "receipt" in result
            assert "receipt_uri" in result

            # Verify receipt
            receipt = result["receipt"]
            assert receipt["signature_name"] == "SimpleSignature"
            assert receipt["success"] is True

            # Verify can retrieve receipt
            receipt_id = receipt["receipt_id"]
            retrieved = bridge.get_receipt(receipt_id)
            assert retrieved is not None

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    def test_multi_signature_workflow(self, mock_ollama, mock_predict, test_signature_module):
        """Test invoking multiple signatures."""
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock predictions for both signatures
        mock_pred1 = Mock()
        mock_pred1.answer = "Answer 1"

        mock_pred2 = Mock()
        mock_pred2.summary = "Summary 2"

        mock_predictor = Mock()
        mock_predictor.side_effect = [mock_pred1, mock_pred2]
        mock_predict.return_value = mock_predictor

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
            mock_get.return_value = mock_response

            bridge = UNRDFBridge()
            bridge.initialize()

            # Invoke first signature
            result1 = bridge.invoke(
                module_path=str(test_signature_module),
                signature_name="IntegrationTestSignature",
                inputs={"context": "Context", "question": "Question?"},
            )

            # Invoke second signature
            result2 = bridge.invoke(
                module_path=str(test_signature_module),
                signature_name="SimpleSignature",
                inputs={"text": "Text to summarize"},
            )

            # Verify both succeeded
            assert result1["result"]["success"] is True
            assert result2["result"]["success"] is True

            # Verify receipts are distinct
            assert result1["receipt"]["receipt_id"] != result2["receipt"]["receipt_id"]

            # List receipts
            receipts = bridge.list_receipts()
            assert len(receipts) == 2

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    def test_batch_invocation_workflow(self, mock_ollama, mock_predict, test_signature_module):
        """Test batch invocation workflow."""
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        mock_prediction = Mock()
        mock_prediction.summary = "Summary"

        mock_predictor = Mock()
        mock_predictor.return_value = mock_prediction
        mock_predict.return_value = mock_predictor

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
            mock_get.return_value = mock_response

            bridge = UNRDFBridge()

            # Batch invoke
            invocations = [
                {
                    "module_path": str(test_signature_module),
                    "signature_name": "SimpleSignature",
                    "inputs": {"text": f"Text {i}"},
                }
                for i in range(5)
            ]

            results = bridge.batch_invoke(invocations)

            assert len(results) == 5
            assert all(r["result"]["success"] for r in results)

            # Verify all receipts stored
            receipts = bridge.list_receipts()
            assert len(receipts) == 5

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    def test_receipt_persistence_workflow(
        self, mock_ollama, mock_predict, test_signature_module, tmp_path
    ):
        """Test receipt persistence and loading."""
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        mock_prediction = Mock()
        mock_prediction.summary = "Summary"

        mock_predictor = Mock()
        mock_predictor.return_value = mock_prediction
        mock_predict.return_value = mock_predictor

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
            mock_get.return_value = mock_response

            # Create bridge and invoke
            bridge1 = UNRDFBridge()
            result = bridge1.invoke(
                module_path=str(test_signature_module),
                signature_name="SimpleSignature",
                inputs={"text": "Test text"},
            )

            receipt_id = result["receipt"]["receipt_id"]

            # Export receipts
            export_file = tmp_path / "receipts.ttl"
            bridge1.export_receipts(str(export_file))

            # Create new bridge and import
            bridge2 = UNRDFBridge()
            bridge2.import_receipts(str(export_file))

            # Verify receipt accessible
            retrieved = bridge2.get_receipt(receipt_id)
            assert retrieved is not None
            assert retrieved["receipt_id"] == receipt_id

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    def test_error_handling_workflow(self, mock_ollama, mock_predict, test_signature_module):
        """Test error handling in workflow."""
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock prediction to fail
        mock_predict.side_effect = RuntimeError("Prediction failed")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
            mock_get.return_value = mock_response

            bridge = UNRDFBridge()

            # Invoke (should handle error gracefully)
            result = bridge.invoke(
                module_path=str(test_signature_module),
                signature_name="SimpleSignature",
                inputs={"text": "Test"},
            )

            # Verify error captured
            assert result["result"]["success"] is False
            assert result["result"]["error"] is not None

            # Verify receipt created for error
            assert result["receipt"] is not None
            assert result["receipt"]["success"] is False
            assert result["receipt"]["error"] is not None

    @patch("dspy.Predict")
    @patch("dspy.OllamaLocal")
    def test_statistics_workflow(self, mock_ollama, mock_predict, test_signature_module):
        """Test statistics collection workflow."""
        mock_lm = Mock()
        mock_ollama.return_value = mock_lm

        # Mock mix of success and failure
        mock_success = Mock()
        mock_success.summary = "Summary"

        mock_predictor = Mock()
        mock_predictor.side_effect = [
            mock_success,
            mock_success,
            RuntimeError("Failed"),
            mock_success,
        ]
        mock_predict.return_value = mock_predictor

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.1"}]}
            mock_get.return_value = mock_response

            bridge = UNRDFBridge()

            # Invoke multiple times
            for i in range(4):
                bridge.invoke(
                    module_path=str(test_signature_module),
                    signature_name="SimpleSignature",
                    inputs={"text": f"Test {i}"},
                )

            # Get statistics
            stats = bridge.get_stats()

            assert stats["total_invocations"] == 4
            assert stats["successful_invocations"] == 3
            assert stats["failed_invocations"] == 1
            assert stats["success_rate"] == 0.75
            assert "average_latency_seconds" in stats


@pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
@pytest.mark.integration
class TestComponentIntegration:
    """Test integration between components."""

    def test_invoker_receipt_generator_integration(self, test_signature_module):
        """Test integration between invoker and receipt generator."""
        with patch("dspy.Predict") as mock_predict:
            mock_prediction = Mock()
            mock_prediction.summary = "Result"

            mock_predictor = Mock()
            mock_predictor.return_value = mock_prediction
            mock_predict.return_value = mock_predictor

            # Create invoker
            invoker = SignatureInvoker()

            # Invoke
            result = invoker.invoke_from_module(
                str(test_signature_module), "SimpleSignature", {"text": "Test"}
            )

            # Create receipt from result
            generator = ReceiptGenerator()
            receipt = generator.generate_receipt(
                signature_name="SimpleSignature",
                module_path=str(test_signature_module),
                inputs=result.inputs,
                outputs=result.outputs,
                success=result.success,
                latency_seconds=result.metrics.get("latency_seconds"),
            )

            # Store and retrieve
            generator.store_receipt(receipt)
            retrieved = generator.get_receipt(receipt.receipt_id)

            assert retrieved is not None
            assert retrieved.signature_name == "SimpleSignature"
