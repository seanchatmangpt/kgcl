"""
UNRDF bridge for DSPy runtime.

Provides external capability interface for UNRDF to invoke DSPy signatures
and generate receipts integrated with the knowledge graph.
"""

import logging
from typing import Any

from opentelemetry import trace
from rdflib import Graph

from .invoker import SignatureInvoker
from .ollama_config import OllamaConfig, OllamaLM
from .receipts import ReceiptGenerator

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class UNRDFBridge:
    """Bridge between UNRDF and DSPy runtime."""

    def __init__(self, ollama_config: OllamaConfig | None = None, rdf_graph: Graph | None = None):
        """
        Initialize UNRDF bridge.

        Args:
            ollama_config: Ollama configuration. If None, loads from environment.
            rdf_graph: RDF graph for receipts. If None, creates new graph.
        """
        self.ollama_config = ollama_config or OllamaConfig.from_env()
        self.ollama_lm: OllamaLM | None = None
        self.invoker: SignatureInvoker | None = None
        self.receipt_generator = ReceiptGenerator(rdf_graph)
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize bridge components.

        Raises
        ------
            RuntimeError: If DSPy or Ollama not available
        """
        if self._initialized:
            return

        try:
            # Initialize Ollama LM
            self.ollama_lm = OllamaLM(self.ollama_config)
            self.ollama_lm.initialize()

            # Initialize invoker
            self.invoker = SignatureInvoker(self.ollama_lm.lm)

            self._initialized = True
            logger.info("UNRDF bridge initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize UNRDF bridge: {e}")
            raise

    def invoke(
        self,
        module_path: str,
        signature_name: str,
        inputs: dict[str, Any],
        source_features: list[str] | None = None,
        source_signatures: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Invoke DSPy signature and generate receipt.

        This is the main external capability interface for UNRDF.

        Args:
            module_path: Path to DSPy signature module
            signature_name: Name of signature class
            inputs: Input field values
            source_features: URIs of source features
            source_signatures: URIs of source signature definitions
            **kwargs: Additional arguments for prediction

        Returns
        -------
            Dictionary with invocation result and receipt
        """
        with tracer.start_as_current_span("unrdf.bridge.invoke") as span:
            span.set_attribute("module_path", module_path)
            span.set_attribute("signature_name", signature_name)
            span.set_attribute("source_feature_count", len(source_features or []))

            # Ensure initialized
            if not self._initialized:
                self.initialize()

            # Invoke signature
            result = self.invoker.invoke_from_module(
                module_path=module_path, signature_name=signature_name, inputs=inputs, **kwargs
            )

            # Generate receipt
            receipt = self.receipt_generator.generate_receipt(
                signature_name=signature_name,
                module_path=module_path,
                inputs=result.inputs,
                outputs=result.outputs,
                success=result.success,
                model=self.ollama_config.model,
                latency_seconds=result.metrics.get("latency_seconds"),
                error=result.error,
                source_features=source_features,
                source_signatures=source_signatures,
                **result.metrics,
            )

            # Store receipt in RDF graph
            receipt_uri = self.receipt_generator.store_receipt(receipt)

            span.set_attribute("success", result.success)
            span.set_attribute("receipt_uri", str(receipt_uri))

            return {
                "result": result.to_dict(),
                "receipt": receipt.to_dict(),
                "receipt_uri": str(receipt_uri),
            }

    def batch_invoke(self, invocations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Invoke multiple signatures in batch.

        Args:
            invocations: List of invocation payloads, each containing:
                - module_path: Path to signature module
                - signature_name: Signature class name
                - inputs: Input values
                - source_features: (optional) Source feature URIs
                - source_signatures: (optional) Source signature URIs

        Returns
        -------
            List of invocation results with receipts
        """
        with tracer.start_as_current_span("unrdf.bridge.batch_invoke") as span:
            span.set_attribute("batch_size", len(invocations))

            results = []

            for i, inv_payload in enumerate(invocations):
                try:
                    result = self.invoke(
                        module_path=inv_payload["module_path"],
                        signature_name=inv_payload["signature_name"],
                        inputs=inv_payload["inputs"],
                        source_features=inv_payload.get("source_features"),
                        source_signatures=inv_payload.get("source_signatures"),
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch invocation {i} failed: {e}", exc_info=True)
                    results.append(
                        {
                            "result": {
                                "success": False,
                                "error": str(e),
                                "inputs": inv_payload.get("inputs", {}),
                            },
                            "receipt": None,
                            "receipt_uri": None,
                        }
                    )

            span.set_attribute("success_count", sum(1 for r in results if r["result"]["success"]))

            return results

    def get_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        """
        Retrieve receipt by ID.

        Args:
            receipt_id: Receipt ID

        Returns
        -------
            Receipt dictionary if found, None otherwise
        """
        receipt = self.receipt_generator.get_receipt(receipt_id)
        return receipt.to_dict() if receipt else None

    def list_receipts(
        self,
        signature_name: str | None = None,
        success: bool | None = None,
        limit: int | None = 100,
    ) -> list[dict[str, Any]]:
        """
        List receipts with optional filters.

        Args:
            signature_name: Filter by signature name
            success: Filter by success status
            limit: Maximum number of receipts

        Returns
        -------
            List of receipt dictionaries
        """
        receipts = self.receipt_generator.list_receipts(
            signature_name=signature_name, success=success, limit=limit
        )
        return [r.to_dict() for r in receipts]

    def export_receipts(self, output_path: str, format: str = "turtle") -> None:
        """
        Export receipt graph to file.

        Args:
            output_path: Output file path
            format: RDF serialization format
        """
        self.receipt_generator.export_graph(output_path, format)
        logger.info(f"Exported receipts to {output_path}")

    def import_receipts(self, input_path: str, format: str = "turtle") -> None:
        """
        Import receipt graph from file.

        Args:
            input_path: Input file path
            format: RDF serialization format
        """
        self.receipt_generator.import_graph(input_path, format)
        logger.info(f"Imported receipts from {input_path}")

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check of bridge components.

        Returns
        -------
            Health check results
        """
        from .ollama_config import health_check as ollama_health_check

        health = ollama_health_check()
        health["bridge_initialized"] = self._initialized
        health["receipt_count"] = len(list(self.receipt_generator.graph.subjects()))

        return health

    def get_stats(self) -> dict[str, Any]:
        """
        Get bridge statistics.

        Returns
        -------
            Statistics dictionary
        """
        receipts = self.receipt_generator.list_receipts()

        total = len(receipts)
        successful = sum(1 for r in receipts if r.success)
        failed = total - successful

        if total > 0:
            avg_latency = sum(r.latency_seconds for r in receipts if r.latency_seconds) / total
        else:
            avg_latency = 0

        # Count by signature
        signature_counts: dict[str, int] = {}
        for receipt in receipts:
            sig = receipt.signature_name
            signature_counts[sig] = signature_counts.get(sig, 0) + 1

        return {
            "total_invocations": total,
            "successful_invocations": successful,
            "failed_invocations": failed,
            "success_rate": successful / total if total > 0 else 0,
            "average_latency_seconds": avg_latency,
            "signature_counts": signature_counts,
            "model": self.ollama_config.model if self.ollama_config else None,
        }
