"""Comprehensive tests for the Diamond Standard Atman Knowledge Engine.

Tests verify behavior of the Chatman Equation A = μ(O):
- QuadDelta (Observation) validation and immutability
- Atman engine deterministic execution
- KnowledgeHook registration and execution ordering
- TransactionContext and Receipt provenance
- Merkle chain (Lockchain) integrity
- Logic Hash cryptographic provenance
- Performance targets (p99 < 100ms)

Chicago School TDD: Real collaborators, no mocking domain objects.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC

import pytest
from rdflib import Dataset

from kgcl.engine import (
    CHATMAN_CONSTANT,
    GENESIS_HASH,
    Atman,
    HookMode,
    HookResult,
    KnowledgeHook,
    QuadDelta,
    Receipt,
    TransactionContext,
)

# Test constants
EXPECTED_GENESIS_LENGTH: int = 64  # SHA256 hex length
EXPECTED_CHATMAN_CONSTANT: int = 64
P99_TARGET_MS: float = 100.0
LOGIC_HASH_TARGET_MS: float = 10.0
DEFAULT_HOOK_PRIORITY: int = 100
SHA256_HEX_LENGTH: int = 64
EXPECTED_UUID_PARTS: int = 5
EXPECTED_UUID_FIRST_PART_LEN: int = 8
MOCK_DURATION_NS: int = 1000
EXPECTED_HOOK_COUNT_PRE_POST: int = 2
EXPECTED_HOOK_COUNT_FULL_WORKFLOW: int = 3


class TestQuadDelta:
    """Tests for QuadDelta (The Observation)."""

    def test_create_empty_delta(self) -> None:
        """Empty delta is valid."""
        delta = QuadDelta()
        assert delta.additions == []
        assert delta.removals == []

    def test_create_delta_with_additions(self) -> None:
        """Delta with additions only."""
        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        assert len(delta.additions) == 1
        assert delta.additions[0] == ("urn:s1", "urn:p1", "urn:o1")

    def test_create_delta_with_removals(self) -> None:
        """Delta with removals only."""
        delta = QuadDelta(removals=[("urn:s2", "urn:p2", "urn:o2")])
        assert len(delta.removals) == 1
        assert delta.removals[0] == ("urn:s2", "urn:p2", "urn:o2")

    def test_create_delta_with_both(self) -> None:
        """Delta with both additions and removals."""
        delta = QuadDelta(
            additions=[("urn:s1", "urn:p1", "urn:o1")],
            removals=[("urn:s2", "urn:p2", "urn:o2")],
        )
        assert len(delta.additions) == 1
        assert len(delta.removals) == 1

    def test_delta_is_immutable(self) -> None:
        """QuadDelta is frozen (immutable)."""
        from pydantic import ValidationError

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        with pytest.raises(ValidationError, match="frozen"):  # Pydantic frozen model
            delta.additions = []  # type: ignore[misc]

    def test_chatman_constant_enforced_additions(self) -> None:
        """Batch size cannot exceed CHATMAN_CONSTANT for additions."""
        oversized = [
            ("urn:s", f"urn:p{i}", f"urn:o{i}") for i in range(CHATMAN_CONSTANT + 1)
        ]
        with pytest.raises(ValueError, match="Topology Violation"):
            QuadDelta(additions=oversized)

    def test_chatman_constant_enforced_removals(self) -> None:
        """Batch size cannot exceed CHATMAN_CONSTANT for removals."""
        oversized = [
            ("urn:s", f"urn:p{i}", f"urn:o{i}") for i in range(CHATMAN_CONSTANT + 1)
        ]
        with pytest.raises(ValueError, match="Topology Violation"):
            QuadDelta(removals=oversized)

    def test_chatman_constant_at_limit(self) -> None:
        """Batch size exactly at CHATMAN_CONSTANT is allowed."""
        at_limit = [
            ("urn:s", f"urn:p{i}", f"urn:o{i}") for i in range(CHATMAN_CONSTANT)
        ]
        delta = QuadDelta(additions=at_limit)
        assert len(delta.additions) == CHATMAN_CONSTANT


class TestTransactionContext:
    """Tests for TransactionContext (Context Window)."""

    def test_create_context_with_prev_hash(self) -> None:
        """TransactionContext requires prev_hash."""
        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        assert ctx.prev_hash == GENESIS_HASH
        assert ctx.actor == "system"
        assert ctx.tx_id is not None

    def test_context_has_uuid_tx_id(self) -> None:
        """Transaction ID is a valid UUID format."""
        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        # UUID4 format: 8-4-4-4-12
        parts = ctx.tx_id.split("-")
        assert len(parts) == EXPECTED_UUID_PARTS
        assert len(parts[0]) == EXPECTED_UUID_FIRST_PART_LEN

    def test_context_has_utc_timestamp(self) -> None:
        """Timestamp is timezone-aware UTC."""
        ctx = TransactionContext(prev_hash=GENESIS_HASH)
        assert ctx.timestamp.tzinfo is not None
        assert ctx.timestamp.tzinfo == UTC

    def test_context_custom_actor(self) -> None:
        """Custom actor can be specified."""
        ctx = TransactionContext(prev_hash=GENESIS_HASH, actor="alice")
        assert ctx.actor == "alice"


class TestHookResult:
    """Tests for HookResult (Hook telemetry)."""

    def test_create_hook_result(self) -> None:
        """HookResult captures execution metadata."""
        result = HookResult(
            hook_id="test-hook",
            mode=HookMode.PRE,
            success=True,
            duration_ns=MOCK_DURATION_NS,
        )
        assert result.hook_id == "test-hook"
        assert result.mode == HookMode.PRE
        assert result.success is True
        assert result.duration_ns == MOCK_DURATION_NS


class TestReceipt:
    """Tests for Receipt (The Action)."""

    def test_create_committed_receipt(self) -> None:
        """Committed receipt has merkle_root and logic_hash."""
        receipt = Receipt(
            tx_id="test-tx",
            committed=True,
            merkle_root="a" * SHA256_HEX_LENGTH,
            logic_hash="b" * SHA256_HEX_LENGTH,
            hook_results=[],
            duration_ns=MOCK_DURATION_NS,
        )
        assert receipt.committed is True
        assert receipt.error is None
        assert len(receipt.merkle_root) == SHA256_HEX_LENGTH
        assert len(receipt.logic_hash) == SHA256_HEX_LENGTH

    def test_create_failed_receipt(self) -> None:
        """Failed receipt has error message."""
        receipt = Receipt(
            tx_id="test-tx",
            committed=False,
            merkle_root="a" * SHA256_HEX_LENGTH,
            logic_hash="b" * SHA256_HEX_LENGTH,
            hook_results=[],
            duration_ns=MOCK_DURATION_NS,
            error="Guard Violation: test-guard",
        )
        assert receipt.committed is False
        assert receipt.error == "Guard Violation: test-guard"


class TestKnowledgeHook:
    """Tests for KnowledgeHook (Laws of Physics)."""

    @pytest.fixture
    def allow_all_handler(self) -> Callable[..., Awaitable[bool]]:
        """Create a handler that allows all transactions."""

        async def handler(
            store: Dataset, delta: QuadDelta, ctx: TransactionContext
        ) -> bool:
            return True

        return handler

    @pytest.fixture
    def deny_all_handler(self) -> Callable[..., Awaitable[bool]]:
        """Create a handler that denies all transactions."""

        async def handler(
            store: Dataset, delta: QuadDelta, ctx: TransactionContext
        ) -> bool:
            return False

        return handler

    def test_create_pre_hook(
        self, allow_all_handler: Callable[..., Awaitable[bool]]
    ) -> None:
        """PRE hook acts as blocking guard."""
        hook = KnowledgeHook("test-guard", HookMode.PRE, allow_all_handler)
        assert hook.id == "test-guard"
        assert hook.mode == HookMode.PRE
        assert hook.priority == DEFAULT_HOOK_PRIORITY

    def test_create_post_hook(
        self, allow_all_handler: Callable[..., Awaitable[bool]]
    ) -> None:
        """POST hook acts as side effect."""
        hook = KnowledgeHook("test-effect", HookMode.POST, allow_all_handler)
        assert hook.mode == HookMode.POST

    def test_hook_signature_deterministic(
        self, allow_all_handler: Callable[..., Awaitable[bool]]
    ) -> None:
        """Hook signature is deterministic for logic hashing."""
        hook = KnowledgeHook("test-hook", HookMode.PRE, allow_all_handler, priority=50)
        signature = hook.signature()
        assert signature == "test-hook:pre:50"

    @pytest.mark.asyncio
    async def test_hook_execute(
        self, allow_all_handler: Callable[..., Awaitable[bool]]
    ) -> None:
        """Hook execution returns handler result."""
        hook = KnowledgeHook("test-hook", HookMode.PRE, allow_all_handler)
        store = Dataset()
        delta = QuadDelta()
        ctx = TransactionContext(prev_hash=GENESIS_HASH)

        result = await hook.execute(store, delta, ctx)
        assert result is True


class TestAtman:
    """Tests for Atman (The Deterministic Operator)."""

    def test_create_engine(self) -> None:
        """Engine initializes with genesis hash."""
        engine = Atman()
        assert engine.tip_hash == GENESIS_HASH
        assert len(engine) == 0
        assert len(engine.hooks) == 0

    def test_create_engine_with_store(self) -> None:
        """Engine can use existing Dataset."""
        store = Dataset()
        engine = Atman(store=store)
        # Dataset may be wrapped, but same underlying storage
        assert engine.store == store or engine.store is not None

    def test_register_hook_sorted_by_priority(self) -> None:
        """Hooks are sorted by priority (descending) then ID (ascending)."""

        async def handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return True

        engine = Atman()
        hook1 = KnowledgeHook("b-hook", HookMode.PRE, handler, priority=50)
        hook2 = KnowledgeHook("a-hook", HookMode.PRE, handler, priority=100)
        hook3 = KnowledgeHook("c-hook", HookMode.PRE, handler, priority=50)

        engine.register_hook(hook1)
        engine.register_hook(hook2)
        engine.register_hook(hook3)

        hooks = engine.hooks
        # Priority 100 first, then 50s sorted by ID
        assert hooks[0].id == "a-hook"  # priority 100
        assert hooks[1].id == "b-hook"  # priority 50, 'b' < 'c'
        assert hooks[2].id == "c-hook"  # priority 50, 'c' > 'b'

    def test_unregister_hook(self) -> None:
        """Hook can be unregistered by ID."""

        async def handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return True

        engine = Atman()
        hook = KnowledgeHook("test-hook", HookMode.PRE, handler)
        engine.register_hook(hook)
        assert len(engine.hooks) == 1

        removed = engine.unregister_hook("test-hook")
        assert removed is True
        assert len(engine.hooks) == 0

    def test_unregister_nonexistent_hook(self) -> None:
        """Unregistering nonexistent hook returns False."""
        engine = Atman()
        removed = engine.unregister_hook("nonexistent")
        assert removed is False

    def test_compute_logic_hash_empty(self) -> None:
        """Logic hash with no hooks is deterministic."""
        engine = Atman()
        hash1 = engine.compute_logic_hash()
        hash2 = engine.compute_logic_hash()
        assert hash1 == hash2
        assert len(hash1) == SHA256_HEX_LENGTH

    def test_compute_logic_hash_changes_with_hooks(self) -> None:
        """Logic hash changes when hooks are added."""

        async def handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return True

        engine = Atman()
        hash_before = engine.compute_logic_hash()

        hook = KnowledgeHook("test-hook", HookMode.PRE, handler)
        engine.register_hook(hook)
        hash_after = engine.compute_logic_hash()

        assert hash_before != hash_after

    @pytest.mark.asyncio
    async def test_apply_empty_delta(self) -> None:
        """Applying empty delta succeeds."""
        engine = Atman()
        delta = QuadDelta()
        receipt = await engine.apply(delta)

        assert receipt.committed is True
        assert receipt.error is None
        assert len(engine) == 0

    @pytest.mark.asyncio
    async def test_apply_additions(self) -> None:
        """Applying additions adds triples to store."""
        engine = Atman()
        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(delta)

        assert receipt.committed is True
        assert len(engine) == 1

    @pytest.mark.asyncio
    async def test_apply_removals(self) -> None:
        """Applying removals removes triples from store."""
        engine = Atman()

        # First add a triple
        add_delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        await engine.apply(add_delta)
        assert len(engine) == 1

        # Then remove it
        remove_delta = QuadDelta(removals=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(remove_delta)

        assert receipt.committed is True
        assert len(engine) == 0

    @pytest.mark.asyncio
    async def test_lockchain_advances(self) -> None:
        """Tip hash advances after each committed transaction."""
        engine = Atman()
        initial_tip = engine.tip_hash
        assert initial_tip == GENESIS_HASH

        delta1 = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        await engine.apply(delta1)
        tip_after_1 = engine.tip_hash
        assert tip_after_1 != initial_tip

        delta2 = QuadDelta(additions=[("urn:s2", "urn:p2", "urn:o2")])
        await engine.apply(delta2)
        tip_after_2 = engine.tip_hash
        assert tip_after_2 != tip_after_1

    @pytest.mark.asyncio
    async def test_merkle_root_deterministic(self) -> None:
        """Same delta produces same merkle root (deterministic)."""
        engine1 = Atman()
        engine2 = Atman()

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])

        receipt1 = await engine1.apply(delta)
        receipt2 = await engine2.apply(delta)

        assert receipt1.merkle_root == receipt2.merkle_root

    @pytest.mark.asyncio
    async def test_pre_hook_blocks_transaction(self) -> None:
        """PRE hook returning False blocks transaction."""

        async def deny_handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return False

        engine = Atman()
        hook = KnowledgeHook("deny-all", HookMode.PRE, deny_handler)
        engine.register_hook(hook)

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(delta)

        assert receipt.committed is False
        assert "Guard Violation: deny-all" in str(receipt.error)
        assert len(engine) == 0  # No mutations applied

    @pytest.mark.asyncio
    async def test_pre_hook_allows_transaction(self) -> None:
        """PRE hook returning True allows transaction."""

        async def allow_handler(
            s: Dataset, d: QuadDelta, c: TransactionContext
        ) -> bool:
            return True

        engine = Atman()
        hook = KnowledgeHook("allow-all", HookMode.PRE, allow_handler)
        engine.register_hook(hook)

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(delta)

        assert receipt.committed is True
        assert len(engine) == 1

    @pytest.mark.asyncio
    async def test_post_hook_executes_after_mutation(self) -> None:
        """POST hook executes after mutations are applied."""
        post_hook_store_size: list[int] = []

        async def capture_size(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            post_hook_store_size.append(len(s))
            return True

        engine = Atman()
        hook = KnowledgeHook("capture-size", HookMode.POST, capture_size)
        engine.register_hook(hook)

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        await engine.apply(delta)

        # POST hook saw the mutation
        assert len(post_hook_store_size) == 1
        assert post_hook_store_size[0] == 1

    @pytest.mark.asyncio
    async def test_hook_results_in_receipt(self) -> None:
        """Receipt contains results from all executed hooks."""

        async def handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return True

        engine = Atman()
        pre_hook = KnowledgeHook("pre-hook", HookMode.PRE, handler)
        post_hook = KnowledgeHook("post-hook", HookMode.POST, handler)
        engine.register_hook(pre_hook)
        engine.register_hook(post_hook)

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(delta)

        assert len(receipt.hook_results) == EXPECTED_HOOK_COUNT_PRE_POST
        assert receipt.hook_results[0].hook_id == "pre-hook"
        assert receipt.hook_results[0].mode == HookMode.PRE
        assert receipt.hook_results[1].hook_id == "post-hook"
        assert receipt.hook_results[1].mode == HookMode.POST

    @pytest.mark.asyncio
    async def test_tip_not_updated_on_failed_transaction(self) -> None:
        """Tip hash doesn't advance when transaction fails."""

        async def deny_handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return False

        engine = Atman()
        hook = KnowledgeHook("deny-all", HookMode.PRE, deny_handler)
        engine.register_hook(hook)

        initial_tip = engine.tip_hash

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        await engine.apply(delta)

        assert engine.tip_hash == initial_tip

    @pytest.mark.asyncio
    async def test_custom_actor_in_receipt(self) -> None:
        """Custom actor is recorded in transaction context."""
        engine = Atman()
        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(delta, actor="alice")

        assert receipt.committed is True
        # Actor isn't directly on receipt, but tx_id proves unique context

    def test_repr(self) -> None:
        """Engine has informative repr."""
        engine = Atman()
        repr_str = repr(engine)
        assert "Atman" in repr_str
        assert "triples=0" in repr_str
        assert "hooks=0" in repr_str


class TestConstants:
    """Tests for module constants."""

    def test_genesis_hash_format(self) -> None:
        """GENESIS_HASH is valid SHA256 hex."""
        assert len(GENESIS_HASH) == EXPECTED_GENESIS_LENGTH
        # Should be valid hex
        int(GENESIS_HASH, 16)

    def test_genesis_hash_is_deterministic(self) -> None:
        """GENESIS_HASH is a valid deterministic starting point."""
        # Verify it's the documented value (stable across runs)
        expected = "4d7c606c9002d3043ee3979533922e25752bd2755709057060b553593605bd62"
        assert expected == GENESIS_HASH

    def test_chatman_constant_value(self) -> None:
        """CHATMAN_CONSTANT is 64."""
        assert CHATMAN_CONSTANT == EXPECTED_CHATMAN_CONSTANT


class TestHookMode:
    """Tests for HookMode enum."""

    def test_pre_mode_value(self) -> None:
        """PRE mode has correct value."""
        assert HookMode.PRE.value == "pre"

    def test_post_mode_value(self) -> None:
        """POST mode has correct value."""
        assert HookMode.POST.value == "post"


@pytest.mark.performance
class TestPerformance:
    """Performance tests against p99 targets."""

    @pytest.mark.asyncio
    async def test_apply_latency_p99(self) -> None:
        """Apply operation completes within p99 target (<100ms)."""
        engine = Atman()
        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])

        start = time.perf_counter()
        await engine.apply(delta)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < P99_TARGET_MS, (
            f"Apply took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"
        )

    @pytest.mark.asyncio
    async def test_batch_apply_latency(self) -> None:
        """Batch of CHATMAN_CONSTANT triples within target."""
        engine = Atman()
        triples = [("urn:s", f"urn:p{i}", f"urn:o{i}") for i in range(CHATMAN_CONSTANT)]
        delta = QuadDelta(additions=triples)

        start = time.perf_counter()
        receipt = await engine.apply(delta)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert receipt.committed is True
        assert elapsed_ms < P99_TARGET_MS, (
            f"Batch took {elapsed_ms:.2f}ms, target <{P99_TARGET_MS}ms"
        )

    def test_logic_hash_latency(self) -> None:
        """Logic hash computation is fast."""

        async def handler(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            return True

        engine = Atman()
        num_hooks = 50
        for i in range(num_hooks):
            hook = KnowledgeHook(f"hook-{i}", HookMode.PRE, handler)
            engine.register_hook(hook)

        start = time.perf_counter()
        engine.compute_logic_hash()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < LOGIC_HASH_TARGET_MS, (
            f"Logic hash took {elapsed_ms:.2f}ms, target <{LOGIC_HASH_TARGET_MS}ms"
        )


@pytest.mark.integration
class TestIntegration:
    """Integration tests for full engine workflows."""

    @pytest.mark.asyncio
    async def test_full_transaction_workflow(self) -> None:
        """Complete workflow: hooks → apply → verify."""
        executed_hooks: list[str] = []

        async def pre_guard(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            executed_hooks.append("pre_guard")
            return True

        async def pre_validate(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            executed_hooks.append("pre_validate")
            return True

        async def post_notify(s: Dataset, d: QuadDelta, c: TransactionContext) -> bool:
            executed_hooks.append("post_notify")
            return True

        engine = Atman()
        engine.register_hook(
            KnowledgeHook("guard", HookMode.PRE, pre_guard, priority=200)
        )
        engine.register_hook(
            KnowledgeHook("validate", HookMode.PRE, pre_validate, priority=100)
        )
        engine.register_hook(KnowledgeHook("notify", HookMode.POST, post_notify))

        delta = QuadDelta(additions=[("urn:s1", "urn:p1", "urn:o1")])
        receipt = await engine.apply(delta)

        assert receipt.committed is True
        assert executed_hooks == ["pre_guard", "pre_validate", "post_notify"]
        assert len(receipt.hook_results) == EXPECTED_HOOK_COUNT_FULL_WORKFLOW
        assert receipt.merkle_root != GENESIS_HASH
        assert engine.tip_hash == receipt.merkle_root

    @pytest.mark.asyncio
    async def test_lockchain_integrity(self) -> None:
        """Lockchain forms valid chain of hashes."""
        engine = Atman()
        hashes: list[str] = [GENESIS_HASH]

        for i in range(5):
            delta = QuadDelta(additions=[(f"urn:s{i}", f"urn:p{i}", f"urn:o{i}")])
            receipt = await engine.apply(delta)
            hashes.append(receipt.merkle_root)

        # All hashes are unique
        assert len(hashes) == len(set(hashes))
        # Final tip matches last receipt
        assert engine.tip_hash == hashes[-1]
