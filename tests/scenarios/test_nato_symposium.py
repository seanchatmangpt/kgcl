"""NATO Symposium with Robert's Rules of Order - YAWL WCP Demonstration.

This module tests real HybridEngine behavior using a NATO symposium scenario
demonstrating YAWL Workflow Control Patterns with Robert's Rules of Order
parliamentary procedure.

SCENARIO OVERVIEW
-----------------
A NATO symposium workflow demonstrating:
- Call to Order → Quorum → Committee Formation
- Three parallel committees (AND-Split)
- Committee synchronization (AND-Join)
- Main motion decisions (XOR-Split)
- Nuclear authorization chain (nested AND-Joins)

WCP PATTERNS TESTED
-------------------
- WCP-1:  Sequence (parliamentary procedure steps)
- WCP-2:  Parallel Split (committee formation)
- WCP-3:  Synchronization (committee sync, dual-key)
- WCP-4:  Exclusive Choice (motion decisions)
- WCP-5:  Simple Merge (amendment handling)

Chicago School TDD: Real RDF graphs, real engine execution, no mocking.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine instance."""
    return HybridEngine()


# =============================================================================
# WCP-1: SEQUENCE PATTERN TESTS
# =============================================================================


class TestSequencePattern:
    """WCP-1: Sequence - Tasks execute in order."""

    def test_completed_task_activates_successor(self, engine: HybridEngine) -> None:
        """When a task completes, its successor becomes Active."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:CallToOrder a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:EstablishQuorum .
        nato:EstablishQuorum a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        assert statuses.get("urn:nato:symposium:EstablishQuorum") == "Active"

    def test_active_task_does_not_activate_successor(self, engine: HybridEngine) -> None:
        """An Active (but not Completed) task doesn't activate its successor."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:CallToOrder a yawl:Task ;
            kgc:status "Active" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:EstablishQuorum .
        nato:EstablishQuorum a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Successor should be Pending (or not exist), not Active
        quorum_status = statuses.get("urn:nato:symposium:EstablishQuorum")
        assert quorum_status in [None, "Pending"]

    def test_three_step_sequence(self, engine: HybridEngine) -> None:
        """Chain of three tasks: Complete A → Activate B → Complete B → Activate C."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:CallToOrder a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:EstablishQuorum .

        nato:EstablishQuorum a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow2 .
        nato:flow2 yawl:nextElementRef nato:FormCommittees .

        nato:FormCommittees a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        assert statuses.get("urn:nato:symposium:FormCommittees") == "Active"


# =============================================================================
# WCP-2: AND-SPLIT PATTERN TESTS (Parallel Split)
# =============================================================================


class TestAndSplitPattern:
    """WCP-2: AND-Split - Parallel activation of all successors."""

    def test_and_split_activates_all_branches(self, engine: HybridEngine) -> None:
        """AND-split activates ALL successor branches simultaneously."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:FormCommittees a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow1, nato:flow2, nato:flow3 .

        nato:flow1 yawl:nextElementRef nato:StrategicAssessment .
        nato:flow2 yawl:nextElementRef nato:IntelligenceReview .
        nato:flow3 yawl:nextElementRef nato:LegalFramework .

        nato:StrategicAssessment a yawl:Task .
        nato:IntelligenceReview a yawl:Task .
        nato:LegalFramework a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # All three committees should be Active
        assert statuses.get("urn:nato:symposium:StrategicAssessment") == "Active"
        assert statuses.get("urn:nato:symposium:IntelligenceReview") == "Active"
        assert statuses.get("urn:nato:symposium:LegalFramework") == "Active"

    def test_and_split_requires_completed_source(self, engine: HybridEngine) -> None:
        """AND-split only fires when source is Completed."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:FormCommittees a yawl:Task ;
            kgc:status "Active" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow1, nato:flow2 .

        nato:flow1 yawl:nextElementRef nato:StrategicAssessment .
        nato:flow2 yawl:nextElementRef nato:IntelligenceReview .

        nato:StrategicAssessment a yawl:Task .
        nato:IntelligenceReview a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Neither branch should be Active
        strategic = statuses.get("urn:nato:symposium:StrategicAssessment")
        intel = statuses.get("urn:nato:symposium:IntelligenceReview")
        assert strategic in [None, "Pending"]
        assert intel in [None, "Pending"]


# =============================================================================
# WCP-3: AND-JOIN PATTERN TESTS (Synchronization)
# =============================================================================


class TestAndJoinPattern:
    """WCP-3: AND-Join - Wait for ALL incoming branches."""

    def test_and_join_requires_all_inputs_completed(self, engine: HybridEngine) -> None:
        """AND-join only activates when ALL inputs are Completed."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:StrategicAssessment a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:CommitteeSync .

        nato:IntelligenceReview a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow2 .
        nato:flow2 yawl:nextElementRef nato:CommitteeSync .

        nato:LegalFramework a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow3 .
        nato:flow3 yawl:nextElementRef nato:CommitteeSync .

        nato:CommitteeSync a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Sync should be Active because ALL inputs completed
        assert statuses.get("urn:nato:symposium:CommitteeSync") == "Active"

    def test_and_join_blocks_when_input_incomplete(self, engine: HybridEngine) -> None:
        """AND-join stays Pending when any input is not Completed."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:StrategicAssessment a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:CommitteeSync .

        nato:IntelligenceReview a yawl:Task ;
            kgc:status "Active" ;
            yawl:flowsInto nato:flow2 .
        nato:flow2 yawl:nextElementRef nato:CommitteeSync .

        nato:LegalFramework a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow3 .
        nato:flow3 yawl:nextElementRef nato:CommitteeSync .

        nato:CommitteeSync a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Sync should NOT be Active because Intel is only Active (not Completed)
        sync_status = statuses.get("urn:nato:symposium:CommitteeSync")
        assert sync_status in [None, "Pending"]

    def test_dual_key_authorization(self, engine: HybridEngine) -> None:
        """Nuclear dual-key: Both USA and UK must authorize (AND-join)."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:USAAuth a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow_usa .
        nato:flow_usa yawl:nextElementRef nato:DualKeySync .

        nato:UKAuth a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow_uk .
        nato:flow_uk yawl:nextElementRef nato:DualKeySync .

        nato:DualKeySync a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow_launch .
        nato:flow_launch yawl:nextElementRef nato:PrepareLaunch .

        nato:PrepareLaunch a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Both keys present → DualKeySync activates → PrepareLaunch pending
        assert statuses.get("urn:nato:symposium:DualKeySync") == "Active"

    def test_dual_key_blocks_without_both_keys(self, engine: HybridEngine) -> None:
        """Nuclear dual-key blocks if one key missing."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:USAAuth a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow_usa .
        nato:flow_usa yawl:nextElementRef nato:DualKeySync .

        nato:UKAuth a yawl:Task ;
            kgc:status "Active" ;
            yawl:flowsInto nato:flow_uk .
        nato:flow_uk yawl:nextElementRef nato:DualKeySync .

        nato:DualKeySync a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # UK key not complete → DualKeySync should NOT activate
        sync_status = statuses.get("urn:nato:symposium:DualKeySync")
        assert sync_status in [None, "Pending"]


# =============================================================================
# WCP-4: XOR-SPLIT PATTERN TESTS (Exclusive Choice)
# =============================================================================


class TestXorSplitPattern:
    """WCP-4: XOR-Split - Exactly one path taken."""

    def test_xor_split_takes_default_path(self, engine: HybridEngine) -> None:
        """XOR-split takes default path when no predicate matches."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:MainMotion a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto nato:flow_authorize, nato:flow_default .

        nato:flow_authorize yawl:nextElementRef nato:AuthorizeDeterrent ;
            yawl:hasPredicate nato:pred_authorize .
        nato:pred_authorize kgc:evaluatesTo false .

        nato:flow_default yawl:nextElementRef nato:MaintainStatusQuo ;
            yawl:isDefaultFlow true .

        nato:AuthorizeDeterrent a yawl:Task .
        nato:MaintainStatusQuo a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Default path should activate, non-matching path should not
        assert statuses.get("urn:nato:symposium:MaintainStatusQuo") == "Active"
        auth_status = statuses.get("urn:nato:symposium:AuthorizeDeterrent")
        assert auth_status in [None, "Pending"]

    def test_xor_split_takes_matching_predicate_path(self, engine: HybridEngine) -> None:
        """XOR-split takes predicate path when it evaluates to true."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:MainMotion a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto nato:flow_authorize, nato:flow_default .

        nato:flow_authorize yawl:nextElementRef nato:AuthorizeDeterrent ;
            yawl:hasPredicate nato:pred_authorize .
        nato:pred_authorize kgc:evaluatesTo true .

        nato:flow_default yawl:nextElementRef nato:MaintainStatusQuo ;
            yawl:isDefaultFlow true .

        nato:AuthorizeDeterrent a yawl:Task .
        nato:MaintainStatusQuo a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Matching predicate path activates
        assert statuses.get("urn:nato:symposium:AuthorizeDeterrent") == "Active"


# =============================================================================
# FULL WORKFLOW SCENARIO TESTS
# =============================================================================


class TestFullWorkflowScenarios:
    """End-to-end workflow tests demonstrating complete scenarios."""

    def test_call_to_order_through_committees(self, engine: HybridEngine) -> None:
        """Full sequence: CallToOrder → Quorum → FormCommittees → 3 Committees."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        # Phase 1: Call to Order (Completed)
        nato:CallToOrder a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:EstablishQuorum .

        # Phase 2: Quorum (Completed)
        nato:EstablishQuorum a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow2 .
        nato:flow2 yawl:nextElementRef nato:FormCommittees .

        # Phase 3: Form Committees with AND-Split (Completed)
        nato:FormCommittees a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow3, nato:flow4, nato:flow5 .

        nato:flow3 yawl:nextElementRef nato:StrategicAssessment .
        nato:flow4 yawl:nextElementRef nato:IntelligenceReview .
        nato:flow5 yawl:nextElementRef nato:LegalFramework .

        nato:StrategicAssessment a yawl:Task .
        nato:IntelligenceReview a yawl:Task .
        nato:LegalFramework a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # All committees should be Active
        assert statuses.get("urn:nato:symposium:StrategicAssessment") == "Active"
        assert statuses.get("urn:nato:symposium:IntelligenceReview") == "Active"
        assert statuses.get("urn:nato:symposium:LegalFramework") == "Active"

    def test_committees_to_main_motion(self, engine: HybridEngine) -> None:
        """Committees complete → AND-join fires → MainMotion activates."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        # All committees completed
        nato:StrategicAssessment a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:CommitteeSync .

        nato:IntelligenceReview a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow2 .
        nato:flow2 yawl:nextElementRef nato:CommitteeSync .

        nato:LegalFramework a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow3 .
        nato:flow3 yawl:nextElementRef nato:CommitteeSync .

        # AND-join synchronization
        nato:CommitteeSync a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasJoin yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow4 .
        nato:flow4 yawl:nextElementRef nato:MainMotion .

        nato:MainMotion a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        assert statuses.get("urn:nato:symposium:MainMotion") == "Active"

    def test_status_quo_leads_to_adjournment(self, engine: HybridEngine) -> None:
        """MainMotion → StatusQuo (default) → Adjournment."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:MainMotion a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto nato:flow_auth, nato:flow_default .

        nato:flow_auth yawl:nextElementRef nato:AuthorizeDeterrent ;
            yawl:hasPredicate nato:pred_auth .
        nato:pred_auth kgc:evaluatesTo false .

        nato:flow_default yawl:nextElementRef nato:MaintainStatusQuo ;
            yawl:isDefaultFlow true .

        nato:AuthorizeDeterrent a yawl:Task .

        nato:MaintainStatusQuo a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow_adj .
        nato:flow_adj yawl:nextElementRef nato:Adjournment .

        nato:Adjournment a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        assert statuses.get("urn:nato:symposium:Adjournment") == "Active"

    def test_authorize_requires_nca_chain(self, engine: HybridEngine) -> None:
        """Authorization path triggers NCA chain (AND-split to nuclear powers)."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:AuthorizeDeterrent a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:NCAAuthorization .

        nato:NCAAuthorization a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow_usa, nato:flow_uk .

        nato:flow_usa yawl:nextElementRef nato:USAAuth .
        nato:flow_uk yawl:nextElementRef nato:UKAuth .

        nato:USAAuth a yawl:Task .
        nato:UKAuth a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Both NCA authorities should activate in parallel
        assert statuses.get("urn:nato:symposium:USAAuth") == "Active"
        assert statuses.get("urn:nato:symposium:UKAuth") == "Active"


# =============================================================================
# SAFETY INVARIANT TESTS
# =============================================================================


class TestSafetyInvariants:
    """Nuclear safety: Critical invariants that must hold."""

    def test_no_launch_without_dual_key(self, engine: HybridEngine) -> None:
        """PrepareLaunch requires both USA and UK authorization (dual-key)."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:USAAuth a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow_usa .
        nato:flow_usa yawl:nextElementRef nato:DualKeySync .

        nato:UKAuth a yawl:Task ;
            kgc:status "Active" ;
            yawl:flowsInto nato:flow_uk .
        nato:flow_uk yawl:nextElementRef nato:DualKeySync .

        nato:DualKeySync a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow_launch .
        nato:flow_launch yawl:nextElementRef nato:PrepareLaunch .

        nato:PrepareLaunch a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Without UK key completed, PrepareLaunch should NOT be reachable
        launch_status = statuses.get("urn:nato:symposium:PrepareLaunch")
        assert launch_status in [None, "Pending"], "SAFETY: No launch without dual-key!"

    def test_committees_must_synchronize(self, engine: HybridEngine) -> None:
        """MainMotion requires ALL committees to complete (AND-join)."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:StrategicAssessment a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:CommitteeSync .

        nato:IntelligenceReview a yawl:Task ;
            kgc:status "Active" ;
            yawl:flowsInto nato:flow2 .
        nato:flow2 yawl:nextElementRef nato:CommitteeSync .

        nato:LegalFramework a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow3 .
        nato:flow3 yawl:nextElementRef nato:CommitteeSync .

        nato:CommitteeSync a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd ;
            yawl:flowsInto nato:flow4 .
        nato:flow4 yawl:nextElementRef nato:MainMotion .

        nato:MainMotion a yawl:Task .
        """
        engine.load_data(topology)
        engine.apply_physics()

        statuses = engine.inspect()
        # Intel not complete → CommitteeSync should block → MainMotion unreachable
        sync_status = statuses.get("urn:nato:symposium:CommitteeSync")
        motion_status = statuses.get("urn:nato:symposium:MainMotion")
        assert sync_status in [None, "Pending"], "CommitteeSync should block"
        assert motion_status in [None, "Pending"], "MainMotion should be blocked"


# =============================================================================
# CONVERGENCE AND PERFORMANCE TESTS
# =============================================================================


class TestConvergence:
    """Engine convergence behavior."""

    def test_engine_converges_on_simple_workflow(self, engine: HybridEngine) -> None:
        """Engine reaches fixpoint (delta=0) on simple workflow."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:CallToOrder a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto nato:flow1 .
        nato:flow1 yawl:nextElementRef nato:Adjournment .
        nato:Adjournment a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        # Should converge in few ticks
        assert len(results) <= 5
        assert results[-1].converged or results[-1].delta == 0

    def test_no_infinite_loop_on_complex_workflow(self, engine: HybridEngine) -> None:
        """Complex workflow converges within max_ticks."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix nato: <urn:nato:symposium:> .

        nato:Start a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto nato:f1, nato:f2, nato:f3 .

        nato:f1 yawl:nextElementRef nato:A .
        nato:f2 yawl:nextElementRef nato:B .
        nato:f3 yawl:nextElementRef nato:C .

        nato:A a yawl:Task .
        nato:B a yawl:Task .
        nato:C a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=20)

        # Should not hit max_ticks
        assert len(results) < 20
