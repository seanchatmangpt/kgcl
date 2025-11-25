#!/usr/bin/env python3
"""Demonstration of KGCL lockchain features.

This script demonstrates:
1. Chain anchoring - linking receipts together
2. Content-addressable storage - receipts addressed by hash
3. Merkle tree proofs - efficient verification
"""

import tempfile
from datetime import datetime
from pathlib import Path

from src.kgcl.hooks.receipts import MerkleTree, Receipt, ReceiptStore


def demo_chain_anchoring():
    """Demonstrate receipt chain anchoring."""
    print("=" * 60)
    print("DEMO 1: Chain Anchoring")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ReceiptStore(Path(tmpdir))

        # Create a chain of receipts
        print("\nCreating chain of 5 receipts...")
        prev_receipt = None

        for i in range(5):
            receipt = Receipt(
                execution_id=f"exec-{i}",
                hook_id=f"hook-{i}",
                condition_result=True,
                effect_result=True,
                timestamp=datetime.utcnow(),
                metadata={"step": i, "action": f"action-{i}"},
            )

            content_hash = store.store_receipt(receipt, prev_receipt)
            loaded = store.load_receipt(content_hash)

            if loaded and loaded.chain_anchor:
                print(
                    f"  Receipt {i}: height={loaded.chain_anchor.chain_height}, "
                    f"hash={content_hash[:16]}..."
                )

            prev_receipt = loaded

        # Verify chain integrity
        print(f"\nVerifying chain integrity: {store.verify_chain_integrity(content_hash)}")

        # Traverse chain
        print("\nTraversing chain backwards:")
        chain = store.get_receipt_chain(content_hash)
        for i, receipt in enumerate(chain):
            print(f"  [{i}] exec_id={receipt.execution_id}, step={receipt.metadata['step']}")


def demo_content_addressing():
    """Demonstrate content-addressable storage."""
    print("\n" + "=" * 60)
    print("DEMO 2: Content-Addressable Storage")
    print("=" * 60)

    receipt1 = Receipt(
        execution_id="exec-1",
        hook_id="hook-1",
        condition_result=True,
        effect_result=True,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        metadata={"key": "value"},
    )

    receipt2 = Receipt(
        execution_id="exec-1",
        hook_id="hook-1",
        condition_result=True,
        effect_result=True,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        metadata={"key": "value"},
    )

    hash1 = receipt1.get_content_hash()
    hash2 = receipt2.get_content_hash()

    print(f"\nReceipt 1 hash: {hash1[:32]}...")
    print(f"Receipt 2 hash: {hash2[:32]}...")
    print(f"\nSame content = same hash: {hash1 == hash2}")


def demo_merkle_proofs():
    """Demonstrate Merkle tree proofs."""
    print("\n" + "=" * 60)
    print("DEMO 3: Merkle Tree Proofs")
    print("=" * 60)

    tree = MerkleTree()

    # Add items
    items = [f"receipt-{i}" for i in range(8)]
    print(f"\nAdding {len(items)} items to Merkle tree...")
    root = tree.add_batch(items)
    print(f"Root hash: {root[:32]}...")

    # Generate and verify proof
    test_item = items[3]
    print(f"\nGenerating proof for: {test_item}")
    proof = tree.get_proof(test_item)

    if proof:
        print(f"Proof has {len(proof)} steps:")
        for i, (hash_val, is_left) in enumerate(proof):
            side = "LEFT" if is_left else "RIGHT"
            print(f"  [{i}] {side}: {hash_val[:32]}...")

        # Verify proof
        is_valid = tree.verify_proof(test_item, proof, root)
        print(f"\nProof verification: {is_valid}")

    # Test with wrong item
    print("\nVerifying proof with wrong item...")
    wrong_proof_valid = tree.verify_proof("wrong-item", proof, root)
    print(f"Wrong item verification: {wrong_proof_valid}")


def demo_full_workflow():
    """Demonstrate complete lockchain workflow."""
    print("\n" + "=" * 60)
    print("DEMO 4: Full Lockchain Workflow")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = ReceiptStore(Path(tmpdir))
        tree = MerkleTree()

        print("\nCreating lockchain with Merkle tree...")
        prev_receipt = None
        receipt_hashes = []

        for i in range(5):
            receipt = Receipt(
                execution_id=f"exec-{i}",
                hook_id=f"hook-{i}",
                condition_result=True,
                effect_result=True,
                timestamp=datetime.utcnow(),
                metadata={"step": i},
            )

            # Store with chain linking
            content_hash = store.store_receipt(receipt, prev_receipt)
            receipt_hashes.append(content_hash)

            # Add to Merkle tree
            tree.add(content_hash)

            prev_receipt = store.load_receipt(content_hash)

        # Verify everything
        print(f"\nChain integrity: {store.verify_chain_integrity(receipt_hashes[-1])}")

        root = tree.get_root()
        print(f"Merkle root: {root[:32]}..." if root else "No root")

        # Verify each receipt is in Merkle tree
        print("\nVerifying all receipts in Merkle tree:")
        for i, receipt_hash in enumerate(receipt_hashes):
            proof = tree.get_proof(receipt_hash)
            if proof and root:
                is_valid = tree.verify_proof(receipt_hash, proof, root)
                print(f"  Receipt {i}: {is_valid}")


if __name__ == "__main__":
    demo_chain_anchoring()
    demo_content_addressing()
    demo_merkle_proofs()
    demo_full_workflow()

    print("\n" + "=" * 60)
    print("All demonstrations completed successfully!")
    print("=" * 60)
