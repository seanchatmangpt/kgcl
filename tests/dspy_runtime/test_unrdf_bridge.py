"""
Unit tests for UNRDF bridge.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from rdflib import Graph

from kgcl.dspy_runtime.unrdf_bridge import UNRDFBridge
from kgcl.dspy_runtime.ollama_config import OllamaConfig, DSPY_AVAILABLE
from kgcl.dspy_runtime.invoker import InvocationResult


@pytest.fixture
def sample_signature_module(tmp_path):
    """Create a sample signature module."""
    signature_code = '''
import dspy

class BridgeTestSignature(dspy.Signature):
    """Test signature for bridge tests."""
    question = dspy.InputField()
    answer = dspy.OutputField()
'''

    signature_file = tmp_path / "bridge_test_sig.py"
    signature_file.write_text(signature_code)
    return signature_file


class TestUNRDFBridge:
    """Test UNRDFBridge class."""

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = OllamaConfig(model="custom-model")
        bridge = UNRDFBridge(ollama_config=config)

        assert bridge.ollama_config.model == "custom-model"
        assert not bridge._initialized

    def test_init_with_graph(self):
        """Test initialization with custom RDF graph."""
        graph = Graph()
        bridge = UNRDFBridge(rdf_graph=graph)

        assert isinstance(bridge.receipt_generator.graph, Graph)

    def test_init_without_params(self):
        """Test initialization with defaults."""
        bridge = UNRDFBridge()

        assert bridge.ollama_config is not None
        assert bridge.receipt_generator is not None

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_initialize(self, mock_invoker, mock_lm):
        """Test bridge initialization."""
        bridge = UNRDFBridge()
        bridge.initialize()

        assert bridge._initialized is True
        assert bridge.ollama_lm is not None
        assert bridge.invoker is not None

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_invoke_success(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test successful invocation through bridge."""
        # Mock components
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        mock_result = InvocationResult(
            success=True,
            inputs={"question": "test"},
            outputs={"answer": "result"},
            metrics={"latency_seconds": 1.0}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.return_value = mock_result
        mock_invoker_class.return_value = mock_invoker

        # Create bridge and invoke
        bridge = UNRDFBridge()
        result = bridge.invoke(
            module_path=str(sample_signature_module),
            signature_name="BridgeTestSignature",
            inputs={"question": "What is 2+2?"}
        )

        assert result["result"]["success"] is True
        assert "receipt" in result
        assert "receipt_uri" in result

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_invoke_with_features(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test invocation with source features."""
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        mock_result = InvocationResult(
            success=True,
            inputs={"question": "test"},
            outputs={"answer": "result"},
            metrics={"latency_seconds": 1.0}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.return_value = mock_result
        mock_invoker_class.return_value = mock_invoker

        bridge = UNRDFBridge()
        result = bridge.invoke(
            module_path=str(sample_signature_module),
            signature_name="BridgeTestSignature",
            inputs={"question": "test"},
            source_features=["http://example.com/feature1"],
            source_signatures=["http://example.com/sig1"]
        )

        assert result["result"]["success"] is True

        # Verify receipt has source links
        receipt = result["receipt"]
        assert len(receipt["source_features"]) == 1
        assert len(receipt["source_signatures"]) == 1

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_batch_invoke(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test batch invocation."""
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        # Mock results
        mock_result1 = InvocationResult(
            success=True,
            inputs={"question": "q1"},
            outputs={"answer": "a1"},
            metrics={"latency_seconds": 1.0}
        )

        mock_result2 = InvocationResult(
            success=True,
            inputs={"question": "q2"},
            outputs={"answer": "a2"},
            metrics={"latency_seconds": 1.5}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.side_effect = [mock_result1, mock_result2]
        mock_invoker_class.return_value = mock_invoker

        # Batch invocation
        bridge = UNRDFBridge()
        invocations = [
            {
                "module_path": str(sample_signature_module),
                "signature_name": "BridgeTestSignature",
                "inputs": {"question": "q1"}
            },
            {
                "module_path": str(sample_signature_module),
                "signature_name": "BridgeTestSignature",
                "inputs": {"question": "q2"}
            }
        ]

        results = bridge.batch_invoke(invocations)

        assert len(results) == 2
        assert results[0]["result"]["success"] is True
        assert results[1]["result"]["success"] is True

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_batch_invoke_with_error(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test batch invocation with one failure."""
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        mock_result_success = InvocationResult(
            success=True,
            inputs={"question": "q1"},
            outputs={"answer": "a1"},
            metrics={}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.side_effect = [
            mock_result_success,
            RuntimeError("Invocation failed")
        ]
        mock_invoker_class.return_value = mock_invoker

        bridge = UNRDFBridge()
        invocations = [
            {
                "module_path": str(sample_signature_module),
                "signature_name": "BridgeTestSignature",
                "inputs": {"question": "q1"}
            },
            {
                "module_path": str(sample_signature_module),
                "signature_name": "BridgeTestSignature",
                "inputs": {"question": "q2"}
            }
        ]

        results = bridge.batch_invoke(invocations)

        assert len(results) == 2
        assert results[0]["result"]["success"] is True
        assert results[1]["result"]["success"] is False

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_get_receipt(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test retrieving receipt by ID."""
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        mock_result = InvocationResult(
            success=True,
            inputs={"question": "test"},
            outputs={"answer": "result"},
            metrics={"latency_seconds": 1.0}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.return_value = mock_result
        mock_invoker_class.return_value = mock_invoker

        bridge = UNRDFBridge()

        # Invoke to create receipt
        result = bridge.invoke(
            module_path=str(sample_signature_module),
            signature_name="BridgeTestSignature",
            inputs={"question": "test"}
        )

        receipt_id = result["receipt"]["receipt_id"]

        # Retrieve receipt
        retrieved = bridge.get_receipt(receipt_id)

        assert retrieved is not None
        assert retrieved["receipt_id"] == receipt_id

    def test_get_nonexistent_receipt(self):
        """Test retrieving nonexistent receipt."""
        bridge = UNRDFBridge()

        receipt = bridge.get_receipt("nonexistent-id")
        assert receipt is None

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_list_receipts(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test listing receipts."""
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        mock_result = InvocationResult(
            success=True,
            inputs={"question": "test"},
            outputs={"answer": "result"},
            metrics={}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.return_value = mock_result
        mock_invoker_class.return_value = mock_invoker

        bridge = UNRDFBridge()

        # Create multiple receipts
        for i in range(3):
            bridge.invoke(
                module_path=str(sample_signature_module),
                signature_name="BridgeTestSignature",
                inputs={"question": f"q{i}"}
            )

        # List receipts
        receipts = bridge.list_receipts()
        assert len(receipts) == 3

    def test_export_receipts(self, tmp_path):
        """Test exporting receipts."""
        bridge = UNRDFBridge()

        output_file = tmp_path / "receipts.ttl"
        bridge.export_receipts(str(output_file))

        assert output_file.exists()

    def test_import_receipts(self, tmp_path):
        """Test importing receipts."""
        # Create and export
        bridge1 = UNRDFBridge()
        export_file = tmp_path / "export.ttl"
        bridge1.export_receipts(str(export_file))

        # Import into new bridge
        bridge2 = UNRDFBridge()
        bridge2.import_receipts(str(export_file))

        # Should not raise error
        assert True

    @patch("kgcl.dspy_runtime.ollama_config.health_check")
    def test_health_check(self, mock_health_check):
        """Test bridge health check."""
        mock_health_check.return_value = {
            "status": "healthy",
            "ollama_available": True
        }

        bridge = UNRDFBridge()
        health = bridge.health_check()

        assert "bridge_initialized" in health
        assert "receipt_count" in health

    @pytest.mark.skipif(not DSPY_AVAILABLE, reason="DSPy not available")
    @patch("kgcl.dspy_runtime.unrdf_bridge.OllamaLM")
    @patch("kgcl.dspy_runtime.unrdf_bridge.SignatureInvoker")
    def test_get_stats(self, mock_invoker_class, mock_lm_class, sample_signature_module):
        """Test getting statistics."""
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        # Create mix of successful and failed results
        mock_success = InvocationResult(
            success=True,
            inputs={},
            outputs={},
            metrics={"latency_seconds": 1.0}
        )

        mock_failure = InvocationResult(
            success=False,
            inputs={},
            outputs={},
            error="Failed",
            metrics={"latency_seconds": 2.0}
        )

        mock_invoker = Mock()
        mock_invoker.invoke_from_module.side_effect = [mock_success, mock_failure]
        mock_invoker_class.return_value = mock_invoker

        bridge = UNRDFBridge()

        # Create invocations
        for i in range(2):
            bridge.invoke(
                module_path=str(sample_signature_module),
                signature_name="BridgeTestSignature",
                inputs={"question": f"q{i}"}
            )

        stats = bridge.get_stats()

        assert stats["total_invocations"] == 2
        assert stats["successful_invocations"] == 1
        assert stats["failed_invocations"] == 1
        assert "average_latency_seconds" in stats
        assert "signature_counts" in stats
