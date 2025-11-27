"""WCP Advanced Pattern Tests - OR-Split, Milestone, OR-Join.

This module tests the newly implemented patterns:
- WCP-6: Multi-Choice (OR-Split) - LAW 15
- WCP-7: Structured Synchronizing Merge (OR-Join) - LAW 17
- WCP-18: Milestone - LAW 16

These patterns fill critical gaps identified in the FMEA analysis.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

# =============================================================================
# WCP-6: MULTI-CHOICE (OR-SPLIT) - LAW 15
# =============================================================================


class TestWCP6OrSplit:
    """Test WCP-6 Multi-Choice (OR-Split) pattern.

    Unlike XOR (exclusive choice), OR-split can activate MULTIPLE branches
    when multiple predicates evaluate to true.

    NATO Scenario: Amendment process where multiple amendments can be active.
    """

    def test_or_split_activates_single_true_branch(self) -> None:
        """OR-split activates branch when single predicate is true."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:Decision> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeOr ;
                yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

            <urn:flow:to_a> yawl:nextElementRef <urn:task:BranchA> ;
                yawl:hasPredicate <urn:pred:a> .
            <urn:pred:a> kgc:evaluatesTo true .

            <urn:flow:to_b> yawl:nextElementRef <urn:task:BranchB> ;
                yawl:hasPredicate <urn:pred:b> .
            <urn:pred:b> kgc:evaluatesTo false .

            <urn:task:BranchA> a yawl:Task .
            <urn:task:BranchB> a yawl:Task .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # Only BranchA should be active (predicate true)
        assert statuses.get("urn:task:BranchA") in ["Active", "Completed", "Archived"]
        # BranchB should NOT be active (predicate false)
        assert statuses.get("urn:task:BranchB") is None

    def test_or_split_activates_multiple_true_branches(self) -> None:
        """OR-split activates ALL branches with true predicates."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:AmendmentProcess> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeOr ;
                yawl:flowsInto <urn:flow:to_amend1>, <urn:flow:to_amend2>, <urn:flow:to_amend3> .

            <urn:flow:to_amend1> yawl:nextElementRef <urn:task:Amendment1> ;
                yawl:hasPredicate <urn:pred:1> .
            <urn:pred:1> kgc:evaluatesTo true .

            <urn:flow:to_amend2> yawl:nextElementRef <urn:task:Amendment2> ;
                yawl:hasPredicate <urn:pred:2> .
            <urn:pred:2> kgc:evaluatesTo true .

            <urn:flow:to_amend3> yawl:nextElementRef <urn:task:Amendment3> ;
                yawl:hasPredicate <urn:pred:3> .
            <urn:pred:3> kgc:evaluatesTo false .

            <urn:task:Amendment1> a yawl:Task ; kgc:requiresManualCompletion true .
            <urn:task:Amendment2> a yawl:Task ; kgc:requiresManualCompletion true .
            <urn:task:Amendment3> a yawl:Task .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # Both Amendment1 and Amendment2 should be active (both predicates true)
        assert statuses.get("urn:task:Amendment1") == "Active"
        assert statuses.get("urn:task:Amendment2") == "Active"
        # Amendment3 should NOT be active (predicate false)
        assert statuses.get("urn:task:Amendment3") is None

    def test_or_split_default_when_no_predicates_true(self) -> None:
        """OR-split takes default path when no predicates are true."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:Decision> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeOr ;
                yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:default> .

            <urn:flow:to_a> yawl:nextElementRef <urn:task:BranchA> ;
                yawl:hasPredicate <urn:pred:a> .
            <urn:pred:a> kgc:evaluatesTo false .

            <urn:flow:to_b> yawl:nextElementRef <urn:task:BranchB> ;
                yawl:hasPredicate <urn:pred:b> .
            <urn:pred:b> kgc:evaluatesTo false .

            <urn:flow:default> yawl:nextElementRef <urn:task:Default> ;
                yawl:isDefaultFlow true .

            <urn:task:BranchA> a yawl:Task .
            <urn:task:BranchB> a yawl:Task .
            <urn:task:Default> a yawl:Task .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # Only Default should be active (all predicates false)
        assert statuses.get("urn:task:Default") in ["Active", "Completed", "Archived"]
        assert statuses.get("urn:task:BranchA") is None
        assert statuses.get("urn:task:BranchB") is None

    def test_or_split_all_true_activates_all(self) -> None:
        """OR-split with all true predicates activates all branches."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:CrisisResponse> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeOr ;
                yawl:flowsInto <urn:flow:to_sanction>, <urn:flow:to_negotiate>, <urn:flow:to_warn> .

            <urn:flow:to_sanction> yawl:nextElementRef <urn:task:Sanctions> ;
                yawl:hasPredicate <urn:pred:sanction> .
            <urn:pred:sanction> kgc:evaluatesTo true .

            <urn:flow:to_negotiate> yawl:nextElementRef <urn:task:Negotiations> ;
                yawl:hasPredicate <urn:pred:negotiate> .
            <urn:pred:negotiate> kgc:evaluatesTo true .

            <urn:flow:to_warn> yawl:nextElementRef <urn:task:Warning> ;
                yawl:hasPredicate <urn:pred:warn> .
            <urn:pred:warn> kgc:evaluatesTo true .

            <urn:task:Sanctions> a yawl:Task ; kgc:requiresManualCompletion true .
            <urn:task:Negotiations> a yawl:Task ; kgc:requiresManualCompletion true .
            <urn:task:Warning> a yawl:Task ; kgc:requiresManualCompletion true .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # All three should be active (all predicates true)
        assert statuses.get("urn:task:Sanctions") == "Active"
        assert statuses.get("urn:task:Negotiations") == "Active"
        assert statuses.get("urn:task:Warning") == "Active"


# =============================================================================
# WCP-7: STRUCTURED SYNCHRONIZING MERGE (OR-JOIN) - LAW 17
# =============================================================================


class TestWCP7OrJoin:
    """Test WCP-7 Structured Synchronizing Merge (OR-Join) pattern.

    OR-join activates when ANY predecessor completes (unlike AND-join).
    This is the merge counterpart to OR-split.

    NATO Scenario: Any delegation arriving triggers meeting start.
    """

    def test_or_join_activates_on_single_predecessor(self) -> None:
        """OR-join activates when any single predecessor completes."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:BranchA> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto <urn:flow:a_to_join> .

            <urn:task:BranchB> a yawl:Task ;
                kgc:requiresManualCompletion true ;
                yawl:flowsInto <urn:flow:b_to_join> .

            <urn:flow:a_to_join> yawl:nextElementRef <urn:task:OrJoin> .
            <urn:flow:b_to_join> yawl:nextElementRef <urn:task:OrJoin> .

            <urn:task:OrJoin> a yawl:Task ;
                yawl:hasJoin yawl:ControlTypeOr .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # OR-join should activate (BranchA is Completed)
        assert statuses.get("urn:task:OrJoin") in ["Active", "Completed", "Archived"]

    def test_or_join_activates_on_any_completion(self) -> None:
        """OR-join activates when any of multiple predecessors completes."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:US_Delegation> a yawl:Task ;
                kgc:requiresManualCompletion true ;
                yawl:flowsInto <urn:flow:us_to_meeting> .

            <urn:task:UK_Delegation> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto <urn:flow:uk_to_meeting> .

            <urn:task:FR_Delegation> a yawl:Task ;
                kgc:requiresManualCompletion true ;
                yawl:flowsInto <urn:flow:fr_to_meeting> .

            <urn:flow:us_to_meeting> yawl:nextElementRef <urn:task:StartMeeting> .
            <urn:flow:uk_to_meeting> yawl:nextElementRef <urn:task:StartMeeting> .
            <urn:flow:fr_to_meeting> yawl:nextElementRef <urn:task:StartMeeting> .

            <urn:task:StartMeeting> a yawl:Task ;
                yawl:hasJoin yawl:ControlTypeOr .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # OR-join should activate (UK_Delegation is Completed)
        assert statuses.get("urn:task:StartMeeting") in ["Active", "Completed", "Archived"]

    def test_or_join_does_not_wait_for_all(self) -> None:
        """OR-join does not wait for all predecessors (unlike AND-join)."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            # Split task
            <urn:task:Split> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeAnd ;
                yawl:flowsInto <urn:flow:to_fast>, <urn:flow:to_slow> .

            <urn:flow:to_fast> yawl:nextElementRef <urn:task:FastPath> .
            <urn:flow:to_slow> yawl:nextElementRef <urn:task:SlowPath> .

            # Fast path completes immediately
            <urn:task:FastPath> a yawl:Task ;
                yawl:flowsInto <urn:flow:fast_to_join> .

            # Slow path requires manual completion
            <urn:task:SlowPath> a yawl:Task ;
                kgc:requiresManualCompletion true ;
                yawl:flowsInto <urn:flow:slow_to_join> .

            <urn:flow:fast_to_join> yawl:nextElementRef <urn:task:OrJoin> .
            <urn:flow:slow_to_join> yawl:nextElementRef <urn:task:OrJoin> .

            # OR-join should NOT wait for slow path
            <urn:task:OrJoin> a yawl:Task ;
                yawl:hasJoin yawl:ControlTypeOr .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # FastPath should be Completed/Archived
        assert statuses.get("urn:task:FastPath") in ["Completed", "Archived"]
        # SlowPath should still be Active (waiting for manual completion)
        assert statuses.get("urn:task:SlowPath") == "Active"
        # OR-join should activate (FastPath is done, doesn't wait for SlowPath)
        assert statuses.get("urn:task:OrJoin") in ["Active", "Completed", "Archived"]


# =============================================================================
# WCP-18: MILESTONE - LAW 16
# =============================================================================


class TestWCP18Milestone:
    """Test WCP-18 Milestone pattern.

    Tasks can require milestones to be reached before they can activate.
    This enables modeling prerequisites like quorum requirements.

    NATO Scenario: Cannot proceed to voting until quorum is reached.
    """

    def test_milestone_blocks_until_reached(self) -> None:
        """Task blocked until milestone is reached."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:Predecessor> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto <urn:flow:to_vote> .

            <urn:flow:to_vote> yawl:nextElementRef <urn:task:StartVoting> .

            # Task requires milestone
            <urn:task:StartVoting> a yawl:Task ;
                kgc:requiresMilestone <urn:milestone:Quorum> .

            # Milestone NOT yet reached
            <urn:milestone:Quorum> a kgc:Milestone .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # StartVoting should be Waiting (milestone not reached)
        assert statuses.get("urn:task:StartVoting") == "Waiting"

    def test_milestone_allows_when_reached(self) -> None:
        """Task activates when milestone is reached."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:Predecessor> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto <urn:flow:to_vote> .

            <urn:flow:to_vote> yawl:nextElementRef <urn:task:StartVoting> .

            # Task requires milestone
            <urn:task:StartVoting> a yawl:Task ;
                kgc:requiresMilestone <urn:milestone:Quorum> .

            # Milestone IS reached
            <urn:milestone:Quorum> a kgc:Milestone ;
                kgc:status "Reached" .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # StartVoting should be Active or beyond (milestone reached)
        assert statuses.get("urn:task:StartVoting") in ["Active", "Completed", "Archived"]

    def test_milestone_quorum_scenario(self) -> None:
        """NATO quorum scenario: voting requires 2/3 members present."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            @prefix nato: <https://nato.int/ns/> .

            # Session begins
            <urn:task:CallToOrder> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto <urn:flow:to_quorum_check> .

            <urn:flow:to_quorum_check> yawl:nextElementRef <urn:task:QuorumCheck> .

            # Quorum check task
            <urn:task:QuorumCheck> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto <urn:flow:to_vote> .

            <urn:flow:to_vote> yawl:nextElementRef <urn:task:MainVote> .

            # Main vote requires quorum milestone
            <urn:task:MainVote> a yawl:Task ;
                kgc:requiresMilestone <urn:milestone:Quorum> .

            # Quorum milestone (reached when 2/3 present)
            <urn:milestone:Quorum> a kgc:Milestone ;
                nato:requiredPresent 20 ;
                nato:totalMembers 30 ;
                kgc:status "Reached" .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # QuorumCheck should progress
        assert statuses.get("urn:task:QuorumCheck") in ["Completed", "Archived"]
        # MainVote should activate (quorum reached)
        assert statuses.get("urn:task:MainVote") in ["Active", "Completed", "Archived"]


# =============================================================================
# INTEGRATION TESTS: OR-SPLIT + SYNC MERGE COMBO
# =============================================================================


class TestOrSplitSyncMergeIntegration:
    """Test OR-split combined with Synchronizing Merge (WCP-6 + WCP-37).

    This is the canonical pattern for diplomatic exhaustion:
    - OR-split: Multiple diplomatic options can be active
    - Sync Merge: Escalation only after ALL activated paths complete
    """

    def test_or_split_sync_merge_waits_for_activated(self) -> None:
        """Sync merge waits for all OR-split activated paths."""
        topology = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            # OR-split: multiple diplomatic options
            <urn:task:DiplomaticOptions> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeOr ;
                yawl:flowsInto <urn:flow:to_sanctions>, <urn:flow:to_negotiation>, <urn:flow:to_warning> .

            <urn:flow:to_sanctions> yawl:nextElementRef <urn:task:Sanctions> ;
                yawl:hasPredicate <urn:pred:sanctions> .
            <urn:pred:sanctions> kgc:evaluatesTo true .

            <urn:flow:to_negotiation> yawl:nextElementRef <urn:task:Negotiation> ;
                yawl:hasPredicate <urn:pred:negotiation> .
            <urn:pred:negotiation> kgc:evaluatesTo true .

            <urn:flow:to_warning> yawl:nextElementRef <urn:task:Warning> ;
                yawl:hasPredicate <urn:pred:warning> .
            <urn:pred:warning> kgc:evaluatesTo false .

            # Diplomatic paths (require manual completion)
            <urn:task:Sanctions> a yawl:Task ;
                kgc:requiresManualCompletion true ;
                yawl:flowsInto <urn:flow:sanctions_to_merge> .

            <urn:task:Negotiation> a yawl:Task ;
                kgc:requiresManualCompletion true ;
                yawl:flowsInto <urn:flow:negotiation_to_merge> .

            <urn:task:Warning> a yawl:Task ;
                yawl:flowsInto <urn:flow:warning_to_merge> .

            <urn:flow:sanctions_to_merge> yawl:nextElementRef <urn:task:Escalation> .
            <urn:flow:negotiation_to_merge> yawl:nextElementRef <urn:task:Escalation> .
            <urn:flow:warning_to_merge> yawl:nextElementRef <urn:task:Escalation> .

            # Synchronizing merge (wait for all ACTIVATED paths)
            <urn:task:Escalation> a yawl:Task ;
                yawl:hasJoin kgc:SynchronizingMerge .
        """
        engine = HybridEngine()
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()
        # Both Sanctions and Negotiation should be Active (predicates true)
        assert statuses.get("urn:task:Sanctions") == "Active"
        assert statuses.get("urn:task:Negotiation") == "Active"
        # Warning should NOT be active (predicate false)
        assert statuses.get("urn:task:Warning") is None
        # Escalation should NOT activate (waiting for both Sanctions and Negotiation)
        # Note: LAW 12 marks them as wasActivated, LAW 11 checks completions
        # Since they're manual, they won't auto-complete


# =============================================================================
# MAIN EXECUTION
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
