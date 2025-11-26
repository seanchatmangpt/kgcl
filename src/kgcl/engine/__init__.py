"""
KGCL Engine Module - The Atman Monolith.

This module provides the Diamond Standard knowledge graph mutation engine
with cryptographic provenance, deterministic hooks, and O(1) receipts.

The Chatman Equation
--------------------
A = μ(O)

Where:
    - O (Observation): QuadDelta - The intent to mutate reality
    - μ (Operator): Atman - The deterministic mutation engine
    - A (Action): Receipt - Cryptographic proof of execution

Core Components
---------------
Atman : class
    The deterministic knowledge graph mutation engine
QuadDelta : class
    Immutable observation representing graph mutations
Receipt : class
    Cryptographic proof of transaction execution
KnowledgeHook : class
    Extensible law of physics for the engine
TransactionContext : class
    Context window linking transactions in a chain
HookMode : enum
    Hook execution mode (PRE or POST)
HookResult : class
    Telemetry from hook execution

Constants
---------
GENESIS_HASH : str
    SHA256 hash of the genesis block ('KNHK')
CHATMAN_CONSTANT : int
    Maximum batch size for Hot Path execution (64)

Examples
--------
>>> import asyncio
>>> from kgcl.engine import Atman, QuadDelta
>>>
>>> async def main():
...     engine = Atman()
...     delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
...     receipt = await engine.apply(delta)
...     return receipt.committed
>>>
>>> asyncio.run(main())
True

See Also
--------
kgcl.hooks : KGCL hooks system for event-driven processing
kgcl.unrdf_engine : UNRDF integration patterns
kgcl.observability : OpenTelemetry instrumentation

Notes
-----
The engine ensures three forms of integrity:
    1. Data Integrity - QuadDelta captures intent immutably
    2. Logic Integrity - logic_hash proves which laws applied
    3. History Integrity - merkle_root links transactions in a chain

All operations target p99 < 100ms for batches up to 64 triples.
"""

from kgcl.engine.atman import (
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

__all__ = [
    "CHATMAN_CONSTANT",
    "GENESIS_HASH",
    "Atman",
    "HookMode",
    "HookResult",
    "KnowledgeHook",
    "QuadDelta",
    "Receipt",
    "TransactionContext",
]
