#!/usr/bin/env python3
"""Proof script: RDR tree worklet selection.

Demonstrates REAL worklet selection behavior through RDR tree traversal.
This is NOT a mock - it uses the actual worklet engine.

Run: uv run python examples/proof_worklet_selection.py

Expected output:
- High priority case selects priority handler
- Normal priority case selects timeout handler
- Invalid priority falls back to default

If RDR engine is broken, this script will fail with wrong worklet selected.
"""

from __future__ import annotations

from kgcl.yawl.worklets.executor import WorkletExecutor
from kgcl.yawl.worklets.models import Worklet, WorkletType


def main() -> None:
    """Prove RDR tree worklet selection works."""
    print("=" * 70)
    print("PROOF: RDR Tree Worklet Selection")
    print("=" * 70)

    # Create executor with real components
    executor = WorkletExecutor()
    print("✓ Created WorkletExecutor with real RDR engine and repository")

    # Register worklets for different priorities
    priority_handler = Worklet(
        id="wl-priority",
        name="Priority Handler",
        worklet_type=WorkletType.CASE_EXCEPTION,
        description="Handles high-priority timeouts with escalation",
        parameters={"action": "escalate", "notify_manager": True},
    )
    executor.register_worklet(priority_handler)

    timeout_handler = Worklet(
        id="wl-timeout",
        name="Timeout Handler",
        worklet_type=WorkletType.CASE_EXCEPTION,
        description="Handles normal timeouts with retry",
        parameters={"action": "retry", "max_retries": 3},
    )
    executor.register_worklet(timeout_handler)

    print(f"✓ Registered 2 worklets: {priority_handler.name}, {timeout_handler.name}")

    # Build RDR tree with priority condition
    tree_id = executor.register_tree(task_id=None, exception_type="TIMEOUT")
    tree = executor.repository.get_tree(tree_id)
    assert tree is not None

    # Root: Check if priority is high
    tree.root.condition = "priority == high"
    tree.root.conclusion = priority_handler.id

    # False branch: Default to timeout handler
    executor.add_rule(
        tree_id=tree_id,
        parent_node_id="root",
        is_true_branch=False,
        condition="true",
        worklet_id=timeout_handler.id,
    )

    print(f"✓ Built RDR tree with condition: 'priority == high'")
    print()

    # Test 1: High priority should select priority handler
    print("Test 1: High Priority Timeout")
    print("-" * 70)
    result1 = executor.handle_case_exception(
        case_id="case-001",
        exception_type="TIMEOUT",
        exception_message="Critical service timeout after 60s",
        case_data={"priority": "high", "service": "payment-api"},
    )

    print(f"  Case ID: case-001")
    print(f"  Priority: high")
    print(f"  Selected Worklet: {result1.worklet_id}")
    print(f"  Action: {result1.output_data.get('action')}")

    if result1.worklet_id == priority_handler.id:
        print("  ✓ CORRECT: Selected priority handler")
    else:
        print(f"  ✗ WRONG: Expected {priority_handler.id}, got {result1.worklet_id}")
        print("  ✗ RDR ENGINE IS BROKEN!")
        return

    assert result1.success, "High priority execution should succeed"
    assert result1.output_data["action"] == "escalate", "Should escalate high priority"
    print()

    # Test 2: Normal priority should select timeout handler
    print("Test 2: Normal Priority Timeout")
    print("-" * 70)
    result2 = executor.handle_case_exception(
        case_id="case-002",
        exception_type="TIMEOUT",
        exception_message="Background job timeout after 30s",
        case_data={"priority": "normal", "service": "email-sender"},
    )

    print(f"  Case ID: case-002")
    print(f"  Priority: normal")
    print(f"  Selected Worklet: {result2.worklet_id}")
    print(f"  Action: {result2.output_data.get('action')}")

    if result2.worklet_id == timeout_handler.id:
        print("  ✓ CORRECT: Selected timeout handler")
    else:
        print(f"  ✗ WRONG: Expected {timeout_handler.id}, got {result2.worklet_id}")
        print("  ✗ RDR ENGINE IS BROKEN!")
        return

    assert result2.success, "Normal priority execution should succeed"
    assert result2.output_data["action"] == "retry", "Should retry normal priority"
    print()

    # Test 3: Missing priority should fall back to default (false branch)
    print("Test 3: Missing Priority (Fallback)")
    print("-" * 70)
    result3 = executor.handle_case_exception(
        case_id="case-003",
        exception_type="TIMEOUT",
        exception_message="Unknown priority timeout",
        case_data={"service": "unknown"},  # No priority field
    )

    print(f"  Case ID: case-003")
    print(f"  Priority: (missing)")
    print(f"  Selected Worklet: {result3.worklet_id}")
    print(f"  Action: {result3.output_data.get('action')}")

    if result3.worklet_id == timeout_handler.id:
        print("  ✓ CORRECT: Fell back to timeout handler")
    else:
        print(f"  ✗ WRONG: Expected {timeout_handler.id}, got {result3.worklet_id}")
        print("  ✗ RDR ENGINE FALLBACK IS BROKEN!")
        return

    print()

    # Verify RDR tree structure
    print("RDR Tree Structure Verification")
    print("-" * 70)
    print(f"  Root condition: {tree.root.condition}")
    print(f"  Root conclusion: {tree.root.conclusion}")
    print(f"  False child exists: {tree.root.false_child is not None}")
    if tree.root.false_child:
        print(f"  False child condition: {tree.root.false_child.condition}")
        print(f"  False child conclusion: {tree.root.false_child.conclusion}")
    print()

    print("=" * 70)
    print("✓ ALL PROOFS PASSED")
    print("=" * 70)
    print()
    print("This proves:")
    print("  1. RDR engine evaluates conditions correctly")
    print("  2. String equality comparison works (priority == high)")
    print("  3. True/false branch navigation works")
    print("  4. Fallback to false branch works when condition fails")
    print("  5. Worklet selection returns correct worklet ID")
    print()
    print("If any test failed, the RDR engine would be broken.")
    print("This is NOT a mock - this is the REAL engine behavior.")


if __name__ == "__main__":
    main()
