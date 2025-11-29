#!/usr/bin/env python3
"""Proof script: Worklet case lifecycle state transitions.

Demonstrates REAL worklet case state management through its lifecycle.
This is NOT a mock - it uses the actual worklet repository.

Run: uv run python examples/proof_worklet_lifecycle.py

Expected output:
- Case starts in PENDING state
- Transitions to RUNNING when started
- Transitions to COMPLETED when finished
- Timestamps are recorded

If lifecycle management is broken, states won't transition correctly.
"""

from __future__ import annotations

from datetime import datetime

from kgcl.yawl.worklets.models import WorkletCase, WorkletStatus
from kgcl.yawl.worklets.repository import WorkletRepository


def main() -> None:
    """Prove worklet case lifecycle state transitions work."""
    print("=" * 70)
    print("PROOF: Worklet Case Lifecycle State Transitions")
    print("=" * 70)

    # Create repository with real storage
    repository = WorkletRepository()
    print("✓ Created WorkletRepository with real in-memory storage")
    print()

    # Create a worklet case
    print("Creating Worklet Case")
    print("-" * 70)
    case = WorkletCase(
        id="case-lifecycle-001",
        worklet_id="wl-test",
        parent_case_id="parent-case-001",
        exception_type="TEST_EXCEPTION",
        exception_data={"message": "Testing lifecycle"},
    )
    print(f"  Case ID: {case.id}")
    print(f"  Initial Status: {case.status.name}")
    print(f"  Started: {case.started}")
    print(f"  Completed: {case.completed}")

    # Verify initial state
    assert case.status == WorkletStatus.PENDING, "Should start in PENDING state"
    assert case.completed is None, "Should not have completion time initially"
    print("  ✓ Case created in PENDING state")
    print()

    # Add to repository
    repository.add_case(case)
    print("✓ Case stored in repository")

    # Verify can retrieve
    retrieved = repository.get_case(case.id)
    assert retrieved is not None, "Should be able to retrieve case"
    assert retrieved.id == case.id, "Retrieved case should match"
    print(f"✓ Retrieved case from repository: {retrieved.id}")
    print()

    # Transition to RUNNING
    print("Transition: PENDING → RUNNING")
    print("-" * 70)
    # Note: started time is set at creation, not when start() is called
    case.start()

    print(f"  Status: {case.status.name}")
    print(f"  Started: {case.started}")
    print(f"  Completed: {case.completed}")

    assert case.status == WorkletStatus.RUNNING, "Should be in RUNNING state"
    assert case.completed is None, "Should still not have completion time"
    assert case.started is not None, "Should have start time"
    print("  ✓ Transitioned to RUNNING state")
    print()

    # Transition to COMPLETED
    print("Transition: RUNNING → COMPLETED")
    print("-" * 70)
    result_data = {
        "worklet_id": "wl-test",
        "action": "completed",
        "success": True,
    }

    before_complete = datetime.now()
    case.complete(result_data)
    after_complete = datetime.now()

    print(f"  Status: {case.status.name}")
    print(f"  Started: {case.started}")
    print(f"  Completed: {case.completed}")
    print(f"  Result Data: {case.result_data}")

    assert case.status == WorkletStatus.COMPLETED, "Should be in COMPLETED state"
    assert case.completed is not None, "Should have completion time"
    assert before_complete <= case.completed <= after_complete, "Completed time should be recent"
    assert case.completed >= case.started, "Completed time should be after started"
    assert case.result_data == result_data, "Result data should be stored"
    print("  ✓ Transitioned to COMPLETED state")
    print("  ✓ Completion timestamp recorded")
    print("  ✓ Result data stored")
    print()

    # Test FAILED transition
    print("Test FAILED Transition")
    print("-" * 70)
    failed_case = WorkletCase(
        id="case-failed",
        worklet_id="wl-test",
        parent_case_id="parent-002",
    )
    repository.add_case(failed_case)
    failed_case.start()

    failed_case.fail("Test error message")

    print(f"  Status: {failed_case.status.name}")
    print(f"  Error: {failed_case.result_data.get('error')}")

    assert failed_case.status == WorkletStatus.FAILED, "Should be in FAILED state"
    assert failed_case.completed is not None, "Should have completion time"
    assert failed_case.result_data["error"] == "Test error message", "Error should be stored"
    print("  ✓ FAILED transition works")
    print()

    # Test CANCELLED transition
    print("Test CANCELLED Transition")
    print("-" * 70)
    cancelled_case = WorkletCase(
        id="case-cancelled",
        worklet_id="wl-test",
        parent_case_id="parent-003",
    )
    repository.add_case(cancelled_case)
    cancelled_case.start()

    cancelled_case.cancel()

    print(f"  Status: {cancelled_case.status.name}")

    assert cancelled_case.status == WorkletStatus.CANCELLED, "Should be in CANCELLED state"
    assert cancelled_case.completed is not None, "Should have completion time"
    print("  ✓ CANCELLED transition works")
    print()

    # Test repository queries
    print("Repository Query Verification")
    print("-" * 70)
    all_cases = repository.find_cases()
    print(f"  Total cases: {len(all_cases)}")

    completed_cases = repository.find_cases(status=WorkletStatus.COMPLETED)
    print(f"  Completed cases: {len(completed_cases)}")

    parent_cases = repository.find_cases(parent_case_id="parent-case-001")
    print(f"  Cases for parent-case-001: {len(parent_cases)}")

    assert len(all_cases) == 3, "Should have 3 total cases"
    assert len(completed_cases) == 1, "Should have 1 completed case"
    assert len(parent_cases) == 1, "Should have 1 case for parent"
    print("  ✓ Repository queries work correctly")
    print()

    print("=" * 70)
    print("✓ ALL LIFECYCLE PROOFS PASSED")
    print("=" * 70)
    print()
    print("This proves:")
    print("  1. Cases start in PENDING state")
    print("  2. start() transitions to RUNNING")
    print("  3. complete() transitions to COMPLETED with timestamp")
    print("  4. fail() transitions to FAILED with error")
    print("  5. cancel() transitions to CANCELLED")
    print("  6. Timestamps are recorded correctly")
    print("  7. Result data is stored")
    print("  8. Repository stores and retrieves cases")
    print("  9. Repository queries work correctly")
    print()
    print("If any test failed, lifecycle management would be broken.")
    print("This is NOT a mock - this is REAL state management.")


if __name__ == "__main__":
    main()
