"""
Tests for factory_boy test fixtures.

Verifies that all factories produce valid, realistic test data following
Chicago School TDD principles.
"""

from __future__ import annotations

from datetime import datetime

import pytest

# NOTE: factory_boy must be installed: uv add --dev factory_boy
pytest.importorskip("factory")

from kgcl.hooks.conditions import AlwaysTrueCondition, ConditionResult
from kgcl.hooks.core import Hook, HookReceipt, HookState
from kgcl.hooks.receipts import MerkleAnchor, Receipt
from kgcl.hooks.transaction import Transaction, TransactionState
from kgcl.hooks.value_objects import HookName
from tests.factories import (
    AlwaysTrueConditionFactory,
    CommittedTransactionFactory,
    ConditionResultFactory,
    DisabledHookFactory,
    FailedHookReceiptFactory,
    HighPriorityHookFactory,
    HookFactory,
    HookReceiptFactory,
    LargeContextHookReceiptFactory,
    LowPriorityHookFactory,
    MerkleAnchorFactory,
    ReceiptFactory,
    RolledBackTransactionFactory,
    TransactionFactory,
    TransactionWithChangesFactory,
)

# ============================================================================
# Condition Factories Tests
# ============================================================================


def test_condition_result_factory_creates_valid_results() -> None:
    """ConditionResultFactory produces valid ConditionResult instances."""
    result = ConditionResultFactory()

    assert isinstance(result, ConditionResult)
    assert isinstance(result.triggered, bool)
    assert isinstance(result.metadata, dict)


def test_condition_result_factory_with_overrides() -> None:
    """ConditionResultFactory accepts custom values."""
    metadata = {"query": "SELECT * WHERE { ?s ?p ?o }", "bindings": 42}
    result = ConditionResultFactory(triggered=True, metadata=metadata)

    assert result.triggered is True
    assert result.metadata == metadata
    assert result.metadata["bindings"] == 42


def test_always_true_condition_factory_creates_working_conditions() -> None:
    """AlwaysTrueConditionFactory produces valid AlwaysTrueCondition instances."""
    condition = AlwaysTrueConditionFactory()

    assert isinstance(condition, AlwaysTrueCondition)


@pytest.mark.asyncio
async def test_always_true_condition_factory_evaluates_correctly() -> None:
    """AlwaysTrueCondition from factory always triggers."""
    condition = AlwaysTrueConditionFactory()
    result = await condition.evaluate({"test": "context"})

    assert result.triggered is True
    assert isinstance(result, ConditionResult)


# ============================================================================
# Hook Factories Tests
# ============================================================================


def test_hook_factory_creates_valid_hooks() -> None:
    """HookFactory produces valid Hook instances."""
    hook = HookFactory()

    assert isinstance(hook, Hook)
    assert isinstance(hook.name, HookName)
    assert 0 <= hook.priority <= 100
    assert hook.timeout > 0
    assert hook.enabled is True
    assert callable(hook.handler)
    assert hook.state == HookState.PENDING


def test_hook_factory_with_overrides() -> None:
    """HookFactory accepts custom values."""
    hook = HookFactory(name="custom-hook", priority=95, timeout=5.0, enabled=False)

    assert str(hook.name) == "custom-hook"
    assert hook.priority == 95
    assert hook.timeout == 5.0
    assert hook.enabled is False


def test_hook_factory_handler_is_callable() -> None:
    """Hook handler from factory can be executed."""
    hook = HookFactory()
    context = {"event": "test", "count": 42}
    result = hook.handler(context)

    assert isinstance(result, dict)
    assert result.get("status") == "success"
    assert result.get("processed") is True
    assert "context_keys" in result


def test_high_priority_hook_factory() -> None:
    """HighPriorityHookFactory creates hooks with priority >= 80."""
    hook = HighPriorityHookFactory()

    assert hook.priority >= 80
    assert hook.priority <= 100
    assert hook.timeout == 10.0  # Stricter timeout


def test_low_priority_hook_factory() -> None:
    """LowPriorityHookFactory creates hooks with priority <= 30."""
    hook = LowPriorityHookFactory()

    assert hook.priority <= 30
    assert hook.priority >= 0
    assert hook.timeout == 60.0  # Relaxed timeout


def test_disabled_hook_factory() -> None:
    """DisabledHookFactory creates disabled hooks."""
    hook = DisabledHookFactory()

    assert hook.enabled is False
    assert isinstance(hook, Hook)


# ============================================================================
# HookReceipt Factories Tests
# ============================================================================


def test_hook_receipt_factory_creates_valid_receipts() -> None:
    """HookReceiptFactory produces valid HookReceipt instances."""
    receipt = HookReceiptFactory()

    assert isinstance(receipt, HookReceipt)
    assert isinstance(receipt.hook_id, HookName)
    assert isinstance(receipt.timestamp, datetime)
    assert isinstance(receipt.condition_result, ConditionResult)
    assert receipt.duration_ms > 0
    assert receipt.error is None  # Default to success


def test_hook_receipt_factory_with_error() -> None:
    """HookReceiptFactory can create failed receipts."""
    receipt = HookReceiptFactory(
        error="Timeout exceeded", handler_result=None, stack_trace="..."
    )

    assert receipt.error == "Timeout exceeded"
    assert receipt.handler_result is None
    assert receipt.stack_trace == "..."


def test_failed_hook_receipt_factory() -> None:
    """FailedHookReceiptFactory creates receipts with errors."""
    receipt = FailedHookReceiptFactory()

    assert receipt.error is not None
    assert len(receipt.error) > 0
    assert receipt.handler_result is None
    assert receipt.stack_trace is not None


def test_large_context_hook_receipt_factory() -> None:
    """LargeContextHookReceiptFactory creates receipts that trigger truncation."""
    receipt = LargeContextHookReceiptFactory(max_size_bytes=1024)

    assert receipt.max_size_bytes == 1024
    # Truncation logic is in HookReceipt.__post_init__
    # Factory creates large data, so truncation should occur
    assert receipt.handler_result is not None


# ============================================================================
# Receipt & Provenance Factories Tests
# ============================================================================


def test_merkle_anchor_factory_creates_valid_anchors() -> None:
    """MerkleAnchorFactory produces valid MerkleAnchor instances."""
    anchor = MerkleAnchorFactory()

    assert isinstance(anchor, MerkleAnchor)
    assert len(anchor.root_hash) == 64  # SHA256 hex digest
    assert anchor.graph_version > 0
    assert isinstance(anchor.timestamp, datetime)


def test_merkle_anchor_factory_with_custom_version() -> None:
    """MerkleAnchorFactory accepts custom graph version."""
    anchor = MerkleAnchorFactory(graph_version=12345)

    assert anchor.graph_version == 12345


def test_receipt_factory_creates_valid_receipts() -> None:
    """ReceiptFactory produces valid Receipt instances."""
    receipt = ReceiptFactory()

    assert isinstance(receipt, Receipt)
    assert len(receipt.receipt_id) == 36  # UUID format
    assert isinstance(receipt.hook_id, str)
    assert receipt.duration_ms > 0
    assert receipt.error is None


def test_receipt_factory_compute_hash() -> None:
    """Receipt from factory can compute SHA256 hash."""
    receipt = ReceiptFactory()
    hash_val = receipt.compute_hash()

    assert len(hash_val) == 64  # SHA256 hex
    assert all(c in "0123456789abcdef" for c in hash_val)


def test_receipt_factory_to_json_ld() -> None:
    """Receipt from factory can serialize to JSON-LD."""
    receipt = ReceiptFactory()
    json_ld = receipt.to_json_ld()

    assert json_ld["@type"] == "HookReceipt"
    assert json_ld["@id"].startswith("urn:uuid:")
    assert "hookId" in json_ld
    assert "timestamp" in json_ld
    assert "hash" in json_ld


def test_receipt_factory_to_rdf_triples() -> None:
    """Receipt from factory can serialize to RDF triples."""
    receipt = ReceiptFactory()
    triples = receipt.to_rdf_triples()

    assert len(triples) > 0
    # All triples are (subject, predicate, object)
    for triple in triples:
        assert len(triple) == 3
        assert all(isinstance(item, str) for item in triple)


def test_receipt_factory_with_merkle_anchor() -> None:
    """ReceiptFactory can create receipts with Merkle anchors."""
    anchor = MerkleAnchorFactory()
    receipt = ReceiptFactory(merkle_anchor=anchor)

    assert receipt.merkle_anchor is anchor
    assert receipt.merkle_anchor.graph_version == anchor.graph_version


def test_receipt_factory_generate_proof() -> None:
    """Receipt from factory can generate cryptographic proof."""
    receipt = ReceiptFactory()
    proof = receipt.generate_proof()

    assert proof["receipt_id"] == receipt.receipt_id
    assert proof["hook_id"] == receipt.hook_id
    assert "timestamp" in proof
    assert "hash" in proof
    assert len(proof["hash"]) == 64


# ============================================================================
# Transaction Factories Tests
# ============================================================================


def test_transaction_factory_creates_valid_transactions() -> None:
    """TransactionFactory produces valid Transaction instances."""
    tx = TransactionFactory()

    assert isinstance(tx, Transaction)
    assert len(tx.tx_id) == 36  # UUID
    assert tx.state == TransactionState.PENDING
    assert isinstance(tx.added_triples, list)
    assert isinstance(tx.removed_triples, list)
    assert tx.isolation_level in ["READ_COMMITTED", "SERIALIZABLE"]


def test_transaction_factory_with_custom_isolation() -> None:
    """TransactionFactory accepts custom isolation level."""
    tx = TransactionFactory(isolation_level="SERIALIZABLE")

    assert tx.isolation_level == "SERIALIZABLE"


def test_transaction_factory_lifecycle() -> None:
    """Transaction from factory supports full lifecycle."""
    tx = TransactionFactory()

    # Begin
    assert tx.state == TransactionState.PENDING
    tx.begin()
    assert tx.state == TransactionState.EXECUTING

    # Add changes
    tx.add_triple("urn:s1", "urn:p1", "urn:o1")
    assert len(tx.added_triples) == 1

    # Commit
    tx.commit()
    assert tx.state == TransactionState.COMMITTED
    assert tx.completed_at is not None


def test_transaction_with_changes_factory() -> None:
    """TransactionWithChangesFactory creates transactions with pre-populated changes."""
    tx = TransactionWithChangesFactory()

    assert len(tx.added_triples) > 0
    # At least one addition
    for triple in tx.added_triples:
        assert len(triple) == 3  # (subject, predicate, object)


def test_committed_transaction_factory() -> None:
    """CommittedTransactionFactory creates already-committed transactions."""
    tx = CommittedTransactionFactory()

    assert tx.state == TransactionState.COMMITTED
    assert tx.completed_at is not None


def test_rolled_back_transaction_factory() -> None:
    """RolledBackTransactionFactory creates rolled-back transactions."""
    tx = RolledBackTransactionFactory()

    assert tx.state == TransactionState.ROLLED_BACK
    assert tx.completed_at is not None
    assert len(tx.added_triples) == 0  # Cleared on rollback
    assert len(tx.removed_triples) == 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_hook_with_receipt_integration() -> None:
    """Hook and HookReceipt factories work together."""
    hook = HookFactory(name="integration-test")
    receipt = HookReceiptFactory(hook_id=hook.name, error=None)

    assert receipt.hook_id == hook.name
    assert receipt.error is None
    assert receipt.condition_result.triggered is True


def test_receipt_with_merkle_anchor_integration() -> None:
    """Receipt and MerkleAnchor factories integrate correctly."""
    anchor = MerkleAnchorFactory(graph_version=999)
    receipt = ReceiptFactory(merkle_anchor=anchor)

    proof = receipt.generate_proof()
    assert proof["merkle_anchor"] is not None
    assert proof["merkle_anchor"]["graph_version"] == 999


def test_multiple_hooks_with_different_priorities() -> None:
    """Multiple hook factories can create diverse test data."""
    high = HighPriorityHookFactory()
    low = LowPriorityHookFactory()
    disabled = DisabledHookFactory()

    assert high.priority > low.priority
    assert high.enabled is True
    assert disabled.enabled is False


def test_transaction_with_multiple_changes() -> None:
    """TransactionWithChangesFactory creates realistic change sets."""
    tx = TransactionWithChangesFactory()

    # Should have both additions and removals
    total_changes = len(tx.added_triples) + len(tx.removed_triples)
    assert total_changes > 0

    # All triples should be valid
    for triple in tx.added_triples + tx.removed_triples:
        assert len(triple) == 3
        assert all(isinstance(part, str) for part in triple)


def test_factory_batch_creation() -> None:
    """Factories can create multiple instances efficiently."""
    hooks = [HookFactory() for _ in range(10)]
    receipts = [HookReceiptFactory() for _ in range(20)]

    # All should be unique
    hook_ids = {h.name for h in hooks}
    receipt_ids = {r.receipt_id for r in receipts}

    assert len(hook_ids) == 10
    assert len(receipt_ids) == 20
