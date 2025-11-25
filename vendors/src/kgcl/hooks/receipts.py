"""Enhanced receipt system with lockchain features.

This module implements UNRDF lockchain patterns for KGCL receipts:
- Chain anchoring (linking receipts to previous receipts)
- Content-addressable storage (receipts addressed by hash)
- Merkle tree proofs (efficient verification)

Ported from UNRDF lockchain-writer.mjs (Phase 3 Part B).
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

# Type alias for Merkle proof: List of (sibling_hash, is_left) tuples
MerkleProof = list[tuple[str, bool]]


@dataclass(frozen=True)
class ChainAnchor:
    """Links a receipt to the previous receipt in the chain.

    Chain anchoring enables:
    - Tamper detection: Any modification breaks the chain
    - Chronological ordering: Height establishes sequence
    - Provenance tracking: Navigate back to genesis

    Attributes
    ----------
        previous_receipt_hash: SHA256 of previous receipt (empty for genesis)
        chain_height: Position in chain (0 = genesis)
        timestamp: When link was created
    """

    previous_receipt_hash: str
    chain_height: int
    timestamp: datetime

    def is_genesis(self) -> bool:
        """Check if this is the genesis (first) anchor.

        Returns
        -------
            True if this is the first receipt in chain (height=0)
        """
        return self.chain_height == 0


@dataclass(frozen=True)
class Receipt:
    """Immutable record of hook execution with chain anchoring.

    Receipts are content-addressed and linked into a tamper-evident chain.
    Each receipt contains a cryptographic hash of its content and an anchor
    to the previous receipt.

    Attributes
    ----------
        execution_id: Unique identifier for this execution
        hook_id: Identifier of the hook that was executed
        condition_result: Whether the hook's condition was met
        effect_result: Whether the hook's effect succeeded
        timestamp: When the hook was executed
        metadata: Additional execution context
        chain_anchor: Link to previous receipt (None for unanchored receipts)
    """

    execution_id: str
    hook_id: str
    condition_result: bool
    effect_result: bool
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    chain_anchor: ChainAnchor | None = None

    def get_content_hash(self) -> str:
        """Get SHA256 hash of receipt content (for chain linking).

        Hash includes all receipt data except chain_anchor. This ensures
        the hash represents intrinsic content, not chain position.

        Returns
        -------
            Hex-encoded SHA256 hash of receipt content
        """
        content = json.dumps(
            {
                "execution_id": self.execution_id,
                "hook_id": self.hook_id,
                "condition_result": self.condition_result,
                "effect_result": self.effect_result,
                "timestamp": self.timestamp.isoformat(),
                "metadata": self.metadata,
            },
            sort_keys=True,
        )
        return sha256(content.encode()).hexdigest()


class ReceiptStore:
    """Enhanced receipt storage with content addressing and chain verification.

    Receipts are stored in a content-addressable system where the receipt's
    hash serves as its address. Each receipt links to the previous receipt,
    forming a tamper-evident chain.

    Attributes
    ----------
        storage_dir: Directory for receipt storage
    """

    def __init__(self, storage_dir: Path):
        """Initialize receipt store.

        Args:
            storage_dir: Directory for storing receipts
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def store_receipt(self, receipt: Receipt, previous_receipt: Receipt | None = None) -> str:
        """Store receipt with chain anchoring.

        If a previous receipt is provided, creates a chain anchor linking
        the new receipt to it. Otherwise, creates a genesis anchor.

        Args:
            receipt: Receipt to store
            previous_receipt: Previous receipt in chain (for anchoring)

        Returns
        -------
            Content hash (address) of stored receipt
        """
        # Create chain anchor
        chain_anchor: ChainAnchor
        if previous_receipt:
            chain_anchor = ChainAnchor(
                previous_receipt_hash=previous_receipt.get_content_hash(),
                chain_height=(
                    previous_receipt.chain_anchor.chain_height + 1
                    if previous_receipt.chain_anchor
                    else 1
                ),
                timestamp=datetime.utcnow(),
            )
        else:
            # Genesis receipt
            chain_anchor = ChainAnchor(
                previous_receipt_hash="", chain_height=0, timestamp=datetime.utcnow()
            )

        # Update receipt with chain anchor
        receipt_with_anchor = Receipt(
            execution_id=receipt.execution_id,
            hook_id=receipt.hook_id,
            condition_result=receipt.condition_result,
            effect_result=receipt.effect_result,
            timestamp=receipt.timestamp,
            metadata=receipt.metadata,
            chain_anchor=chain_anchor,
        )

        # Content address = receipt hash
        content_hash = receipt_with_anchor.get_content_hash()

        # Store in file system (key = content hash)
        receipt_file = self.storage_dir / f"{content_hash}.json"
        with open(receipt_file, "w") as f:
            json.dump(
                {
                    "receipt": {
                        "execution_id": receipt_with_anchor.execution_id,
                        "hook_id": receipt_with_anchor.hook_id,
                        "condition_result": receipt_with_anchor.condition_result,
                        "effect_result": receipt_with_anchor.effect_result,
                        "timestamp": receipt_with_anchor.timestamp.isoformat(),
                        "metadata": receipt_with_anchor.metadata,
                        "chain_anchor": {
                            "previous_receipt_hash": chain_anchor.previous_receipt_hash,
                            "chain_height": chain_anchor.chain_height,
                            "timestamp": chain_anchor.timestamp.isoformat(),
                        },
                    },
                    "content_hash": content_hash,
                },
                f,
                indent=2,
            )

        return content_hash

    def load_receipt(self, content_hash: str) -> Receipt | None:
        """Load receipt by content hash.

        Args:
            content_hash: Hash of receipt to load

        Returns
        -------
            Receipt if found, None otherwise
        """
        receipt_file = self.storage_dir / f"{content_hash}.json"
        if not receipt_file.exists():
            return None

        with open(receipt_file) as f:
            data = json.load(f)

        receipt_data = data["receipt"]
        anchor_data = receipt_data.get("chain_anchor")

        chain_anchor = None
        if anchor_data:
            chain_anchor = ChainAnchor(
                previous_receipt_hash=anchor_data["previous_receipt_hash"],
                chain_height=anchor_data["chain_height"],
                timestamp=datetime.fromisoformat(anchor_data["timestamp"]),
            )

        return Receipt(
            execution_id=receipt_data["execution_id"],
            hook_id=receipt_data["hook_id"],
            condition_result=receipt_data["condition_result"],
            effect_result=receipt_data["effect_result"],
            timestamp=datetime.fromisoformat(receipt_data["timestamp"]),
            metadata=receipt_data["metadata"],
            chain_anchor=chain_anchor,
        )

    def get_receipt_chain(self, receipt_hash: str, depth: int = 100) -> list[Receipt]:
        """Traverse receipt chain backwards.

        Starting from the given receipt, walks backwards through the chain
        via chain anchors. Stops at genesis or when depth limit reached.

        Args:
            receipt_hash: Hash of receipt to start from
            depth: Maximum chain depth to traverse

        Returns
        -------
            List of receipts in chain (most recent first)
        """
        chain: list[Receipt] = []
        current_hash = receipt_hash

        for _ in range(depth):
            receipt = self.load_receipt(current_hash)
            if not receipt or not receipt.chain_anchor:
                break

            chain.append(receipt)

            # Move to previous receipt
            if receipt.chain_anchor.previous_receipt_hash:
                current_hash = receipt.chain_anchor.previous_receipt_hash
            else:
                # Reached genesis
                break

        return chain

    def verify_chain_integrity(self, receipt_hash: str) -> bool:
        """Verify receipt chain integrity.

        Verifies that:
        1. Each receipt's hash matches its content
        2. Each receipt's anchor points to a valid previous receipt
        3. Chain is unbroken back to genesis

        Args:
            receipt_hash: Hash of receipt to verify

        Returns
        -------
            True if entire chain is valid
        """
        receipt = self.load_receipt(receipt_hash)
        if not receipt or not receipt.chain_anchor:
            return False

        current = receipt
        current_hash = receipt_hash

        while current and current.chain_anchor:
            # Verify this receipt's hash matches its content
            expected_hash = current.get_content_hash()
            if expected_hash != current_hash:
                return False

            # If genesis, we're done
            if current.chain_anchor.is_genesis():
                return True

            # Move to previous receipt
            if current.chain_anchor.previous_receipt_hash:
                prev_hash = current.chain_anchor.previous_receipt_hash
                current = self.load_receipt(prev_hash)
                if not current:
                    return False
                current_hash = prev_hash
            else:
                # Should not happen if not genesis
                return False

        return False


class MerkleTree:
    """Enhanced Merkle tree with batch operations and proof generation.

    A Merkle tree enables efficient verification of data integrity:
    - Root hash represents all leaves
    - Proofs verify membership without full tree
    - Batch operations efficiently update tree

    Attributes
    ----------
        leaves: List of leaf hashes
        root: Current root hash (None if empty)
    """

    def __init__(self):
        """Initialize empty Merkle tree."""
        self.leaves: list[str] = []
        self.root: str | None = None

    def _hash_pair(self, left: str, right: str) -> str:
        """Hash a pair of nodes.

        Args:
            left: Left node hash
            right: Right node hash

        Returns
        -------
            Combined hash
        """
        combined = left + right
        return sha256(combined.encode()).hexdigest()

    def _compute_root(self, hashes: list[str]) -> str:
        """Compute root hash from list of hashes.

        Args:
            hashes: List of hashes (must be non-empty)

        Returns
        -------
            Root hash
        """
        if len(hashes) == 1:
            return hashes[0]

        # Build next level
        next_level: list[str] = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else left
            next_level.append(self._hash_pair(left, right))

        return self._compute_root(next_level)

    def add(self, item: str) -> str:
        """Add item to tree.

        Args:
            item: Item to add (will be hashed)

        Returns
        -------
            Root hash after addition
        """
        item_hash = sha256(item.encode()).hexdigest()
        self.leaves.append(item_hash)
        self.root = self._compute_root(self.leaves) if self.leaves else None
        return self.root or ""

    def add_batch(self, items: list[str]) -> str:
        """Add multiple items to tree.

        More efficient than calling add() multiple times as it
        computes the root only once.

        Args:
            items: List of items to add

        Returns
        -------
            Root hash after additions
        """
        for item in items:
            item_hash = sha256(item.encode()).hexdigest()
            self.leaves.append(item_hash)

        self.root = self._compute_root(self.leaves) if self.leaves else None
        return self.root or ""

    def get_root(self) -> str | None:
        """Get current root hash.

        Returns
        -------
            Root hash, or None if tree is empty
        """
        return self.root

    def get_proof(self, item: str) -> MerkleProof | None:
        """Get Merkle proof for item (list of (hash, is_left) tuples to root).

        A Merkle proof is a list of sibling hashes with position information
        needed to compute the root from a leaf. This allows efficient
        verification that an item is in the tree.

        Args:
            item: Item to get proof for

        Returns
        -------
            List of (hash, is_left) tuples forming proof path, or None if
            item not found. is_left=True means sibling is on left side.
        """
        item_hash = sha256(item.encode()).hexdigest()
        try:
            index = self.leaves.index(item_hash)
        except ValueError:
            return None

        proof: MerkleProof = []
        current_level = self.leaves.copy()
        current_index = index

        while len(current_level) > 1:
            # Get sibling and track if it's on left or right
            if current_index % 2 == 0:
                # We're on left - sibling is on right
                sibling_index = current_index + 1
                if sibling_index < len(current_level):
                    proof.append((current_level[sibling_index], False))
                else:
                    # Odd number of nodes - duplicate ourselves
                    proof.append((current_level[current_index], False))
            else:
                # We're on right - sibling is on left
                sibling_index = current_index - 1
                proof.append((current_level[sibling_index], True))

            # Build next level
            next_level: list[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                next_level.append(self._hash_pair(left, right))

            current_level = next_level
            current_index = current_index // 2

        return proof

    def verify_proof(self, item: str, proof: MerkleProof, root: str) -> bool:
        """Verify Merkle proof.

        Recomputes the root hash using the item and proof, and checks
        if it matches the expected root.

        Args:
            item: Item being verified
            proof: Proof from get_proof() - list of (hash, is_left) tuples
            root: Expected tree root

        Returns
        -------
            True if proof is valid
        """
        item_hash = sha256(item.encode()).hexdigest()
        current = item_hash

        for sibling_hash, is_left in proof:
            # Combine according to position
            if is_left:
                # Sibling is on left
                current = self._hash_pair(sibling_hash, current)
            else:
                # Sibling is on right
                current = self._hash_pair(current, sibling_hash)

        return current == root
