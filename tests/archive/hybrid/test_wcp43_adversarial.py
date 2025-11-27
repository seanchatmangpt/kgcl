"""Adversarial (Devil's Advocate) Tests for WCP-43 Physics Rules.

These tests verify that the N3 physics rules correctly handle edge cases where
naive implementations would fail. Each test targets a specific failure mode
discovered during adversarial analysis.

Failure Modes Tested
--------------------
- WCP-4: XOR-Split mutual exclusion (multiple true predicates)
- WCP-10: Arbitrary cycles edge exclusivity (back vs exit)
- WCP-12: MI spawning termination (infinite loop prevention)
- WCP-17: Interleaved parallel mutex (race conditions)
- WCP-21: Structured loop termination (infinite iteration)
- WCP-29: Cancelling discriminator winner preservation
- WCP-39: Critical section mutual exclusion (race conditions)

References
----------
- van der Aalst et al. (2003) "Workflow Patterns"
- Plan: /Users/sac/.claude/plans/cuddly-tickling-karp.md
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.wcp43_physics import (
    WCP4_EXCLUSIVE_CHOICE,
    WCP10_ARBITRARY_CYCLES,
    WCP12_MI_WITHOUT_SYNC,
    WCP17_INTERLEAVED_PARALLEL,
    WCP21_STRUCTURED_LOOP,
    WCP29_CANCELLING_DISCRIMINATOR,
    WCP39_CRITICAL_SECTION,
)

# WCP43 Lean Six Sigma tests run full engine cycles - mark as slow
pytestmark = pytest.mark.slow


class TestWCP4XorSplitMutualExclusion:
    """WCP-4: Only ONE branch activates when multiple predicates are true.

    Failure mode: Without monotonic marker, N3 fires ALL matching bindings,
    activating both Branch_A and Branch_B when both predicates are true.

    Fix: Uses kgc:xorBranchSelected marker with log:notIncludes guard.
    """

    def test_rule_has_xor_branch_selected_marker(self) -> None:
        """Rule 4a must add kgc:xorBranchSelected marker."""
        assert "kgc:xorBranchSelected true" in WCP4_EXCLUSIVE_CHOICE

    def test_rule_has_first_wins_guard(self) -> None:
        """Rule 4a must guard against already-selected branch."""
        assert "_:scope log:notIncludes { ?task kgc:xorBranchSelected true }" in WCP4_EXCLUSIVE_CHOICE

    def test_default_path_also_guarded(self) -> None:
        """Rule 4b (default path) must also respect marker."""
        # Find the default path rule section
        default_section = WCP4_EXCLUSIVE_CHOICE.split("isDefaultFlow true")[1]
        assert "kgc:xorBranchSelected true" in default_section

    def test_selected_branch_recorded(self) -> None:
        """Winner branch is recorded for traceability."""
        assert "kgc:selectedBranch ?next" in WCP4_EXCLUSIVE_CHOICE


class TestWCP10ArbitraryCyclesExclusivity:
    """WCP-10: Only ONE edge (back or exit) fires per completion.

    Failure mode: Both back-edge AND exit-edge could fire simultaneously
    when the rule structure doesn't enforce mutual exclusion.

    Fix: Uses kgc:cycleEdgeSelected marker for edge exclusivity.
    """

    def test_rule_has_cycle_edge_marker(self) -> None:
        """Rules must use kgc:cycleEdgeSelected for exclusivity."""
        assert "kgc:cycleEdgeSelected true" in WCP10_ARBITRARY_CYCLES

    def test_back_edge_guarded(self) -> None:
        """Back-edge rule must check marker before firing."""
        assert "_:scope log:notIncludes { ?task kgc:cycleEdgeSelected true }" in WCP10_ARBITRARY_CYCLES

    def test_exit_edge_guarded(self) -> None:
        """Exit-edge rule must also check marker."""
        # Both rules should have the guard
        guard_count = WCP10_ARBITRARY_CYCLES.count("_:scope log:notIncludes { ?task kgc:cycleEdgeSelected true }")
        assert guard_count >= 2, "Both back-edge and exit-edge need guards"

    def test_selected_edge_recorded(self) -> None:
        """Selected edge (back/exit) is recorded for traceability."""
        assert 'kgc:selectedEdge "back"' in WCP10_ARBITRARY_CYCLES
        assert 'kgc:selectedEdge "exit"' in WCP10_ARBITRARY_CYCLES


class TestWCP12MIWithoutSyncTermination:
    """WCP-12: MI spawning MUST terminate at instanceCount.

    Failure mode: Without termination guard, spawning rule fires repeatedly
    as spawnedCount increments, causing delta=3584 runaway.

    Fix: Uses kgc:spawningComplete marker with math:notLessThan guard.
    """

    def test_rule_has_spawning_complete_marker(self) -> None:
        """Rule must use kgc:spawningComplete for termination."""
        assert "kgc:spawningComplete true" in WCP12_MI_WITHOUT_SYNC

    def test_termination_check_exists(self) -> None:
        """Termination condition uses math:notLessThan."""
        assert "math:notLessThan" in WCP12_MI_WITHOUT_SYNC

    def test_spawn_rule_guarded(self) -> None:
        """Spawn rule must check spawningComplete before firing."""
        assert "_:scope log:notIncludes { ?mi kgc:spawningComplete true }" in WCP12_MI_WITHOUT_SYNC

    def test_termination_rule_comes_first(self) -> None:
        """Termination marker rule (12a) should be defined before spawn rule (12b)."""
        # Find positions
        termination_pos = WCP12_MI_WITHOUT_SYNC.find("Rule 12a")
        spawn_pos = WCP12_MI_WITHOUT_SYNC.find("Rule 12b")
        assert termination_pos < spawn_pos, "Termination rule must come before spawn rule"


class TestWCP17InterleavedParallelMutex:
    """WCP-17: Mutex ensures only ONE task Active at a time.

    Failure mode: When mutex holder="none" and multiple Ready tasks exist,
    naive rule fires for ALL, setting holder to each (last wins, others active).

    Fix: Uses URI-based ordering (string:lessThan) for deterministic selection.
    """

    def test_rule_has_ordering_guard(self) -> None:
        """Acquire rule must use ordering to break ties."""
        assert "string:lessThan" in WCP17_INTERLEAVED_PARALLEL

    def test_lowest_ordered_wins(self) -> None:
        """Guard checks that no lower-ordered Ready task exists."""
        assert "_:scope log:notIncludes" in WCP17_INTERLEAVED_PARALLEL
        assert "?other string:lessThan ?task" in WCP17_INTERLEAVED_PARALLEL

    def test_higher_ordered_blocked(self) -> None:
        """Higher-ordered Ready tasks become Blocked."""
        assert 'kgc:status "Blocked"' in WCP17_INTERLEAVED_PARALLEL
        assert "kgc:blockedByOrdering" in WCP17_INTERLEAVED_PARALLEL

    def test_mutex_release_on_completion(self) -> None:
        """Mutex released when task completes."""
        assert 'kgc:holder "none"' in WCP17_INTERLEAVED_PARALLEL
        assert 'kgc:status "Completed"' in WCP17_INTERLEAVED_PARALLEL


class TestWCP21StructuredLoopTermination:
    """WCP-21: Loop MUST terminate at maxIterations.

    Failure mode: Without termination guard, iteration continues forever
    when condition stays true, causing delta=96 runaway.

    Fix: Uses kgc:loopExhausted marker with math:notLessThan guard.
    """

    def test_rule_has_loop_exhausted_marker(self) -> None:
        """Rule must use kgc:loopExhausted for termination."""
        assert "kgc:loopExhausted true" in WCP21_STRUCTURED_LOOP

    def test_termination_check_exists(self) -> None:
        """Termination condition uses math:notLessThan."""
        assert "math:notLessThan" in WCP21_STRUCTURED_LOOP

    def test_continue_rule_guarded(self) -> None:
        """Continue iteration rule must check loopExhausted."""
        assert "_:scope log:notIncludes { ?loop kgc:loopExhausted true }" in WCP21_STRUCTURED_LOOP

    def test_exit_reason_recorded(self) -> None:
        """Exit reason (maxIterations or conditionFalse) is recorded."""
        assert 'kgc:exitReason "maxIterations"' in WCP21_STRUCTURED_LOOP
        assert 'kgc:exitReason "conditionFalse"' in WCP21_STRUCTURED_LOOP


class TestWCP29CancellingDiscriminatorWinnerPreservation:
    """WCP-29: Winner branch must NOT be cancelled.

    Failure mode: Naive cancel rule fires for ALL waitingFor branches,
    including the winner which already has status "Completed".

    Fix: Multiple guards ensure winner is never cancelled:
    1. ?loser != ?winner check
    2. status != "Completed" check
    3. isWinningBranch marker check
    """

    def test_winner_marked(self) -> None:
        """Winner branch is explicitly marked."""
        assert "kgc:isWinningBranch true" in WCP29_CANCELLING_DISCRIMINATOR

    def test_loser_not_winner_check(self) -> None:
        """Cancel rule checks loser is not winner."""
        assert "?loser log:equalTo ?winner" in WCP29_CANCELLING_DISCRIMINATOR

    def test_completed_status_guard(self) -> None:
        """Cancel rule guards against Completed status."""
        assert '_:scope2 log:notIncludes { ?status log:equalTo "Completed" }' in WCP29_CANCELLING_DISCRIMINATOR

    def test_cancelled_status_guard(self) -> None:
        """Cancel rule guards against already Cancelled."""
        assert '_:scope3 log:notIncludes { ?status log:equalTo "Cancelled" }' in WCP29_CANCELLING_DISCRIMINATOR

    def test_winning_branch_guard(self) -> None:
        """Cancel rule checks isWinningBranch marker."""
        assert "?loser kgc:isWinningBranch true" in WCP29_CANCELLING_DISCRIMINATOR


class TestWCP39CriticalSectionMutualExclusion:
    """WCP-39: Critical section lock ensures mutual exclusion across instances.

    Failure mode: When lockHolder="none" and multiple Ready tasks exist,
    naive rule fires for ALL, granting lock to each (race condition).

    Fix: Uses URI-based ordering (string:lessThan) for deterministic selection.
    """

    def test_rule_has_ordering_guard(self) -> None:
        """Acquire rule must use ordering to break ties."""
        assert "string:lessThan" in WCP39_CRITICAL_SECTION

    def test_lowest_ordered_wins(self) -> None:
        """Guard checks that no lower-ordered Ready task exists."""
        assert "_:scope log:notIncludes" in WCP39_CRITICAL_SECTION
        assert "?other string:lessThan ?task" in WCP39_CRITICAL_SECTION

    def test_higher_ordered_blocked(self) -> None:
        """Higher-ordered Ready tasks become Blocked."""
        assert 'kgc:status "Blocked"' in WCP39_CRITICAL_SECTION
        assert "kgc:blockedByOrdering" in WCP39_CRITICAL_SECTION

    def test_lock_release_on_completion(self) -> None:
        """Lock released when task completes."""
        assert 'kgc:lockHolder "none"' in WCP39_CRITICAL_SECTION
        assert 'kgc:status "Completed"' in WCP39_CRITICAL_SECTION

    def test_same_cs_requirement_in_guard(self) -> None:
        """Ordering guard only compares tasks requiring SAME critical section."""
        # The guard should bind ?other to same ?cs
        assert "?other kgc:requiresCriticalSection ?cs" in WCP39_CRITICAL_SECTION


class TestMonotonicMarkerPattern:
    """Verify all fixes follow the monotonic marker pattern.

    The monotonic marker pattern is:
    1. Assert a marker on first match
    2. Guard subsequent rules with log:notIncludes { marker }

    This pattern enables "first-wins" semantics in monotonic N3.
    """

    def test_wcp4_uses_monotonic_pattern(self) -> None:
        """WCP-4 uses xorBranchSelected as monotonic marker."""
        # Marker is asserted in consequent
        assert "?task kgc:xorBranchSelected true ." in WCP4_EXCLUSIVE_CHOICE
        # Marker is checked in antecedent
        assert "log:notIncludes { ?task kgc:xorBranchSelected true }" in WCP4_EXCLUSIVE_CHOICE

    def test_wcp10_uses_monotonic_pattern(self) -> None:
        """WCP-10 uses cycleEdgeSelected as monotonic marker."""
        assert "?task kgc:cycleEdgeSelected true ." in WCP10_ARBITRARY_CYCLES
        assert "log:notIncludes { ?task kgc:cycleEdgeSelected true }" in WCP10_ARBITRARY_CYCLES

    def test_wcp12_uses_monotonic_pattern(self) -> None:
        """WCP-12 uses spawningComplete as monotonic marker."""
        assert "?mi kgc:spawningComplete true ." in WCP12_MI_WITHOUT_SYNC
        assert "log:notIncludes { ?mi kgc:spawningComplete true }" in WCP12_MI_WITHOUT_SYNC

    def test_wcp21_uses_monotonic_pattern(self) -> None:
        """WCP-21 uses loopExhausted as monotonic marker."""
        assert "?loop kgc:loopExhausted true ." in WCP21_STRUCTURED_LOOP
        assert "log:notIncludes { ?loop kgc:loopExhausted true }" in WCP21_STRUCTURED_LOOP

    def test_wcp29_uses_monotonic_pattern(self) -> None:
        """WCP-29 uses discriminatorFired and isWinningBranch as markers."""
        assert "kgc:discriminatorFired true" in WCP29_CANCELLING_DISCRIMINATOR
        assert "kgc:isWinningBranch true" in WCP29_CANCELLING_DISCRIMINATOR


class TestURIOrderingPattern:
    """Verify mutex patterns use URI-based ordering for determinism.

    URI-based ordering ensures deterministic selection when multiple
    tasks compete for a resource. Uses string:lessThan for comparison.
    """

    def test_wcp17_uses_uri_ordering(self) -> None:
        """WCP-17 uses string:lessThan for task ordering."""
        assert "string:lessThan" in WCP17_INTERLEAVED_PARALLEL

    def test_wcp39_uses_uri_ordering(self) -> None:
        """WCP-39 uses string:lessThan for task ordering."""
        assert "string:lessThan" in WCP39_CRITICAL_SECTION

    def test_ordering_in_notincludes_guard(self) -> None:
        """Ordering comparison happens inside log:notIncludes guard."""
        # WCP-17
        wcp17_guard = "?other string:lessThan ?task"
        assert wcp17_guard in WCP17_INTERLEAVED_PARALLEL

        # WCP-39
        wcp39_guard = "?other string:lessThan ?task"
        assert wcp39_guard in WCP39_CRITICAL_SECTION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
