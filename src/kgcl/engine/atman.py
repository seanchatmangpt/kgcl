"""
THE ATMAN MONOLITH (Diamond Standard).

Philosophy: The Chatman Equation (A = μ(O))
Integrity: Data (O) + Logic (μ) + History (Lockchain)

This module implements a deterministic knowledge graph mutation engine
with O(1) provenance, cryptographic receipts, and configurable hooks.

The engine ensures:
1. Data Integrity - QuadDelta captures intent immutably
2. Logic Integrity - logic_hash proves which laws applied
3. History Integrity - merkle_root links transactions in a chain

Examples
--------
>>> import asyncio
>>> from kgcl.engine import Atman, QuadDelta, KnowledgeHook, HookMode
>>>
>>> async def main():
...     engine = Atman()
...     delta = QuadDelta(additions=[("urn:root", "urn:type", "urn:System")])
...     receipt = await engine.apply(delta)
...     assert receipt.committed
...     return receipt.merkle_root[:16]
>>>
>>> result = asyncio.run(main())
>>> len(result) == 16
True
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from rdflib import Dataset, Literal, URIRef

logger = logging.getLogger(__name__)

# Genesis Block Hash (SHA256 of 'KNHK')
GENESIS_HASH: str = "4d7c606c9002d3043ee3979533922e25752bd2755709057060b553593605bd62"

# Maximum batch size for Hot Path execution
CHATMAN_CONSTANT: int = 64


class HookMode(str, Enum):
    """
    Hook execution mode.

    Attributes
    ----------
    PRE : str
        Blocking Guard - executes before mutation (Hot Path).
        If any PRE hook returns False, the transaction is aborted.
    POST : str
        Async Side Effect - executes after mutation (Warm Path).
        POST hooks cannot block the transaction.
    """

    PRE = "pre"
    POST = "post"


# Triple Tuple: (Subject, Predicate, Object) - The Atomic Unit
Triple = tuple[str, str, str]


class QuadDelta(BaseModel):
    """
    The Observation (O).

    Represents the intent to mutate reality. Immutable once created.
    This is the input to the Chatman Equation: A = μ(O).

    Attributes
    ----------
    additions : list[Triple]
        Triples to add to the knowledge graph.
    removals : list[Triple]
        Triples to remove from the knowledge graph.

    Raises
    ------
    ValueError
        If batch size exceeds CHATMAN_CONSTANT (64).

    Examples
    --------
    >>> delta = QuadDelta(
    ...     additions=[("urn:s1", "urn:p1", "urn:o1")],
    ...     removals=[("urn:s2", "urn:p2", "urn:o2")],
    ... )
    """

    additions: list[Triple] = Field(default_factory=list)
    removals: list[Triple] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

    @field_validator("additions", "removals")
    @classmethod
    def enforce_chatman_constant(cls, v: list[Triple]) -> list[Triple]:
        """
        Ingress Guard: The Chatman Constant.

        Topology must be simple enough to execute in the Hot Path.

        Parameters
        ----------
        v : list[Triple]
            List of triples to validate.

        Returns
        -------
        list[Triple]
            The validated list.

        Raises
        ------
        ValueError
            If batch size exceeds CHATMAN_CONSTANT.
        """
        if len(v) > CHATMAN_CONSTANT:
            msg = (
                f"Topology Violation: Batch size {len(v)} "
                f"exceeds Hot Path limit ({CHATMAN_CONSTANT})."
            )
            raise ValueError(msg)
        return v


class TransactionContext(BaseModel):
    """
    The Context Window.

    Carries the pointer to the previous reality to form the Chain.
    This links each transaction to its predecessor, forming the Lockchain.

    Attributes
    ----------
    tx_id : str
        Unique transaction identifier (UUID4).
    actor : str
        Identity of the actor initiating the transaction.
    prev_hash : str
        Hash of the previous transaction (Lockchain link).
    timestamp : datetime
        UTC timestamp of transaction creation.
    """

    tx_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    actor: str = "system"
    prev_hash: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class HookResult(BaseModel):
    """
    Result of a single hook execution.

    Provides telemetry for each hook in the execution chain,
    enabling agents to understand what happened and why.

    Attributes
    ----------
    hook_id : str
        Identifier of the executed hook.
    mode : HookMode
        Whether this was a PRE or POST hook.
    success : bool
        Whether the hook executed successfully.
    duration_ns : int
        Execution duration in nanoseconds.
    """

    hook_id: str
    mode: HookMode
    success: bool
    duration_ns: int


class Receipt(BaseModel):
    """
    The Action (A).

    Cryptographic Proof of: State + Logic + History.
    This is the output of the Chatman Equation: A = μ(O).

    The Receipt provides complete provenance:
    - merkle_root: Proves WHAT data changed (links to previous state)
    - logic_hash: Proves WHICH laws applied (engine configuration)
    - hook_results: Proves HOW the transaction executed

    Attributes
    ----------
    tx_id : str
        Transaction identifier.
    committed : bool
        Whether the transaction was successfully committed.
    merkle_root : str
        Hash(Prev + Delta) - Links to previous state.
    logic_hash : str
        Hash(Active_Hooks) - Proves which laws applied.
    hook_results : list[HookResult]
        Results from all executed hooks.
    duration_ns : int
        Total transaction duration in nanoseconds.
    error : str | None
        Error message if transaction failed.

    Examples
    --------
    >>> r = Receipt(
    ...     tx_id="test-tx",
    ...     committed=True,
    ...     merkle_root="a" * 64,
    ...     logic_hash="b" * 64,
    ...     hook_results=[],
    ...     duration_ns=1000,
    ... )
    >>> r.committed
    True
    >>> len(r.merkle_root)
    64
    """

    tx_id: str
    committed: bool
    merkle_root: str
    logic_hash: str
    hook_results: list[HookResult]
    duration_ns: int
    error: str | None = None


# Type alias for hook handlers
HookHandler = Callable[[Dataset, QuadDelta, TransactionContext], Awaitable[bool]]


class KnowledgeHook:
    """
    A distinct Law of Physics within the engine.

    Hooks define the rules that govern knowledge graph mutations.
    PRE hooks act as guards (can block), POST hooks act as side effects.

    Parameters
    ----------
    hook_id : str
        Unique identifier for this hook.
    mode : HookMode
        PRE (blocking guard) or POST (side effect).
    handler : HookHandler
        Async function implementing the hook logic.
    priority : int
        Execution priority (higher = earlier). Default 100.

    Examples
    --------
    >>> async def guard_root(store, delta, ctx) -> bool:
    ...     for s, p, o in delta.removals:
    ...         if "urn:root" in s:
    ...             return False
    ...     return True
    >>>
    >>> hook = KnowledgeHook("guard-root", HookMode.PRE, guard_root)
    """

    __slots__ = ("_handler", "id", "mode", "priority")

    def __init__(
        self, hook_id: str, mode: HookMode, handler: HookHandler, priority: int = 100
    ) -> None:
        """Initialize a KnowledgeHook."""
        self.id = hook_id
        self.mode = mode
        self._handler = handler
        self.priority = priority

    async def execute(
        self, store: Dataset, delta: QuadDelta, ctx: TransactionContext
    ) -> bool:
        """
        Execute the hook handler.

        Parameters
        ----------
        store : Dataset
            The RDF Dataset being modified.
        delta : QuadDelta
            The proposed mutations.
        ctx : TransactionContext
            Transaction context with metadata.

        Returns
        -------
        bool
            True if hook allows the transaction, False to block.
        """
        return await self._handler(store, delta, ctx)

    def signature(self) -> str:
        """
        Return unique signature for Logic Hashing.

        Returns
        -------
        str
            Deterministic signature string.
        """
        return f"{self.id}:{self.mode.value}:{self.priority}"


class Atman:
    """
    The Deterministic Operator (μ).

    Implements A = μ(O) with O(1) Provenance.

    The Atman engine provides:
    - Deterministic execution of registered hooks
    - Cryptographic receipts for every transaction
    - Rolling Merkle hash (Lockchain) linking all transactions
    - Logic hash proving engine configuration

    Parameters
    ----------
    store : Dataset | None
        RDF Dataset for storage. Creates new if None.

    Attributes
    ----------
    store : Dataset
        The underlying RDF Dataset.
    tip_hash : str
        Current tip of the Lockchain (read-only property).

    Examples
    --------
    >>> import asyncio
    >>> engine = Atman()
    >>>
    >>> # Register a guard hook
    >>> async def no_delete_root(store, delta, ctx) -> bool:
    ...     return not any("urn:root" in s for s, _, _ in delta.removals)
    >>>
    >>> engine.register_hook(KnowledgeHook("guard-root", HookMode.PRE, no_delete_root))
    >>>
    >>> # Apply a transaction
    >>> delta = QuadDelta(additions=[("urn:root", "urn:type", "urn:System")])
    >>> receipt = asyncio.run(engine.apply(delta))
    >>> assert receipt.committed
    """

    __slots__ = ("_hooks", "_tip_hash", "store")

    def __init__(self, store: Dataset | None = None) -> None:
        """Initialize the Atman engine."""
        self.store: Dataset = store if store else Dataset()
        self._hooks: list[KnowledgeHook] = []
        self._tip_hash: str = GENESIS_HASH

    @property
    def tip_hash(self) -> str:
        """
        Current tip of the Lockchain.

        Returns
        -------
        str
            SHA256 hash of the most recent committed transaction.
        """
        return self._tip_hash

    @property
    def hooks(self) -> list[KnowledgeHook]:
        """
        Registered hooks (read-only copy).

        Returns
        -------
        list[KnowledgeHook]
            Copy of registered hooks in execution order.
        """
        return list(self._hooks)

    def register_hook(self, hook: KnowledgeHook) -> None:
        """
        Inject a Law into the Physics.

        Hooks are sorted by priority (descending) then ID (ascending)
        to ensure deterministic execution order.

        Parameters
        ----------
        hook : KnowledgeHook
            The hook to register.
        """
        self._hooks.append(hook)
        # Deterministic Execution Order: Priority DESC, then ID ASC
        self._hooks.sort(key=lambda h: (-h.priority, h.id))

    def unregister_hook(self, hook_id: str) -> bool:
        """
        Remove a Law from the Physics.

        Parameters
        ----------
        hook_id : str
            ID of the hook to remove.

        Returns
        -------
        bool
            True if hook was found and removed, False otherwise.
        """
        original_len = len(self._hooks)
        self._hooks = [h for h in self._hooks if h.id != hook_id]
        return len(self._hooks) < original_len

    def compute_logic_hash(self) -> str:
        """
        Provenance of Logic.

        Hashes the configuration of the engine itself.
        If the laws change, the receipt reflects it.

        Returns
        -------
        str
            SHA256 hash of all hook signatures.
        """
        signatures = [h.signature() for h in self._hooks]
        payload = "|".join(signatures)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _convert_triple(
        self, t: Triple
    ) -> tuple[URIRef | Literal, URIRef, URIRef | Literal]:
        """
        JIT Compilation of Strings to RDF Terms.

        Parameters
        ----------
        t : Triple
            String triple (subject, predicate, object).

        Returns
        -------
        tuple
            RDF term triple suitable for rdflib.
        """
        s, p, o = t
        # Heuristic: If it looks like a URI, it is. Else Literal.
        s_term: URIRef | Literal = URIRef(s) if "://" in s or ":" in s else Literal(s)
        p_term = URIRef(p)
        o_term: URIRef | Literal = URIRef(o) if "://" in o or ":" in o else Literal(o)
        return (s_term, p_term, o_term)

    async def apply(self, delta: QuadDelta, actor: str = "system") -> Receipt:
        """
        Execute the indivisible mutation operation.

        Executes the Chatman Equation: A = μ(O)
        - Runs PRE hooks (guards)
        - Applies mutations atomically
        - Runs POST hooks (side effects)
        - Returns cryptographic Receipt

        Parameters
        ----------
        delta : QuadDelta
            The observation (mutations to apply).
        actor : str
            Identity of the actor. Default "system".

        Returns
        -------
        Receipt
            Cryptographic proof of the transaction.

        Notes
        -----
        If any PRE hook returns False, the transaction is aborted
        and no mutations are applied. The Receipt will have
        committed=False and an error message.
        """
        start_ns = time.perf_counter_ns()

        # 1. CONTEXTUAL BINDING
        ctx = TransactionContext(actor=actor, prev_hash=self._tip_hash)
        hook_results: list[HookResult] = []
        committed = False
        error_msg: str | None = None

        try:
            # 2. PRE-HOOKS (Guards)
            pre_hooks = [h for h in self._hooks if h.mode == HookMode.PRE]
            for hook in pre_hooks:
                h_start = time.perf_counter_ns()
                success = await hook.execute(self.store, delta, ctx)

                hook_results.append(
                    HookResult(
                        hook_id=hook.id,
                        mode=HookMode.PRE,
                        success=success,
                        duration_ns=time.perf_counter_ns() - h_start,
                    )
                )

                if not success:
                    msg = f"Guard Violation: {hook.id}"
                    raise ValueError(msg)

            # 3. STATE MUTATION (The Physics)
            for t in delta.removals:
                self.store.remove(self._convert_triple(t))
            for t in delta.additions:
                self.store.add(self._convert_triple(t))

            committed = True

            # 4. POST-HOOKS (Side Effects)
            post_hooks = [h for h in self._hooks if h.mode == HookMode.POST]
            for hook in post_hooks:
                h_start = time.perf_counter_ns()
                await hook.execute(self.store, delta, ctx)
                hook_results.append(
                    HookResult(
                        hook_id=hook.id,
                        mode=HookMode.POST,
                        success=True,
                        duration_ns=time.perf_counter_ns() - h_start,
                    )
                )

        except Exception as e:
            logger.exception("TX Failed: %s", ctx.tx_id)
            error_msg = str(e)

        # 5. PROVENANCE (The Receipt)
        # Deterministic serialization for cross-platform consistency
        merkle_payload = f"{ctx.prev_hash}|{delta.model_dump_json(exclude_none=True)}"
        new_hash = hashlib.sha256(merkle_payload.encode()).hexdigest()

        # Update Tip *only if committed* (Atomic State)
        if committed:
            self._tip_hash = new_hash

        return Receipt(
            tx_id=ctx.tx_id,
            committed=committed,
            merkle_root=new_hash,
            logic_hash=self.compute_logic_hash(),
            hook_results=hook_results,
            duration_ns=time.perf_counter_ns() - start_ns,
            error=error_msg,
        )

    def __len__(self) -> int:
        """Return number of triples in the store."""
        return len(self.store)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Atman(triples={len(self)}, hooks={len(self._hooks)}, tip={self._tip_hash[:8]}...)"
