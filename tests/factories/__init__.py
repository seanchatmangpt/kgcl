"""
Factory_boy test fixtures for KGCL.

This module provides comprehensive test data factories following the Chicago School
TDD approach with realistic, production-grade test data.

NOTE
----
Requires factory_boy dependency:
    uv add --dev factory_boy

Factories
---------
- ConditionResultFactory: ConditionResult with metadata
- HookReceiptFactory: HookReceipt with timing and provenance
- HookFactory: Hook with condition and handler
- MerkleAnchorFactory: MerkleAnchor for cryptographic anchoring
- ReceiptFactory: Receipt with JSON-LD and hashing
- TransactionFactory: Transaction with ACID properties
- SparqlAskConditionFactory: SPARQL ASK condition
- ThresholdConditionFactory: Threshold-based condition
- AlwaysTrueConditionFactory: Always-true test condition

Usage
-----
>>> from tests.factories import HookFactory, ConditionResultFactory
>>> hook = HookFactory(name="test-hook", priority=90)
>>> result = ConditionResultFactory(triggered=True)
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

import factory
from factory import Faker, LazyAttribute, LazyFunction, SubFactory

from kgcl.hooks.conditions import AlwaysTrueCondition, ConditionResult
from kgcl.hooks.core import Hook, HookReceipt
from kgcl.hooks.receipts import MerkleAnchor, Receipt
from kgcl.hooks.transaction import Transaction, TransactionState
from kgcl.hooks.value_objects import HookName

# ============================================================================
# Condition Factories
# ============================================================================


class ConditionResultFactory(factory.Factory):
    """
    Factory for ConditionResult.

    Creates realistic condition evaluation results with metadata.

    Examples
    --------
    >>> result = ConditionResultFactory(triggered=True)
    >>> assert result.triggered is True
    >>> result = ConditionResultFactory(metadata={"count": 42})
    """

    class Meta:
        model = ConditionResult

    triggered = Faker("boolean", chance_of_getting_true=70)
    metadata = LazyFunction(dict)


class AlwaysTrueConditionFactory(factory.Factory):
    """
    Factory for AlwaysTrueCondition.

    Creates test conditions that always trigger.

    Examples
    --------
    >>> condition = AlwaysTrueConditionFactory()
    >>> result = await condition.evaluate({})
    >>> assert result.triggered is True
    """

    class Meta:
        model = AlwaysTrueCondition


# ============================================================================
# Hook Factories
# ============================================================================


def _default_hook_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Default test handler that logs context and returns success."""
    return {
        "status": "success",
        "processed": True,
        "context_keys": list(context.keys()),
    }


class HookFactory(factory.Factory):
    """
    Factory for Hook.

    Creates realistic hooks with conditions and handlers.

    Examples
    --------
    >>> hook = HookFactory(name="delta-monitor", priority=90)
    >>> assert hook.name == "delta-monitor"
    >>> assert hook.priority == 90
    >>> assert hook.enabled is True
    """

    class Meta:
        model = Hook

    name = LazyAttribute(lambda _: HookName.new(f"hook-{uuid.uuid4()}"))
    description = Faker("sentence", nb_words=6)
    condition = SubFactory(AlwaysTrueConditionFactory)
    handler = LazyFunction(lambda: _default_hook_handler)
    priority = Faker("random_int", min=0, max=100)
    timeout = 30.0
    enabled = True
    actor = Faker("user_name")
    metadata = LazyFunction(dict)


class HookReceiptFactory(factory.Factory):
    """
    Factory for HookReceipt.

    Creates realistic hook execution receipts with timing, provenance, and errors.

    Examples
    --------
    >>> receipt = HookReceiptFactory(error=None)
    >>> assert receipt.error is None
    >>> assert receipt.duration_ms > 0
    >>> failed_receipt = HookReceiptFactory(
    ...     error="Handler timeout", handler_result=None
    ... )
    >>> assert failed_receipt.error == "Handler timeout"
    """

    class Meta:
        model = HookReceipt

    hook_id = LazyAttribute(lambda _: HookName.new(f"hook-{uuid.uuid4()}"))
    timestamp = LazyFunction(lambda: datetime.now(UTC))
    condition_result = SubFactory(ConditionResultFactory, triggered=True)
    handler_result = LazyFunction(
        lambda: {"status": "success", "result": {"key": "value"}}
    )
    duration_ms = Faker("pyfloat", min_value=1.0, max_value=5000.0, right_digits=2)
    actor = Faker("user_name")
    error = None
    stack_trace = None
    memory_delta_bytes = Faker("random_int", min=0, max=1024 * 1024)
    input_context = LazyFunction(
        lambda: {"event": "test", "timestamp": datetime.now(UTC)}
    )
    metadata = LazyFunction(dict)
    receipt_id = LazyAttribute(lambda _: str(uuid.uuid4()))
    max_size_bytes = None
    merkle_anchor = None


# ============================================================================
# Receipt & Provenance Factories
# ============================================================================


class MerkleAnchorFactory(factory.Factory):
    """
    Factory for MerkleAnchor.

    Creates realistic Merkle anchors for cryptographic provenance.

    Examples
    --------
    >>> anchor = MerkleAnchorFactory(graph_version=42)
    >>> assert len(anchor.root_hash) == 64  # SHA256 hex
    >>> assert anchor.graph_version == 42
    """

    class Meta:
        model = MerkleAnchor

    root_hash = LazyAttribute(lambda _: hashlib.sha256(uuid.uuid4().bytes).hexdigest())
    graph_version = Faker("random_int", min=1, max=10000)
    timestamp = LazyFunction(lambda: datetime.now(UTC))


class ReceiptFactory(factory.Factory):
    """
    Factory for Receipt.

    Creates cryptographically verifiable receipts with hashing and JSON-LD.

    Examples
    --------
    >>> receipt = ReceiptFactory(actor="alice@example.com")
    >>> assert receipt.actor == "alice@example.com"
    >>> hash_val = receipt.compute_hash()
    >>> assert len(hash_val) == 64  # SHA256
    >>> json_ld = receipt.to_json_ld()
    >>> assert json_ld["@type"] == "HookReceipt"
    """

    class Meta:
        model = Receipt

    receipt_id = LazyAttribute(lambda _: str(uuid.uuid4()))
    hook_id = LazyAttribute(lambda _: f"hook-{uuid.uuid4()}")
    timestamp = LazyFunction(lambda: datetime.now(UTC))
    actor = Faker("email")
    condition_result = SubFactory(ConditionResultFactory, triggered=True)
    handler_result = LazyFunction(
        lambda: {"status": "completed", "data": {"key": "value"}}
    )
    duration_ms = Faker("pyfloat", min_value=0.5, max_value=3000.0, right_digits=2)
    error = None
    stack_trace = None
    memory_delta_bytes = Faker("random_int", min=0, max=2 * 1024 * 1024)
    input_context = LazyFunction(lambda: {"source": "test", "id": str(uuid.uuid4())})
    metadata = LazyFunction(dict)
    max_size_bytes = None
    merkle_anchor = None


# ============================================================================
# Transaction Factories
# ============================================================================


class TransactionFactory(factory.Factory):
    """
    Factory for Transaction.

    Creates ACID transactions with realistic triple changes.

    Examples
    --------
    >>> tx = TransactionFactory(isolation_level="SERIALIZABLE")
    >>> assert tx.state == TransactionState.PENDING
    >>> tx.begin()
    >>> tx.add_triple("urn:s1", "urn:p1", "urn:o1")
    >>> assert len(tx.added_triples) == 1
    >>> tx.commit()
    >>> assert tx.state == TransactionState.COMMITTED
    """

    class Meta:
        model = Transaction

    tx_id = LazyAttribute(lambda _: str(uuid.uuid4()))
    state = TransactionState.PENDING
    added_triples = LazyFunction(list)
    removed_triples = LazyFunction(list)
    started_at = LazyFunction(lambda: datetime.now(UTC))
    completed_at = None
    metadata = LazyFunction(dict)
    isolation_level = "READ_COMMITTED"


# ============================================================================
# Specialized Hook Factories
# ============================================================================


class HighPriorityHookFactory(HookFactory):
    """
    Factory for high-priority hooks.

    Examples
    --------
    >>> hook = HighPriorityHookFactory()
    >>> assert hook.priority >= 80
    """

    priority = Faker("random_int", min=80, max=100)
    timeout = 10.0  # High priority = stricter timeout


class LowPriorityHookFactory(HookFactory):
    """
    Factory for low-priority hooks.

    Examples
    --------
    >>> hook = LowPriorityHookFactory()
    >>> assert hook.priority <= 30
    """

    priority = Faker("random_int", min=0, max=30)
    timeout = 60.0  # Low priority = relaxed timeout


class DisabledHookFactory(HookFactory):
    """
    Factory for disabled hooks.

    Examples
    --------
    >>> hook = DisabledHookFactory()
    >>> assert hook.enabled is False
    """

    enabled = False


class FailedHookReceiptFactory(HookReceiptFactory):
    """
    Factory for failed hook receipts.

    Examples
    --------
    >>> receipt = FailedHookReceiptFactory()
    >>> assert receipt.error is not None
    >>> assert receipt.handler_result is None
    """

    error = Faker("sentence", nb_words=5)
    handler_result = None
    stack_trace = LazyAttribute(
        lambda _: "Traceback (most recent call last):\n"
        '  File "<test>", line 1, in <module>\n'
        "SomeError: Test error occurred"
    )


class LargeContextHookReceiptFactory(HookReceiptFactory):
    """
    Factory for receipts with large context (for testing truncation).

    Examples
    --------
    >>> receipt = LargeContextHookReceiptFactory(max_size_bytes=1024)
    >>> # Large handler_result triggers truncation logic
    """

    handler_result = LazyFunction(
        lambda: {"large_data": "x" * 10000, "status": "success"}  # 10KB+ result
    )


class TransactionWithChangesFactory(TransactionFactory):
    """
    Factory for transactions with pre-populated changes.

    Examples
    --------
    >>> tx = TransactionWithChangesFactory()
    >>> assert len(tx.added_triples) > 0
    >>> assert len(tx.removed_triples) > 0
    """

    added_triples = LazyFunction(
        lambda: [
            (f"urn:s{i}", "urn:p:created", f"urn:o{i}")
            for i in range(3)  # Fixed count for predictable tests
        ]
    )
    removed_triples = LazyFunction(
        lambda: [
            (f"urn:s{i}", "urn:p:deleted", f"urn:o{i}")
            for i in range(2)  # Fixed count for predictable tests
        ]
    )


class CommittedTransactionFactory(TransactionFactory):
    """
    Factory for committed transactions.

    Examples
    --------
    >>> tx = CommittedTransactionFactory()
    >>> assert tx.state == TransactionState.COMMITTED
    >>> assert tx.completed_at is not None
    """

    state = TransactionState.COMMITTED
    completed_at = LazyFunction(lambda: datetime.now(UTC))


class RolledBackTransactionFactory(TransactionFactory):
    """
    Factory for rolled-back transactions.

    Examples
    --------
    >>> tx = RolledBackTransactionFactory()
    >>> assert tx.state == TransactionState.ROLLED_BACK
    >>> assert tx.completed_at is not None
    """

    state = TransactionState.ROLLED_BACK
    completed_at = LazyFunction(lambda: datetime.now(UTC))
    added_triples = LazyFunction(list)  # Cleared on rollback
    removed_triples = LazyFunction(list)


__all__ = [
    "AlwaysTrueConditionFactory",
    "CommittedTransactionFactory",
    "ConditionResultFactory",
    "DisabledHookFactory",
    "FailedHookReceiptFactory",
    "HighPriorityHookFactory",
    "HookFactory",
    "HookReceiptFactory",
    "LargeContextHookReceiptFactory",
    "LowPriorityHookFactory",
    "MerkleAnchorFactory",
    "ReceiptFactory",
    "RolledBackTransactionFactory",
    "TransactionFactory",
    "TransactionWithChangesFactory",
]
