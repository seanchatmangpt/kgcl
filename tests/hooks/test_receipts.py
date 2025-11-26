"""
Chicago School TDD Tests for Receipt & Provenance System.

Tests define receipt behaviors including cryptographic verification,
RDF serialization, and queryability.
"""

from datetime import UTC, datetime, timedelta

import pytest

from kgcl.hooks.conditions import ConditionResult
from kgcl.hooks.receipts import MerkleAnchor, Receipt, ReceiptStore


class TestReceiptCapture:
    """Test receipt data capture behaviors."""

    def test_receipt_captures_hook_id_timestamp_actor(self):
        """Receipt captures: hookId, timestamp, actor, condition_result, handler_result."""
        timestamp = datetime.now(UTC)
        condition_result = ConditionResult(triggered=True, metadata={"test": "value"})
        handler_result = {"success": True}

        receipt = Receipt(
            hook_id="test_hook",
            timestamp=timestamp,
            actor="test_user",
            condition_result=condition_result,
            handler_result=handler_result,
            duration_ms=150.5,
        )

        assert receipt.hook_id == "test_hook"
        assert receipt.timestamp == timestamp
        assert receipt.actor == "test_user"
        assert receipt.condition_result == condition_result
        assert receipt.handler_result == handler_result

    def test_receipt_includes_duration_and_memory_delta(self):
        """Receipt includes duration_ms and memory_delta."""
        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=250.75,
            memory_delta_bytes=1024,
        )

        assert receipt.duration_ms == 250.75
        assert receipt.memory_delta_bytes == 1024

    def test_receipt_stores_full_input_output(self):
        """Receipt stores full input/output (if reasonable size)."""
        large_input = {"data": "x" * 100}
        large_output = {"result": "y" * 100}

        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result=large_output,
            duration_ms=100.0,
            input_context=large_input,
        )

        assert receipt.input_context == large_input
        assert receipt.handler_result == large_output

    def test_receipt_truncates_oversized_data(self):
        """Receipt truncates data exceeding size limits."""
        huge_data = {"data": "x" * 1_000_000}  # 1MB of data

        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result=huge_data,
            duration_ms=100.0,
            max_size_bytes=10_000,  # 10KB limit
        )

        # Should indicate truncation
        assert receipt.truncated is True
        assert len(str(receipt.handler_result)) < 20_000


class TestReceiptErrorHandling:
    """Test receipt error information capture."""

    def test_receipt_includes_error_information_with_stack_trace(self):
        """Receipt includes error information with stack trace."""
        error_message = "Something went wrong"
        stack_trace = "Traceback (most recent call last):\n  File...\nValueError: error"

        receipt = Receipt(
            hook_id="failing_hook",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result=None,
            duration_ms=50.0,
            error=error_message,
            stack_trace=stack_trace,
        )

        assert receipt.error == error_message
        assert receipt.stack_trace == stack_trace
        assert "ValueError" in receipt.stack_trace


class TestReceiptCryptography:
    """Test receipt cryptographic properties."""

    def test_receipt_is_cryptographically_hashable_sha256(self):
        """Receipt is cryptographically hashable (sha256)."""
        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        hash_value = receipt.compute_hash()

        assert hash_value is not None
        assert len(hash_value) == 64  # SHA256 hex digest is 64 chars

    def test_receipt_hash_is_deterministic(self):
        """Receipt hash is deterministic for same data."""
        timestamp = datetime.now(UTC)
        condition_result = ConditionResult(triggered=True, metadata={"key": "value"})
        receipt_id = "deterministic-id-123"

        receipt1 = Receipt(
            receipt_id=receipt_id,
            hook_id="test",
            timestamp=timestamp,
            condition_result=condition_result,
            handler_result={"result": "value"},
            duration_ms=100.0,
        )

        receipt2 = Receipt(
            receipt_id=receipt_id,
            hook_id="test",
            timestamp=timestamp,
            condition_result=condition_result,
            handler_result={"result": "value"},
            duration_ms=100.0,
        )

        assert receipt1.compute_hash() == receipt2.compute_hash()

    def test_receipt_hash_changes_with_data(self):
        """Receipt hash changes when data changes."""
        timestamp = datetime.now(UTC)

        receipt1 = Receipt(
            hook_id="test1",
            timestamp=timestamp,
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        receipt2 = Receipt(
            hook_id="test2",  # Different hook_id
            timestamp=timestamp,
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        assert receipt1.compute_hash() != receipt2.compute_hash()


class TestMerkleAnchor:
    """Test Merkle tree anchoring behaviors."""

    def test_receipt_contains_merkle_anchor_to_graph_state(self):
        """Receipt contains merkle anchor to graph state."""
        merkle_anchor = MerkleAnchor(root_hash="abc123", graph_version=42, timestamp=datetime.now(UTC))

        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
            merkle_anchor=merkle_anchor,
        )

        assert receipt.merkle_anchor is not None
        assert receipt.merkle_anchor.root_hash == "abc123"
        assert receipt.merkle_anchor.graph_version == 42


class TestReceiptSerialization:
    """Test receipt serialization behaviors."""

    def test_receipt_supports_json_ld_serialization(self):
        """Receipt supports JSON-LD serialization."""
        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            actor="test_user",
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        json_ld = receipt.to_json_ld()

        assert "@context" in json_ld
        assert "@type" in json_ld
        assert json_ld["@type"] == "HookReceipt"
        assert "hookId" in json_ld or "hook_id" in json_ld

    def test_receipt_can_be_deserialized_from_json_ld(self):
        """Receipt can be deserialized from JSON-LD."""
        original = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            actor="test_user",
            condition_result=ConditionResult(triggered=True, metadata={"key": "value"}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        json_ld = original.to_json_ld()
        restored = Receipt.from_json_ld(json_ld)

        assert restored.hook_id == original.hook_id
        assert restored.actor == original.actor
        assert restored.duration_ms == original.duration_ms


class TestReceiptRDFTriples:
    """Test RDF triple generation behaviors."""

    def test_receipt_can_be_stored_as_rdf_triple(self):
        """Receipt can be stored as RDF triple."""
        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            actor="test_user",
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        triples = receipt.to_rdf_triples()

        assert len(triples) > 0
        # Each triple should be (subject, predicate, object)
        for triple in triples:
            assert len(triple) == 3

    def test_rdf_triples_include_provenance_data(self):
        """RDF triples include provenance data."""
        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            actor="test_user",
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        triples = receipt.to_rdf_triples()
        triples_str = "\n".join([str(t) for t in triples])

        # Should contain actor, timestamp, etc.
        assert "test_user" in triples_str or "actor" in triples_str.lower()


class TestReceiptProof:
    """Test receipt proof generation."""

    def test_receipt_provides_proof_that_hook_executed(self):
        """Receipt provides proof that hook executed."""
        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            actor="test_user",
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        proof = receipt.generate_proof()

        assert proof is not None
        assert "hash" in proof
        assert "timestamp" in proof
        assert "hook_id" in proof


class TestReceiptStore:
    """Test receipt storage and querying behaviors."""

    @pytest.mark.asyncio
    async def test_receipt_store_persists_receipts(self):
        """ReceiptStore persists receipts."""
        store = ReceiptStore()

        receipt = Receipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        await store.save(receipt)

        # Should be retrievable
        retrieved = await store.get_by_id(receipt.receipt_id)
        assert retrieved is not None
        assert retrieved.hook_id == "test"

    @pytest.mark.asyncio
    async def test_receipts_are_queryable_by_hook_id(self):
        """Receipts are queryable (filter by hookId, timestamp, actor)."""
        store = ReceiptStore()

        receipt1 = Receipt(
            hook_id="test1",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        receipt2 = Receipt(
            hook_id="test2",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        await store.save(receipt1)
        await store.save(receipt2)

        # Query by hook_id
        results = await store.query(hook_id="test1")
        assert len(results) == 1
        assert results[0].hook_id == "test1"

    @pytest.mark.asyncio
    async def test_receipts_queryable_by_timestamp_range(self):
        """Receipts queryable by timestamp range."""
        store = ReceiptStore()

        now = datetime.now(UTC)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        receipt_old = Receipt(
            hook_id="old",
            timestamp=past,
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        receipt_new = Receipt(
            hook_id="new",
            timestamp=now,
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        await store.save(receipt_old)
        await store.save(receipt_new)

        # Query by timestamp range
        results = await store.query(timestamp_from=now - timedelta(minutes=5), timestamp_to=future)

        assert len(results) == 1
        assert results[0].hook_id == "new"

    @pytest.mark.asyncio
    async def test_receipts_queryable_by_actor(self):
        """Receipts queryable by actor."""
        store = ReceiptStore()

        receipt1 = Receipt(
            hook_id="test1",
            timestamp=datetime.now(UTC),
            actor="user1",
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        receipt2 = Receipt(
            hook_id="test2",
            timestamp=datetime.now(UTC),
            actor="user2",
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        await store.save(receipt1)
        await store.save(receipt2)

        # Query by actor
        results = await store.query(actor="user1")
        assert len(results) == 1
        assert results[0].actor == "user1"
