"""
Receipt & Provenance System.

Implements cryptographic receipts, Merkle anchoring, and RDF serialization
for hook execution provenance.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MerkleAnchor:
    """
    Merkle tree anchor linking receipt to graph state.

    Parameters
    ----------
    root_hash : str
        Merkle root hash of graph state
    graph_version : int
        Graph version number
    timestamp : datetime
        Time of anchoring
    """

    root_hash: str
    graph_version: int
    timestamp: datetime


class Receipt:
    """
    Cryptographically verifiable receipt of hook execution.

    Provides immutable proof of execution with hashing and RDF serialization.
    """

    def __init__(
        self,
        hook_id: str,
        timestamp: datetime,
        condition_result: Any,
        handler_result: dict[str, Any] | None,
        duration_ms: float,
        actor: str | None = None,
        error: str | None = None,
        stack_trace: str | None = None,
        memory_delta_bytes: int | None = None,
        input_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        receipt_id: str | None = None,
        max_size_bytes: int | None = None,
        merkle_anchor: MerkleAnchor | None = None,
    ):
        """Initialize receipt with execution data."""
        self.receipt_id = receipt_id or str(uuid.uuid4())
        self.hook_id = hook_id
        self.timestamp = timestamp
        self.actor = actor
        self.condition_result = condition_result
        self.handler_result = handler_result
        self.duration_ms = duration_ms
        self.error = error
        self.stack_trace = stack_trace
        self.memory_delta_bytes = memory_delta_bytes
        self.input_context = input_context
        self.metadata = metadata or {}
        self.max_size_bytes = max_size_bytes
        self.merkle_anchor = merkle_anchor
        self.truncated = False

        # Handle size limits
        if max_size_bytes and handler_result:
            result_size = len(json.dumps(handler_result))
            if result_size > max_size_bytes:
                self.truncated = True
                self.handler_result = {"_truncated": True, "_size": result_size}

    def compute_hash(self) -> str:
        """
        Compute SHA256 hash of receipt.

        Returns
        -------
        str
            Hexadecimal hash digest
        """
        # Create deterministic representation
        data = {
            "receipt_id": self.receipt_id,
            "hook_id": self.hook_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "condition_triggered": (
                self.condition_result.triggered
                if hasattr(self.condition_result, "triggered")
                else False
            ),
            "handler_result": self.handler_result,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }

        # Serialize to JSON (sorted keys for determinism)
        json_str = json.dumps(data, sort_keys=True)

        # Compute SHA256
        return hashlib.sha256(json_str.encode()).hexdigest()

    def to_json_ld(self) -> dict[str, Any]:
        """
        Convert receipt to JSON-LD format.

        Returns
        -------
        Dict[str, Any]
            JSON-LD representation
        """
        return {
            "@context": {
                "@vocab": "http://kgcl.io/hooks/",
                "prov": "http://www.w3.org/ns/prov#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
            },
            "@type": "HookReceipt",
            "@id": f"urn:uuid:{self.receipt_id}",
            "hookId": self.hook_id,
            "timestamp": {"@type": "xsd:dateTime", "@value": self.timestamp.isoformat()},
            "actor": self.actor,
            "conditionTriggered": (
                self.condition_result.triggered
                if hasattr(self.condition_result, "triggered")
                else False
            ),
            "handlerResult": self.handler_result,
            "durationMs": self.duration_ms,
            "error": self.error,
            "hash": self.compute_hash(),
        }

    @classmethod
    def from_json_ld(cls, data: dict[str, Any]) -> "Receipt":
        """
        Restore receipt from JSON-LD.

        Parameters
        ----------
        data : Dict[str, Any]
            JSON-LD representation

        Returns
        -------
        Receipt
            Restored receipt
        """
        from kgcl.hooks.conditions import ConditionResult

        timestamp_value = data.get("timestamp", {})
        if isinstance(timestamp_value, dict):
            timestamp = datetime.fromisoformat(timestamp_value.get("@value", ""))
        else:
            timestamp = datetime.fromisoformat(timestamp_value)

        condition_result = ConditionResult(
            triggered=data.get("conditionTriggered", False), metadata={}
        )

        return cls(
            receipt_id=data.get("@id", "").replace("urn:uuid:", ""),
            hook_id=data.get("hookId", ""),
            timestamp=timestamp,
            actor=data.get("actor"),
            condition_result=condition_result,
            handler_result=data.get("handlerResult"),
            duration_ms=data.get("durationMs", 0.0),
            error=data.get("error"),
        )

    def to_rdf_triples(self) -> list[tuple[str, str, str]]:
        """
        Convert receipt to RDF triples.

        Returns
        -------
        List[tuple]
            List of (subject, predicate, object) triples
        """
        subject = f"urn:uuid:{self.receipt_id}"
        triples = [
            (subject, "rdf:type", "HookReceipt"),
            (subject, "hookId", self.hook_id),
            (subject, "timestamp", self.timestamp.isoformat()),
            (subject, "durationMs", str(self.duration_ms)),
        ]

        if self.actor:
            triples.append((subject, "actor", self.actor))

        if self.error:
            triples.append((subject, "error", self.error))

        if hasattr(self.condition_result, "triggered"):
            triples.append((subject, "conditionTriggered", str(self.condition_result.triggered)))

        return triples

    def generate_proof(self) -> dict[str, Any]:
        """
        Generate cryptographic proof of execution.

        Returns
        -------
        Dict[str, Any]
            Proof data including hash and metadata
        """
        return {
            "receipt_id": self.receipt_id,
            "hook_id": self.hook_id,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.compute_hash(),
            "merkle_anchor": (
                {
                    "root_hash": self.merkle_anchor.root_hash,
                    "graph_version": self.merkle_anchor.graph_version,
                    "timestamp": self.merkle_anchor.timestamp.isoformat(),
                }
                if self.merkle_anchor
                else None
            ),
        }


class ReceiptStore:
    """
    Storage and querying for receipts.

    Provides persistence and indexed queries.
    """

    def __init__(self) -> None:
        """Initialize in-memory receipt store."""
        self._receipts: dict[str, Receipt] = {}
        self._index_by_hook: dict[str, list[str]] = {}
        self._index_by_actor: dict[str, list[str]] = {}

    async def save(self, receipt: Receipt) -> None:
        """
        Save a receipt.

        Parameters
        ----------
        receipt : Receipt
            Receipt to save
        """
        self._receipts[receipt.receipt_id] = receipt

        # Index by hook_id
        if receipt.hook_id not in self._index_by_hook:
            self._index_by_hook[receipt.hook_id] = []
        self._index_by_hook[receipt.hook_id].append(receipt.receipt_id)

        # Index by actor
        if receipt.actor:
            if receipt.actor not in self._index_by_actor:
                self._index_by_actor[receipt.actor] = []
            self._index_by_actor[receipt.actor].append(receipt.receipt_id)

    async def get_by_id(self, receipt_id: str) -> Receipt | None:
        """
        Get receipt by ID.

        Parameters
        ----------
        receipt_id : str
            Receipt identifier

        Returns
        -------
        Optional[Receipt]
            Receipt if found
        """
        return self._receipts.get(receipt_id)

    async def query(
        self,
        hook_id: str | None = None,
        actor: str | None = None,
        timestamp_from: datetime | None = None,
        timestamp_to: datetime | None = None,
    ) -> list[Receipt]:
        """
        Query receipts by various criteria.

        Parameters
        ----------
        hook_id : Optional[str]
            Filter by hook ID
        actor : Optional[str]
            Filter by actor
        timestamp_from : Optional[datetime]
            Filter by timestamp range (start)
        timestamp_to : Optional[datetime]
            Filter by timestamp range (end)

        Returns
        -------
        List[Receipt]
            Matching receipts
        """
        receipt_ids = None

        # Filter by hook_id
        if hook_id:
            receipt_ids = set(self._index_by_hook.get(hook_id, []))

        # Filter by actor
        if actor:
            actor_ids = set(self._index_by_actor.get(actor, []))
            receipt_ids = actor_ids if receipt_ids is None else receipt_ids.intersection(actor_ids)

        # Get receipts
        if receipt_ids is not None:
            receipts = [self._receipts[rid] for rid in receipt_ids if rid in self._receipts]
        else:
            receipts = list(self._receipts.values())

        # Filter by timestamp
        if timestamp_from:
            receipts = [r for r in receipts if r.timestamp >= timestamp_from]

        if timestamp_to:
            receipts = [r for r in receipts if r.timestamp <= timestamp_to]

        return receipts


class MerkleTree:
    """
    Merkle tree for graph state anchoring.

    Provides cryptographic proof of graph state at receipt time.
    """

    def __init__(self) -> None:
        """Initialize Merkle tree."""
        self._leaves: list[str] = []

    def add_leaf(self, data: str) -> None:
        """
        Add leaf to tree.

        Parameters
        ----------
        data : str
            Leaf data
        """
        leaf_hash = hashlib.sha256(data.encode()).hexdigest()
        self._leaves.append(leaf_hash)

    def compute_root(self) -> str:
        """
        Compute Merkle root.

        Returns
        -------
        str
            Root hash
        """
        if not self._leaves:
            return ""

        current_level = self._leaves[:]

        while len(current_level) > 1:
            next_level = []

            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left

                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)

            current_level = next_level

        return current_level[0]

    def create_anchor(self, graph_version: int) -> MerkleAnchor:
        """
        Create Merkle anchor for current state.

        Parameters
        ----------
        graph_version : int
            Graph version number

        Returns
        -------
        MerkleAnchor
            Merkle anchor
        """
        return MerkleAnchor(
            root_hash=self.compute_root(), graph_version=graph_version, timestamp=datetime.utcnow()
        )
