"""
Receipt generation for DSPy invocations.

Captures invocation metadata, links to source signatures and features,
and stores receipts as RDF nodes in UNRDF graph.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

logger = logging.getLogger(__name__)

# RDF namespaces
KGCL = Namespace("http://kgcl.org/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")
DSPY = Namespace("http://kgcl.org/dspy/")


@dataclass
class Receipt:
    """Receipt for a DSPy invocation."""

    receipt_id: str
    timestamp: float
    signature_name: str
    module_path: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    success: bool

    # Metadata
    model: str | None = None
    latency_seconds: float | None = None
    token_count: int | None = None
    error: str | None = None

    # Links
    source_features: list[str] = field(default_factory=list)
    source_signatures: list[str] = field(default_factory=list)

    # Additional metrics
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @property
    def datetime(self) -> datetime:
        """Get timestamp as datetime."""
        return datetime.fromtimestamp(self.timestamp)

    @property
    def uri(self) -> URIRef:
        """Get RDF URI for this receipt."""
        return DSPY[f"receipt/{self.receipt_id}"]


class ReceiptGenerator:
    """Generates and stores receipts for DSPy invocations."""

    def __init__(self, graph: Graph | None = None):
        """
        Initialize receipt generator.

        Args:
            graph: RDF graph for storing receipts. If None, creates new graph.
        """
        self.graph = graph or Graph()
        self._bind_namespaces()

    def _bind_namespaces(self) -> None:
        """Bind RDF namespaces to graph."""
        self.graph.bind("kgcl", KGCL)
        self.graph.bind("prov", PROV)
        self.graph.bind("dspy", DSPY)

    def generate_receipt(
        self,
        signature_name: str,
        module_path: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        success: bool,
        model: str | None = None,
        latency_seconds: float | None = None,
        error: str | None = None,
        source_features: list[str] | None = None,
        source_signatures: list[str] | None = None,
        **metrics,
    ) -> Receipt:
        """
        Generate receipt for invocation.

        Args:
            signature_name: Name of DSPy signature
            module_path: Path to signature module
            inputs: Input values
            outputs: Output values
            success: Whether invocation succeeded
            model: Model name used
            latency_seconds: Execution latency
            error: Error message if failed
            source_features: Source feature URIs
            source_signatures: Source signature URIs
            **metrics: Additional metrics

        Returns
        -------
            Generated receipt
        """
        receipt_id = f"{signature_name}_{int(time.time() * 1000)}"
        timestamp = time.time()

        receipt = Receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            signature_name=signature_name,
            module_path=module_path,
            inputs=inputs,
            outputs=outputs,
            success=success,
            model=model,
            latency_seconds=latency_seconds,
            error=error,
            source_features=source_features or [],
            source_signatures=source_signatures or [],
            metrics=metrics,
        )

        logger.info(f"Generated receipt: {receipt_id}")
        return receipt

    def store_receipt(self, receipt: Receipt) -> URIRef:
        """
        Store receipt as RDF in graph.

        Args:
            receipt: Receipt to store

        Returns
        -------
            URI of stored receipt
        """
        uri = receipt.uri

        # Basic receipt properties
        self.graph.add((uri, RDF.type, DSPY.Receipt))
        self.graph.add((uri, RDFS.label, Literal(receipt.receipt_id)))
        self.graph.add((uri, DSPY.signatureName, Literal(receipt.signature_name)))
        self.graph.add((uri, DSPY.modulePath, Literal(receipt.module_path)))
        self.graph.add((uri, DSPY.success, Literal(receipt.success, datatype=XSD.boolean)))
        self.graph.add(
            (uri, PROV.generatedAtTime, Literal(receipt.datetime, datatype=XSD.dateTime))
        )

        # Model and metrics
        if receipt.model:
            self.graph.add((uri, DSPY.model, Literal(receipt.model)))

        if receipt.latency_seconds is not None:
            self.graph.add(
                (uri, DSPY.latencySeconds, Literal(receipt.latency_seconds, datatype=XSD.float))
            )

        if receipt.token_count is not None:
            self.graph.add(
                (uri, DSPY.tokenCount, Literal(receipt.token_count, datatype=XSD.integer))
            )

        if receipt.error:
            self.graph.add((uri, DSPY.error, Literal(receipt.error)))

        # Inputs and outputs as JSON
        self.graph.add((uri, DSPY.inputs, Literal(json.dumps(receipt.inputs))))
        self.graph.add((uri, DSPY.outputs, Literal(json.dumps(receipt.outputs))))

        # Links to source features
        for feature_uri in receipt.source_features:
            self.graph.add((uri, PROV.wasDerivedFrom, URIRef(feature_uri)))

        # Links to source signatures
        for sig_uri in receipt.source_signatures:
            self.graph.add((uri, DSPY.usedSignature, URIRef(sig_uri)))

        # Additional metrics
        for key, value in receipt.metrics.items():
            metric_uri = DSPY[f"metric/{key}"]
            self.graph.add((uri, metric_uri, Literal(value)))

        logger.info(f"Stored receipt in RDF graph: {uri}")
        return uri

    def get_receipt(self, receipt_id: str) -> Receipt | None:
        """
        Retrieve receipt from graph.

        Args:
            receipt_id: Receipt ID

        Returns
        -------
            Receipt if found, None otherwise
        """
        uri = DSPY[f"receipt/{receipt_id}"]

        # Check if receipt exists
        if (uri, RDF.type, DSPY.Receipt) not in self.graph:
            return None

        # Extract properties
        def get_value(predicate, default=None):
            obj = self.graph.value(uri, predicate)
            return obj.toPython() if obj else default

        signature_name = get_value(DSPY.signatureName, "")
        module_path = get_value(DSPY.modulePath, "")
        success = get_value(DSPY.success, False)
        timestamp_dt = get_value(PROV.generatedAtTime)
        timestamp = timestamp_dt.timestamp() if timestamp_dt else time.time()

        inputs_json = get_value(DSPY.inputs, "{}")
        outputs_json = get_value(DSPY.outputs, "{}")

        try:
            inputs = json.loads(inputs_json)
            outputs = json.loads(outputs_json)
        except json.JSONDecodeError:
            inputs = {}
            outputs = {}

        # Get source features and signatures
        source_features = [str(obj) for obj in self.graph.objects(uri, PROV.wasDerivedFrom)]
        source_signatures = [str(obj) for obj in self.graph.objects(uri, DSPY.usedSignature)]

        receipt = Receipt(
            receipt_id=receipt_id,
            timestamp=timestamp,
            signature_name=signature_name,
            module_path=module_path,
            inputs=inputs,
            outputs=outputs,
            success=success,
            model=get_value(DSPY.model),
            latency_seconds=get_value(DSPY.latencySeconds),
            token_count=get_value(DSPY.tokenCount),
            error=get_value(DSPY.error),
            source_features=source_features,
            source_signatures=source_signatures,
        )

        logger.debug(f"Retrieved receipt from graph: {receipt_id}")
        return receipt

    def list_receipts(
        self,
        signature_name: str | None = None,
        success: bool | None = None,
        limit: int | None = None,
    ) -> list[Receipt]:
        """
        List receipts from graph.

        Args:
            signature_name: Filter by signature name
            success: Filter by success status
            limit: Maximum number of receipts to return

        Returns
        -------
            List of receipts
        """
        receipts = []

        for uri in self.graph.subjects(RDF.type, DSPY.Receipt):
            # Extract receipt ID from URI
            receipt_id = str(uri).split("/")[-1]
            receipt = self.get_receipt(receipt_id)

            if receipt is None:
                continue

            # Apply filters
            if signature_name and receipt.signature_name != signature_name:
                continue

            if success is not None and receipt.success != success:
                continue

            receipts.append(receipt)

            if limit and len(receipts) >= limit:
                break

        # Sort by timestamp descending
        receipts.sort(key=lambda r: r.timestamp, reverse=True)

        return receipts

    def export_graph(self, output_path: str, format: str = "turtle") -> None:
        """
        Export RDF graph to file.

        Args:
            output_path: Output file path
            format: RDF serialization format (turtle, xml, json-ld)
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        self.graph.serialize(destination=str(output_file), format=format)
        logger.info(f"Exported {len(self.graph)} triples to {output_path}")

    def import_graph(self, input_path: str, format: str = "turtle") -> None:
        """
        Import RDF graph from file.

        Args:
            input_path: Input file path
            format: RDF serialization format (turtle, xml, json-ld)
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Graph file not found: {input_path}")

        self.graph.parse(str(input_file), format=format)
        logger.info(f"Imported graph from {input_path}")
