"""
Unit tests for receipt generation.
"""

import time
from datetime import datetime

import pytest
from rdflib import Graph
from rdflib.namespace import RDF

from kgcl.dspy_runtime.receipts import DSPY, Receipt, ReceiptGenerator


class TestReceipt:
    """Test Receipt dataclass."""

    def test_create_success_receipt(self):
        """Test creating successful receipt."""
        receipt = Receipt(
            receipt_id="test-123",
            timestamp=time.time(),
            signature_name="TestSignature",
            module_path="/path/to/module.py",
            inputs={"input": "value"},
            outputs={"output": "result"},
            success=True,
            latency_seconds=1.5,
        )

        assert receipt.success is True
        assert receipt.receipt_id == "test-123"
        assert receipt.latency_seconds == 1.5

    def test_create_error_receipt(self):
        """Test creating error receipt."""
        receipt = Receipt(
            receipt_id="error-456",
            timestamp=time.time(),
            signature_name="TestSignature",
            module_path="/path/to/module.py",
            inputs={"input": "value"},
            outputs={},
            success=False,
            error="Something went wrong",
        )

        assert receipt.success is False
        assert receipt.error == "Something went wrong"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        receipt = Receipt(
            receipt_id="dict-test",
            timestamp=time.time(),
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=True,
        )

        receipt_dict = receipt.to_dict()
        assert "receipt_id" in receipt_dict
        assert "timestamp" in receipt_dict
        assert "success" in receipt_dict

    def test_datetime_property(self):
        """Test datetime property."""
        ts = time.time()
        receipt = Receipt(
            receipt_id="dt-test",
            timestamp=ts,
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=True,
        )

        dt = receipt.datetime
        assert isinstance(dt, datetime)
        assert dt.timestamp() == pytest.approx(ts)

    def test_uri_property(self):
        """Test URI property."""
        receipt = Receipt(
            receipt_id="uri-test",
            timestamp=time.time(),
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=True,
        )

        uri = receipt.uri
        assert "uri-test" in str(uri)


class TestReceiptGenerator:
    """Test ReceiptGenerator class."""

    def test_init_with_graph(self):
        """Test initialization with provided graph."""
        graph = Graph()
        generator = ReceiptGenerator(graph)

        assert isinstance(generator.graph, Graph)

    def test_init_without_graph(self):
        """Test initialization without graph."""
        generator = ReceiptGenerator()

        assert isinstance(generator.graph, Graph)

    def test_generate_receipt(self):
        """Test generating receipt."""
        generator = ReceiptGenerator()

        receipt = generator.generate_receipt(
            signature_name="TestSignature",
            module_path="/path/to/module.py",
            inputs={"input": "test"},
            outputs={"output": "result"},
            success=True,
            model="llama3.1",
            latency_seconds=2.5,
        )

        assert receipt.signature_name == "TestSignature"
        assert receipt.success is True
        assert receipt.model == "llama3.1"
        assert receipt.latency_seconds == 2.5

    def test_generate_receipt_with_features(self):
        """Test generating receipt with source features."""
        generator = ReceiptGenerator()

        receipt = generator.generate_receipt(
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=True,
            source_features=[
                "http://example.com/feature1",
                "http://example.com/feature2",
            ],
            source_signatures=["http://example.com/sig1"],
        )

        assert len(receipt.source_features) == 2
        assert len(receipt.source_signatures) == 1

    def test_store_receipt(self):
        """Test storing receipt in RDF graph."""
        generator = ReceiptGenerator()

        receipt = Receipt(
            receipt_id="store-test",
            timestamp=time.time(),
            signature_name="TestSig",
            module_path="/path/to/module.py",
            inputs={"input": "value"},
            outputs={"output": "result"},
            success=True,
            model="llama3.1",
            latency_seconds=1.0,
        )

        uri = generator.store_receipt(receipt)

        # Verify receipt stored in graph
        assert (uri, RDF.type, DSPY.Receipt) in generator.graph
        assert len(list(generator.graph.triples((uri, None, None)))) > 0

    def test_store_receipt_with_error(self):
        """Test storing error receipt."""
        generator = ReceiptGenerator()

        receipt = Receipt(
            receipt_id="error-test",
            timestamp=time.time(),
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=False,
            error="Test error message",
        )

        uri = generator.store_receipt(receipt)

        # Verify error stored
        error_value = generator.graph.value(uri, DSPY.error)
        assert error_value is not None
        assert "Test error" in str(error_value)

    def test_get_receipt(self):
        """Test retrieving receipt from graph."""
        generator = ReceiptGenerator()

        # Store receipt
        original = Receipt(
            receipt_id="retrieve-test",
            timestamp=time.time(),
            signature_name="TestSignature",
            module_path="/path/to/module.py",
            inputs={"input": "value"},
            outputs={"output": "result"},
            success=True,
        )
        generator.store_receipt(original)

        # Retrieve receipt
        retrieved = generator.get_receipt("retrieve-test")

        assert retrieved is not None
        assert retrieved.receipt_id == "retrieve-test"
        assert retrieved.signature_name == "TestSignature"
        assert retrieved.success is True

    def test_get_nonexistent_receipt(self):
        """Test retrieving nonexistent receipt."""
        generator = ReceiptGenerator()

        receipt = generator.get_receipt("nonexistent")
        assert receipt is None

    def test_list_receipts_empty(self):
        """Test listing receipts from empty graph."""
        generator = ReceiptGenerator()

        receipts = generator.list_receipts()
        assert receipts == []

    def test_list_receipts(self):
        """Test listing receipts."""
        generator = ReceiptGenerator()

        # Store multiple receipts
        for i in range(5):
            receipt = Receipt(
                receipt_id=f"list-test-{i}",
                timestamp=time.time() + i,
                signature_name=f"Signature{i}",
                module_path="/path",
                inputs={},
                outputs={},
                success=True,
            )
            generator.store_receipt(receipt)

        receipts = generator.list_receipts()
        assert len(receipts) == 5

    def test_list_receipts_with_signature_filter(self):
        """Test listing receipts filtered by signature."""
        generator = ReceiptGenerator()

        # Store receipts with different signatures
        for i in range(3):
            receipt = Receipt(
                receipt_id=f"filter-test-{i}",
                timestamp=time.time(),
                signature_name="SignatureA" if i < 2 else "SignatureB",
                module_path="/path",
                inputs={},
                outputs={},
                success=True,
            )
            generator.store_receipt(receipt)

        receipts = generator.list_receipts(signature_name="SignatureA")
        assert len(receipts) == 2

    def test_list_receipts_with_success_filter(self):
        """Test listing receipts filtered by success status."""
        generator = ReceiptGenerator()

        # Store mix of successful and failed receipts
        for i in range(4):
            receipt = Receipt(
                receipt_id=f"success-filter-{i}",
                timestamp=time.time(),
                signature_name="TestSig",
                module_path="/path",
                inputs={},
                outputs={},
                success=i % 2 == 0,
            )
            generator.store_receipt(receipt)

        successful = generator.list_receipts(success=True)
        failed = generator.list_receipts(success=False)

        assert len(successful) == 2
        assert len(failed) == 2

    def test_list_receipts_with_limit(self):
        """Test listing receipts with limit."""
        generator = ReceiptGenerator()

        # Store many receipts
        for i in range(10):
            receipt = Receipt(
                receipt_id=f"limit-test-{i}",
                timestamp=time.time(),
                signature_name="TestSig",
                module_path="/path",
                inputs={},
                outputs={},
                success=True,
            )
            generator.store_receipt(receipt)

        receipts = generator.list_receipts(limit=5)
        assert len(receipts) == 5

    def test_export_graph(self, tmp_path):
        """Test exporting graph to file."""
        generator = ReceiptGenerator()

        # Store receipt
        receipt = Receipt(
            receipt_id="export-test",
            timestamp=time.time(),
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=True,
        )
        generator.store_receipt(receipt)

        # Export
        output_file = tmp_path / "receipts.ttl"
        generator.export_graph(str(output_file), format="turtle")

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_import_graph(self, tmp_path):
        """Test importing graph from file."""
        # Create and export graph
        generator1 = ReceiptGenerator()
        receipt = Receipt(
            receipt_id="import-test",
            timestamp=time.time(),
            signature_name="TestSig",
            module_path="/path",
            inputs={},
            outputs={},
            success=True,
        )
        generator1.store_receipt(receipt)

        graph_file = tmp_path / "import.ttl"
        generator1.export_graph(str(graph_file))

        # Import into new generator
        generator2 = ReceiptGenerator()
        generator2.import_graph(str(graph_file))

        # Verify receipt imported
        imported_receipt = generator2.get_receipt("import-test")
        assert imported_receipt is not None
        assert imported_receipt.receipt_id == "import-test"

    def test_import_nonexistent_file(self):
        """Test importing from nonexistent file."""
        generator = ReceiptGenerator()

        with pytest.raises(FileNotFoundError):
            generator.import_graph("/nonexistent/file.ttl")
