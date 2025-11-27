"""Comprehensive test suite for Nuclear Launch validation scenario.

This module tests all YAWL Workflow Control Patterns (WCP) using a nuclear
launch authorization workflow as a comprehensive validation scenario.

The workflow demonstrates:
- WCP-1: Sequence (Start → DualKeyCheck → Auth → Sync → Decision → Launch/Abort → End)
- WCP-2: Parallel Split (DualKeyCheck → CommanderAuth + DeputyAuth)
- WCP-3: Synchronization (CommanderAuth + DeputyAuth → DualKeySync)
- WCP-4: Exclusive Choice (DualKeySync → ArmWarhead OR AbortSequence)
- WCP-5: Simple Merge (Multiple paths → End)

The scenario tests safety-critical workflow properties:
- Dual authorization required (both Commander AND Deputy must authorize)
- Abort signal preempts launch sequence
- Timeout protection (if countdown exceeds limit, abort)
- No dual launch/abort (exactly one terminal state)
- Fixed-point convergence (all scenarios terminate)

Follows Chicago School TDD: real RDF graphs, no mocking of domain logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib import Namespace

from kgcl.hybrid.hybrid_engine import HybridEngine

if TYPE_CHECKING:
    pass

# Test namespaces
KGC = Namespace("https://kgc.org/ns/")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
NUC = Namespace("urn:nuclear:launch:")


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine instance.

    Returns
    -------
    HybridEngine
        Fresh engine with in-memory PyOxigraph store.
    """
    return HybridEngine()


@pytest.fixture
def nuclear_physics_rules() -> str:
    """N3 physics rules for nuclear launch workflow.

    These rules implement the YAWL workflow control patterns for the
    nuclear launch authorization process.

    Returns
    -------
    str
        N3 rules in Turtle format implementing WCP patterns.
    """
    return """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .
@prefix log: <http://www.w3.org/2000/10/swap/log#> .

# --- WCP-1: SEQUENCE (Basic Flow) ---
# When task completes and flows to next, activate next task
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?next kgc:status "Active" .
} .

# --- WCP-2: PARALLEL SPLIT (AND-split) ---
# When task with AND-split completes, activate ALL outgoing tasks
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeAnd .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?next kgc:status "Active" .
} .

# --- WCP-3: SYNCHRONIZATION (AND-join) ---
# When task has AND-join, activate ONLY when ALL incoming tasks completed
# This is simplified: check if both inputs exist and are completed
{
    ?task yawl:hasJoin yawl:ControlTypeAnd .
    ?flow1 yawl:nextElementRef ?task .
    ?flow2 yawl:nextElementRef ?task .
    ?task1 yawl:flowsInto ?flow1 .
    ?task2 yawl:flowsInto ?flow2 .
    ?task1 kgc:status "Completed" .
    ?task2 kgc:status "Completed" .
}
=>
{
    ?task kgc:status "Active" .
} .

# Complete sync task when activated
{
    ?task yawl:hasJoin yawl:ControlTypeAnd .
    ?task kgc:status "Active" .
}
=>
{
    ?task kgc:status "Completed" .
} .

# --- WCP-4: EXCLUSIVE CHOICE (XOR-split) ---
# When XOR task completes, select ONE path based on predicate
# Path 1: Abort signal present → AbortSequence
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeXor .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:hasPredicate ?pred .
    ?pred kgc:evaluatesTo true .
}
=>
{
    ?next kgc:status "Active" .
} .

# Path 2: No abort → default flow (ArmWarhead)
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeXor .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:isDefaultFlow true .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?next kgc:status "Active" .
} .

# --- WCP-5: SIMPLE MERGE (Multiple paths to End) ---
# Any completed terminal task activates End
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef nuc:End .
}
=>
{
    nuc:End kgc:status "Active" .
} .

# --- TASK AUTO-COMPLETION ---
# Simple tasks auto-complete when activated
{
    ?task kgc:status "Active" .
    ?task a yawl:Task .
}
=>
{
    ?task kgc:status "Completed" .
} .

# --- CLEANUP (Archive completed tasks after successors activate) ---
{
    ?next kgc:status "Active" .
    ?prev yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?prev kgc:status "Completed" .
}
=>
{
    ?prev kgc:status "Archived" .
} .
"""


@pytest.fixture
def abort_topology() -> str:
    """Nuclear launch topology with abort signal present.

    This topology represents the abort scenario where the abort signal
    is detected, causing the XOR-split to select the abort path.

    Returns
    -------
    str
        Turtle topology with abort signal active.
    """
    return """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

# Initial state
nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

# DualKeyCheck (WCP-2: AND-split to Commander + Deputy)
nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

nuc:CommanderAuth a yawl:Task .
nuc:DeputyAuth a yawl:Task .

# DualKeySync (WCP-3: AND-join waiting for both auth)
nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

# XOR-split (WCP-4: Abort signal detected)
nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo true .  # ABORT SIGNAL PRESENT

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

# Terminal tasks
nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .

nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""


@pytest.fixture
def launch_topology() -> str:
    """Nuclear launch topology with NO abort signal (proceed to launch).

    This topology represents the launch scenario where no abort signal
    is present, causing the XOR-split to select the default launch path.

    Returns
    -------
    str
        Turtle topology without abort signal.
    """
    return """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

# Initial state
nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

# DualKeyCheck (WCP-2: AND-split to Commander + Deputy)
nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

nuc:CommanderAuth a yawl:Task .
nuc:DeputyAuth a yawl:Task .

# DualKeySync (WCP-3: AND-join waiting for both auth)
nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

# XOR-split (WCP-4: NO abort signal, use default path)
nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .  # NO ABORT SIGNAL

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

# Terminal tasks
nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .

nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""


@pytest.fixture
def abort_scenario(engine: HybridEngine, nuclear_physics_rules: str, abort_topology: str) -> HybridEngine:
    """Engine loaded with abort scenario (abort signal present).

    Parameters
    ----------
    engine : HybridEngine
        Fresh engine instance.
    nuclear_physics_rules : str
        N3 physics rules.
    abort_topology : str
        Topology with abort signal.

    Returns
    -------
    HybridEngine
        Engine ready to execute abort scenario.
    """
    # Note: HybridEngine uses load_data() not load_ontology/load_topology
    # and runs with apply_physics() not tick()
    engine.load_data(abort_topology)
    # Physics rules are built-in to HybridEngine (N3_PHYSICS constant)
    # This fixture provides topology only
    return engine


@pytest.fixture
def launch_scenario(engine: HybridEngine, nuclear_physics_rules: str, launch_topology: str) -> HybridEngine:
    """Engine loaded with launch scenario (no abort signal).

    Parameters
    ----------
    engine : HybridEngine
        Fresh engine instance.
    nuclear_physics_rules : str
        N3 physics rules.
    launch_topology : str
        Topology without abort signal.

    Returns
    -------
    HybridEngine
        Engine ready to execute launch scenario.
    """
    engine.load_data(launch_topology)
    return engine


# =============================================================================
# PHASE TESTS (Verify each workflow phase)
# =============================================================================


def test_phase1_start_to_dualkey(engine: HybridEngine, abort_topology: str) -> None:
    """WCP-1: Sequence from Start activates DualKeyCheck.

    Arrange:
        - Load topology with Start task completed
    Act:
        - Execute physics (EYE computes deductive closure)
    Assert:
        - DualKeyCheck was activated (may have progressed to Completed/Archived)

    Note: EYE computes full deductive closure, so task may progress past Active
    in a single tick. We verify it WAS activated by checking for any status.
    """
    engine.load_data(abort_topology)

    # Apply physics - EYE computes full closure
    result = engine.apply_physics()

    # Verify Start flowed to DualKeyCheck (task was activated, may have progressed)
    statuses = engine.inspect()
    assert statuses.get("urn:nuclear:launch:DualKeyCheck") in ["Active", "Completed", "Archived"]


def test_phase2_parallel_split(engine: HybridEngine, abort_topology: str) -> None:
    """WCP-2: DualKeyCheck splits to Commander AND Deputy auth.

    Arrange:
        - DualKeyCheck is Completed (simulate)
    Act:
        - Apply physics (EYE computes deductive closure)
    Assert:
        - Both CommanderAuth AND DeputyAuth were activated

    Note: EYE computes full deductive closure, so tasks may progress past Active.
    """
    # Modify topology to have DualKeyCheck completed
    topology = abort_topology.replace(
        "nuc:DualKeyCheck a yawl:Task ;", 'nuc:DualKeyCheck a yawl:Task ;\n    kgc:status "Completed" ;'
    )
    engine.load_data(topology)

    result = engine.apply_physics()

    # Both auth tasks should be activated (parallel split - may have progressed)
    statuses = engine.inspect()
    assert statuses.get("urn:nuclear:launch:CommanderAuth") in ["Active", "Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:DeputyAuth") in ["Active", "Completed", "Archived"]


def test_phase3_synchronization(engine: HybridEngine, abort_topology: str) -> None:
    """WCP-3: DualKeySync waits for BOTH auth completions.

    Arrange:
        - Both CommanderAuth and DeputyAuth Completed
    Act:
        - Apply physics (EYE computes deductive closure)
    Assert:
        - DualKeySync was activated (AND-join satisfied)

    Note: EYE computes full deductive closure, so task may progress past Active.
    """
    # Modify topology: both auth tasks completed
    topology = abort_topology.replace(
        "nuc:CommanderAuth a yawl:Task .", 'nuc:CommanderAuth a yawl:Task ;\n    kgc:status "Completed" .'
    ).replace("nuc:DeputyAuth a yawl:Task .", 'nuc:DeputyAuth a yawl:Task ;\n    kgc:status "Completed" .')
    engine.load_data(topology)

    result = engine.apply_physics()

    # Sync task should activate when both inputs completed (may have progressed)
    statuses = engine.inspect()
    assert statuses.get("urn:nuclear:launch:DualKeySync") in ["Active", "Completed", "Archived"]


def test_phase4_xor_abort_path(abort_scenario: HybridEngine) -> None:
    """WCP-4: XOR selects Abort when abort signal present.

    Arrange:
        - abort_scenario fixture (abort signal = true)
    Act:
        - Run to completion
    Assert:
        - AbortSequence is activated (NOT ArmWarhead)
        - End state reached
    """
    # Run the abort scenario to completion
    results = abort_scenario.run_to_completion(max_ticks=20)

    # Final statuses
    statuses = abort_scenario.inspect()

    # Abort path should be taken
    assert statuses.get("urn:nuclear:launch:AbortSequence") in ["Active", "Completed", "Archived"]

    # Launch path should NOT be taken (ArmWarhead should not activate)
    # Note: Task might not have status if never activated
    arm_status = statuses.get("urn:nuclear:launch:ArmWarhead")
    assert arm_status != "Active" and arm_status != "Completed"


def test_phase4_xor_arm_path(launch_scenario: HybridEngine) -> None:
    """WCP-4: XOR selects ArmWarhead when no abort signal.

    Arrange:
        - launch_scenario fixture (abort signal = false)
    Act:
        - Run to completion
    Assert:
        - ArmWarhead is activated (NOT AbortSequence)
        - LaunchMissile follows
    """
    # Run the launch scenario to completion
    results = launch_scenario.run_to_completion(max_ticks=20)

    # Final statuses
    statuses = launch_scenario.inspect()

    # Launch path should be taken
    assert statuses.get("urn:nuclear:launch:ArmWarhead") in ["Active", "Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:LaunchMissile") in ["Active", "Completed", "Archived"]

    # Abort path should NOT be taken
    abort_status = statuses.get("urn:nuclear:launch:AbortSequence")
    assert abort_status != "Active" and abort_status != "Completed"


def test_phase5_simple_merge(abort_scenario: HybridEngine) -> None:
    """WCP-5: Multiple end paths merge to single End state.

    Arrange:
        - Scenario that reaches End via any path
    Act:
        - Run to completion
    Assert:
        - End task becomes Active regardless of which path taken
    """
    results = abort_scenario.run_to_completion(max_ticks=20)

    statuses = abort_scenario.inspect()

    # End should be active/completed via abort path
    assert statuses.get("urn:nuclear:launch:End") in ["Active", "Completed", "Archived"]


# =============================================================================
# END-TO-END SCENARIO TESTS
# =============================================================================


def test_full_abort_scenario(abort_scenario: HybridEngine) -> None:
    """Complete workflow: Start → DualKey → Auth → Sync → ABORT → End.

    Arrange:
        - Abort scenario fixture
    Act:
        - Run to completion
    Assert:
        - Workflow reaches End via abort path
        - Fixed point reached
        - LaunchMissile never activated
    """
    results = abort_scenario.run_to_completion(max_ticks=20)

    # Should converge
    assert results[-1].converged is True

    statuses = abort_scenario.inspect()

    # Verify abort path taken
    assert statuses.get("urn:nuclear:launch:AbortSequence") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:End") in ["Active", "Completed"]

    # Verify launch path NOT taken
    launch_status = statuses.get("urn:nuclear:launch:LaunchMissile")
    assert launch_status is None or launch_status not in ["Active", "Completed"]


def test_full_launch_scenario(launch_scenario: HybridEngine) -> None:
    """Complete workflow: Start → DualKey → Auth → Sync → Arm → Launch → End.

    Arrange:
        - Launch scenario fixture
    Act:
        - Run to completion
    Assert:
        - Workflow reaches End via launch path
        - Fixed point reached
        - AbortSequence never activated
    """
    results = launch_scenario.run_to_completion(max_ticks=20)

    # Should converge
    assert results[-1].converged is True

    statuses = launch_scenario.inspect()

    # Verify launch path taken
    assert statuses.get("urn:nuclear:launch:ArmWarhead") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:LaunchMissile") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:End") in ["Active", "Completed"]

    # Verify abort path NOT taken
    abort_status = statuses.get("urn:nuclear:launch:AbortSequence")
    assert abort_status is None or abort_status not in ["Active", "Completed"]


# =============================================================================
# INVARIANT TESTS
# =============================================================================


def test_no_dual_launch(launch_scenario: HybridEngine) -> None:
    """Safety invariant: Cannot have both Abort AND Launch active.

    Arrange:
        - Any scenario
    Act:
        - Run to completion
    Assert:
        - At most one of {AbortSequence, LaunchMissile} is Completed
    """
    results = launch_scenario.run_to_completion(max_ticks=20)

    statuses = launch_scenario.inspect()

    abort_completed = statuses.get("urn:nuclear:launch:AbortSequence") in ["Completed", "Archived"]
    launch_completed = statuses.get("urn:nuclear:launch:LaunchMissile") in ["Completed", "Archived"]

    # XOR: NOT both
    assert not (abort_completed and launch_completed)


def test_dual_key_required(launch_scenario: HybridEngine) -> None:
    """Safety invariant: Cannot arm without BOTH authorizations.

    Arrange:
        - Launch scenario
    Act:
        - Run to completion
    Assert:
        - If ArmWarhead activated, both CommanderAuth and DeputyAuth were Completed
    """
    results = launch_scenario.run_to_completion(max_ticks=20)

    statuses = launch_scenario.inspect()

    arm_status = statuses.get("urn:nuclear:launch:ArmWarhead")

    if arm_status in ["Active", "Completed", "Archived"]:
        # Both auth tasks must have completed (or archived)
        commander_status = statuses.get("urn:nuclear:launch:CommanderAuth")
        deputy_status = statuses.get("urn:nuclear:launch:DeputyAuth")

        # Both must have been completed at some point
        assert commander_status in ["Completed", "Archived"]
        assert deputy_status in ["Completed", "Archived"]


def test_no_infinite_loop(abort_scenario: HybridEngine) -> None:
    """Convergence: All scenarios reach fixed point < 64 ticks.

    Arrange:
        - Abort scenario
    Act:
        - Run with max_ticks=64
    Assert:
        - Converges before limit
        - Last result has converged=True
    """
    results = abort_scenario.run_to_completion(max_ticks=64)

    # Should not hit 64 tick limit
    assert len(results) < 64

    # Last tick should be fixed point
    assert results[-1].converged is True


def test_single_end_state(launch_scenario: HybridEngine) -> None:
    """Exactly one end state (Abort, Launch, or TimeoutAbort) is reached.

    Arrange:
        - Launch scenario
    Act:
        - Run to completion
    Assert:
        - Exactly one terminal task is Completed
    """
    results = launch_scenario.run_to_completion(max_ticks=20)

    statuses = launch_scenario.inspect()

    terminal_states = [
        statuses.get("urn:nuclear:launch:AbortSequence"),
        statuses.get("urn:nuclear:launch:LaunchMissile"),
    ]

    # Count how many are completed
    completed_count = sum(1 for s in terminal_states if s in ["Completed", "Archived"])

    # Exactly one should be completed
    assert completed_count == 1


# =============================================================================
# STATE VERIFICATION HELPERS
# =============================================================================


def assert_task_status(engine: HybridEngine, task_uri: str, expected_status: str) -> None:
    """Assert a task has the expected status in the graph.

    Parameters
    ----------
    engine : HybridEngine
        Engine instance.
    task_uri : str
        Full URI of task to check.
    expected_status : str
        Expected status value.

    Raises
    ------
    AssertionError
        If status does not match expected.
    """
    statuses = engine.inspect()
    actual_status = statuses.get(task_uri)
    assert actual_status == expected_status, f"Expected {task_uri} status={expected_status}, got {actual_status}"


def assert_task_active(engine: HybridEngine, task_uri: str) -> None:
    """Assert a task is currently active.

    Parameters
    ----------
    engine : HybridEngine
        Engine instance.
    task_uri : str
        Full URI of task to check.

    Raises
    ------
    AssertionError
        If task is not Active.
    """
    assert_task_status(engine, task_uri, "Active")


def assert_task_completed(engine: HybridEngine, task_uri: str) -> None:
    """Assert a task has completed.

    Parameters
    ----------
    engine : HybridEngine
        Engine instance.
    task_uri : str
        Full URI of task to check.

    Raises
    ------
    AssertionError
        If task is not Completed or Archived.
    """
    statuses = engine.inspect()
    actual_status = statuses.get(task_uri)
    assert actual_status in ["Completed", "Archived"], (
        f"Expected {task_uri} to be Completed/Archived, got {actual_status}"
    )


def get_active_tasks(engine: HybridEngine) -> list[str]:
    """Return list of currently active task URIs.

    Parameters
    ----------
    engine : HybridEngine
        Engine instance.

    Returns
    -------
    list[str]
        List of task URIs with status "Active".
    """
    statuses = engine.inspect()
    return [uri for uri, status in statuses.items() if status == "Active"]


# =============================================================================
# TICK-BY-TICK VERIFICATION
# =============================================================================


def test_tick_sequence_abort() -> None:
    """Verify workflow trace for abort scenario.

    This test validates that the workflow follows the correct path through
    WCP patterns when abort signal is present.

    Note: EYE computes full deductive closure in each tick, so we verify
    the workflow DID flow through each point (status was assigned) rather
    than catching exact intermediate "Active" states.

    Arrange:
        - Abort scenario with predicate=true
    Act:
        - Apply physics and run to completion
    Assert:
        - All tasks on abort path were executed (have status)
        - Launch path was NOT executed (no status)
        - Workflow terminates at End
    """
    engine = HybridEngine()

    # Initial topology: Start already completed
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

nuc:CommanderAuth a yawl:Task .
nuc:DeputyAuth a yawl:Task .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo true .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)

    # Tick 0: Check initial state before physics
    statuses_0 = engine.inspect()
    # Start is already completed in topology
    assert statuses_0.get("urn:nuclear:launch:Start") == "Completed"

    # Tick 1: Apply physics - EYE computes full deductive closure
    # All rules fire until fixpoint, so multiple state transitions occur
    result_1 = engine.apply_physics()
    statuses_1 = engine.inspect()

    # DualKeyCheck was activated (may have progressed to Completed/Archived)
    # EYE computes full closure, so we check it WAS activated, not that it IS Active
    assert statuses_1.get("urn:nuclear:launch:DualKeyCheck") in ["Active", "Completed", "Archived"]

    # Continue to convergence and verify abort path
    remaining_results = engine.run_to_completion(max_ticks=15)

    final_statuses = engine.inspect()

    # Verify the complete workflow trace:
    # Start → DualKeyCheck → (CommanderAuth + DeputyAuth) → DualKeySync → AbortSequence → End
    assert final_statuses.get("urn:nuclear:launch:Start") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:DualKeyCheck") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:CommanderAuth") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:DeputyAuth") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:DualKeySync") in ["Completed", "Archived"]

    # Verify abort path was taken (XOR with predicate=true)
    assert final_statuses.get("urn:nuclear:launch:AbortSequence") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:End") in ["Active", "Completed"]

    # Verify launch path NOT taken (exclusive choice)
    arm_status = final_statuses.get("urn:nuclear:launch:ArmWarhead")
    assert arm_status is None or arm_status not in ["Active", "Completed", "Archived"]


def test_tick_sequence_launch() -> None:
    """Verify workflow trace for launch scenario.

    This test validates that the workflow follows the correct path through
    WCP patterns when abort signal is NOT present (default path taken).

    Note: EYE computes full deductive closure in each tick, so we verify
    the workflow DID flow through each point (status was assigned) rather
    than catching exact intermediate "Active" states.

    Arrange:
        - Launch scenario with predicate=false (no abort)
    Act:
        - Run to completion
    Assert:
        - All tasks on launch path were executed (have status)
        - Abort path was NOT executed (no status)
        - Workflow terminates at End
    """
    engine = HybridEngine()

    # Launch topology (no abort signal)
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

nuc:CommanderAuth a yawl:Task .
nuc:DeputyAuth a yawl:Task .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .  # NO ABORT

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .

nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)

    # Run to completion
    results = engine.run_to_completion(max_ticks=20)

    final_statuses = engine.inspect()

    # Verify launch path was taken
    assert final_statuses.get("urn:nuclear:launch:ArmWarhead") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:LaunchMissile") in ["Completed", "Archived"]
    assert final_statuses.get("urn:nuclear:launch:End") in ["Active", "Completed"]

    # Verify abort path NOT taken
    abort_status = final_statuses.get("urn:nuclear:launch:AbortSequence")
    assert abort_status is None or abort_status not in ["Active", "Completed"]


# =============================================================================
# EDGE CASE TESTS: PARTIAL AUTHORIZATION FAILURES
# =============================================================================


def test_only_commander_authorizes_workflow_blocks() -> None:
    """Test that workflow blocks when ONLY Commander authorizes (Deputy missing).

    The AND-join at DualKeySync requires BOTH CommanderAuth AND DeputyAuth
    to complete. If only one completes, the workflow should NOT progress
    past the synchronization point.

    This tests WCP-3 (Synchronization) blocking behavior.
    """
    engine = HybridEngine()

    # Topology where only Commander completes, Deputy stays waiting
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

# Start already completed
nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

# DualKeyCheck completed (AND-split happened)
nuc:DualKeyCheck a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

# Commander has authenticated and completed
nuc:CommanderAuth a yawl:Task ;
    kgc:status "Completed" ;
    kgc:requiresManualCompletion true .

# Deputy is BLOCKED - not yet authenticated (requires manual completion)
# The requiresManualCompletion flag prevents auto-completion by physics rules
nuc:DeputyAuth a yawl:Task ;
    kgc:requiresManualCompletion true .
# Note: No kgc:status means this task is waiting for human input

# AND-join requires BOTH
nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)

    # Apply physics
    results = engine.run_to_completion(max_ticks=10)

    statuses = engine.inspect()

    # DualKeySync should NOT be activated (AND-join not satisfied)
    sync_status = statuses.get("urn:nuclear:launch:DualKeySync")
    assert sync_status is None, f"DualKeySync should NOT activate with only Commander auth, got {sync_status}"

    # Neither abort nor arm should be activated
    abort_status = statuses.get("urn:nuclear:launch:AbortSequence")
    arm_status = statuses.get("urn:nuclear:launch:ArmWarhead")
    assert abort_status is None, f"AbortSequence should not activate, got {abort_status}"
    assert arm_status is None, f"ArmWarhead should not activate, got {arm_status}"

    # End should NOT be reached
    end_status = statuses.get("urn:nuclear:launch:End")
    assert end_status is None, f"End should not be reached, got {end_status}"


def test_only_deputy_authorizes_workflow_blocks() -> None:
    """Test that workflow blocks when ONLY Deputy authorizes (Commander missing).

    Mirror test of test_only_commander_authorizes_workflow_blocks.
    Verifies AND-join blocks from the other direction.
    """
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

# Commander is BLOCKED (requires manual completion, no status yet)
nuc:CommanderAuth a yawl:Task ;
    kgc:requiresManualCompletion true .

# Deputy has authenticated and completed
nuc:DeputyAuth a yawl:Task ;
    kgc:status "Completed" ;
    kgc:requiresManualCompletion true .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # DualKeySync should NOT be activated
    sync_status = statuses.get("urn:nuclear:launch:DualKeySync")
    assert sync_status is None, f"DualKeySync should NOT activate with only Deputy auth, got {sync_status}"

    # End should NOT be reached
    end_status = statuses.get("urn:nuclear:launch:End")
    assert end_status is None, f"End should not be reached, got {end_status}"


def test_neither_key_authorizes_workflow_blocks() -> None:
    """Test that workflow blocks when NEITHER Commander nor Deputy authorizes.

    Both auth tasks remain in waiting state, AND-join never satisfied.
    """
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

# Both are BLOCKED - no authentication (require manual completion)
nuc:CommanderAuth a yawl:Task ;
    kgc:requiresManualCompletion true .
nuc:DeputyAuth a yawl:Task ;
    kgc:requiresManualCompletion true .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # DualKeySync should NOT be activated
    sync_status = statuses.get("urn:nuclear:launch:DualKeySync")
    assert sync_status is None, f"DualKeySync should NOT activate with no auth, got {sync_status}"

    # Both auth tasks should be Active (activated by AND-SPLIT from DualKeyCheck)
    # but NOT Completed because they require manual completion
    cmd_status = statuses.get("urn:nuclear:launch:CommanderAuth")
    dep_status = statuses.get("urn:nuclear:launch:DeputyAuth")
    assert cmd_status == "Active", f"CommanderAuth should be Active (waiting), got {cmd_status}"
    assert dep_status == "Active", f"DeputyAuth should be Active (waiting), got {dep_status}"


# =============================================================================
# EDGE CASE TESTS: XOR EXCLUSIVITY
# =============================================================================


def test_xor_both_predicates_true_takes_first_match() -> None:
    """Test XOR behavior when multiple predicates could match.

    In YAWL, XOR should take exactly ONE path. If multiple predicates
    evaluate to true, the behavior depends on rule firing order.

    This tests that we don't activate BOTH paths.
    """
    engine = HybridEngine()

    # Intentionally malformed: both predicates true
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Decision a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_a, nuc:flow_to_b .

# Path A with predicate=true
nuc:flow_to_a yawl:nextElementRef nuc:PathA ;
    yawl:hasPredicate nuc:pred_a .
nuc:pred_a kgc:evaluatesTo true .

# Path B as default (should NOT fire if predicate path fires)
nuc:flow_to_b yawl:nextElementRef nuc:PathB ;
    yawl:isDefaultFlow true .

nuc:PathA a yawl:Task .
nuc:PathB a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # PathA should be taken (predicate=true)
    path_a_status = statuses.get("urn:nuclear:launch:PathA")
    assert path_a_status in ["Active", "Completed", "Archived"], f"PathA should be activated, got {path_a_status}"

    # PathB should NOT be taken (default only fires when predicate=false)
    path_b_status = statuses.get("urn:nuclear:launch:PathB")
    assert path_b_status is None, f"PathB should NOT activate when predicate path taken, got {path_b_status}"


def test_xor_no_predicate_takes_default() -> None:
    """Test XOR behavior when no predicate matches - default path taken."""
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Decision a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_a, nuc:flow_to_b .

# Path A with predicate=FALSE
nuc:flow_to_a yawl:nextElementRef nuc:PathA ;
    yawl:hasPredicate nuc:pred_a .
nuc:pred_a kgc:evaluatesTo false .

# Path B as default - should be taken
nuc:flow_to_b yawl:nextElementRef nuc:PathB ;
    yawl:isDefaultFlow true .

nuc:PathA a yawl:Task .
nuc:PathB a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # PathA should NOT be taken (predicate=false)
    path_a_status = statuses.get("urn:nuclear:launch:PathA")
    assert path_a_status is None, f"PathA should NOT activate when predicate=false, got {path_a_status}"

    # PathB should be taken (default path)
    path_b_status = statuses.get("urn:nuclear:launch:PathB")
    assert path_b_status in ["Active", "Completed", "Archived"], f"PathB (default) should activate, got {path_b_status}"


# =============================================================================
# EDGE CASE TESTS: AND-SPLIT PARALLEL ACTIVATION
# =============================================================================


def test_and_split_activates_all_branches() -> None:
    """Test that AND-split activates ALL outgoing branches simultaneously."""
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:ParallelGateway a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_a, nuc:flow_to_b, nuc:flow_to_c .

nuc:flow_to_a yawl:nextElementRef nuc:BranchA .
nuc:flow_to_b yawl:nextElementRef nuc:BranchB .
nuc:flow_to_c yawl:nextElementRef nuc:BranchC .

nuc:BranchA a yawl:Task .
nuc:BranchB a yawl:Task .
nuc:BranchC a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # ALL three branches should be activated
    branch_a = statuses.get("urn:nuclear:launch:BranchA")
    branch_b = statuses.get("urn:nuclear:launch:BranchB")
    branch_c = statuses.get("urn:nuclear:launch:BranchC")

    assert branch_a in ["Active", "Completed", "Archived"], f"BranchA should activate, got {branch_a}"
    assert branch_b in ["Active", "Completed", "Archived"], f"BranchB should activate, got {branch_b}"
    assert branch_c in ["Active", "Completed", "Archived"], f"BranchC should activate, got {branch_c}"


def test_and_join_waits_for_at_least_two_branches() -> None:
    """Test that AND-join requires at least 2 completed branches.

    The current N3 rule checks for at least 2 DISTINCT completed predecessors.
    This is correct for the nuclear launch scenario (2 auth tasks).
    With only 1 branch completed, the join should NOT activate.
    """
    engine = HybridEngine()

    # Only 1 of 2 branches complete - join should NOT fire
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:BranchA a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_a_to_join .

# BranchB is NOT completed - blocks the join
nuc:BranchB a yawl:Task ;
    yawl:flowsInto nuc:flow_b_to_join .

nuc:flow_a_to_join yawl:nextElementRef nuc:JoinPoint .
nuc:flow_b_to_join yawl:nextElementRef nuc:JoinPoint .

nuc:JoinPoint a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # JoinPoint should NOT activate (only 1 of 2 branches complete)
    join_status = statuses.get("urn:nuclear:launch:JoinPoint")
    assert join_status is None, f"JoinPoint should NOT activate with only 1/2 branches, got {join_status}"


def test_and_join_fires_when_all_branches_complete() -> None:
    """Test that AND-join DOES fire when all 2 branches complete."""
    engine = HybridEngine()

    # Both branches complete - join should fire
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:BranchA a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_a_to_join .

nuc:BranchB a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_b_to_join .

nuc:flow_a_to_join yawl:nextElementRef nuc:JoinPoint .
nuc:flow_b_to_join yawl:nextElementRef nuc:JoinPoint .

nuc:JoinPoint a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # JoinPoint SHOULD activate (both branches complete)
    join_status = statuses.get("urn:nuclear:launch:JoinPoint")
    assert join_status in ["Active", "Completed", "Archived"], (
        f"JoinPoint should activate with 2/2 branches, got {join_status}"
    )


# =============================================================================
# EDGE CASE TESTS: SIMPLE MERGE (WCP-5)
# =============================================================================


def test_simple_merge_any_path_reaches_end() -> None:
    """Test that any ONE completed path triggers the merge point (WCP-5).

    Unlike AND-join, simple merge activates when ANY input arrives.
    """
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

# Only PathA completes
nuc:PathA a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_a_to_merge .

# PathB not completed
nuc:PathB a yawl:Task ;
    yawl:flowsInto nuc:flow_b_to_merge .

nuc:flow_a_to_merge yawl:nextElementRef nuc:MergePoint .
nuc:flow_b_to_merge yawl:nextElementRef nuc:MergePoint .

# Simple sequence (no join type = simple merge)
nuc:MergePoint a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # MergePoint should activate (PathA completed)
    merge_status = statuses.get("urn:nuclear:launch:MergePoint")
    assert merge_status in ["Active", "Completed", "Archived"], (
        f"MergePoint should activate via PathA, got {merge_status}"
    )


# =============================================================================
# EDGE CASE TESTS: WORKFLOW NOT STARTED
# =============================================================================


def test_workflow_not_started_nothing_activates() -> None:
    """Test that workflow with no initial status stays dormant."""
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

# Start task has NO status - workflow not initiated
nuc:Start a yawl:Task ;
    yawl:flowsInto nuc:flow_to_next .

nuc:flow_to_next yawl:nextElementRef nuc:Next .

nuc:Next a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # Nothing should have any status
    assert len(statuses) == 0, f"No tasks should have status when workflow not started, got {statuses}"


def test_workflow_active_start_progresses() -> None:
    """Test that workflow with Active start task progresses correctly."""
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

# Start is Active - will auto-complete and flow
nuc:Start a yawl:Task ;
    kgc:status "Active" ;
    yawl:flowsInto nuc:flow_to_next .

nuc:flow_to_next yawl:nextElementRef nuc:Next .

nuc:Next a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=10)
    statuses = engine.inspect()

    # Start should complete and flow to Next
    start_status = statuses.get("urn:nuclear:launch:Start")
    next_status = statuses.get("urn:nuclear:launch:Next")

    assert start_status in ["Completed", "Archived"], f"Start should complete, got {start_status}"
    assert next_status in ["Active", "Completed", "Archived"], f"Next should activate, got {next_status}"


# =============================================================================
# EDGE CASE TESTS: COMPLEX WORKFLOW PATTERNS
# =============================================================================


def test_sequential_chain_all_complete() -> None:
    """Test a sequential chain of tasks all complete in order."""
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Step1 a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_1_2 .
nuc:flow_1_2 yawl:nextElementRef nuc:Step2 .

nuc:Step2 a yawl:Task ;
    yawl:flowsInto nuc:flow_2_3 .
nuc:flow_2_3 yawl:nextElementRef nuc:Step3 .

nuc:Step3 a yawl:Task ;
    yawl:flowsInto nuc:flow_3_4 .
nuc:flow_3_4 yawl:nextElementRef nuc:Step4 .

nuc:Step4 a yawl:Task ;
    yawl:flowsInto nuc:flow_4_5 .
nuc:flow_4_5 yawl:nextElementRef nuc:Step5 .

nuc:Step5 a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # All 5 steps should have completed/archived
    for i in range(1, 6):
        status = statuses.get(f"urn:nuclear:launch:Step{i}")
        assert status in ["Completed", "Archived"], f"Step{i} should complete, got {status}"


def test_diamond_pattern_and_split_and_join() -> None:
    """Test diamond workflow pattern: split then rejoin.

    Pattern: Start → AND-Split → (A, B) → AND-Join → End
    """
    engine = HybridEngine()

    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_a, nuc:flow_to_b .

nuc:flow_to_a yawl:nextElementRef nuc:BranchA .
nuc:flow_to_b yawl:nextElementRef nuc:BranchB .

nuc:BranchA a yawl:Task ;
    yawl:flowsInto nuc:flow_a_to_end .

nuc:BranchB a yawl:Task ;
    yawl:flowsInto nuc:flow_b_to_end .

nuc:flow_a_to_end yawl:nextElementRef nuc:End .
nuc:flow_b_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # All tasks should complete
    assert statuses.get("urn:nuclear:launch:Start") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:BranchA") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:BranchB") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:End") in ["Active", "Completed", "Archived"]


def test_abort_at_any_stage_before_launch() -> None:
    """Test that abort signal prevents launch even when other conditions met."""
    engine = HybridEngine()

    # Full workflow with abort signal
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

nuc:CommanderAuth a yawl:Task .
nuc:DeputyAuth a yawl:Task .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

# ABORT SIGNAL IS SET
nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo true .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # Abort path should be taken
    assert statuses.get("urn:nuclear:launch:AbortSequence") in ["Completed", "Archived"]
    assert statuses.get("urn:nuclear:launch:End") in ["Active", "Completed"]

    # Launch path should NOT be taken
    arm_status = statuses.get("urn:nuclear:launch:ArmWarhead")
    launch_status = statuses.get("urn:nuclear:launch:LaunchMissile")
    assert arm_status is None, f"ArmWarhead should not activate on abort, got {arm_status}"
    assert launch_status is None, f"LaunchMissile should not activate on abort, got {launch_status}"


# =============================================================================
# INVARIANT TESTS: SAFETY PROPERTIES
# =============================================================================


def test_safety_no_launch_without_dual_auth() -> None:
    """Safety property: LaunchMissile requires BOTH Commander AND Deputy auth."""
    engine = HybridEngine()

    # Try to set up a scenario where launch happens without proper auth
    # This should be impossible given proper WCP implementation
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

# ONLY Commander completes - Deputy blocked (requires manual completion)
nuc:CommanderAuth a yawl:Task ;
    kgc:status "Completed" ;
    kgc:requiresManualCompletion true .
nuc:DeputyAuth a yawl:Task ;
    kgc:requiresManualCompletion true .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # LaunchMissile should NEVER be activated without dual auth
    launch_status = statuses.get("urn:nuclear:launch:LaunchMissile")
    assert launch_status is None, (
        f"SAFETY VIOLATION: LaunchMissile activated without dual auth! Status: {launch_status}"
    )

    # ArmWarhead should also not activate
    arm_status = statuses.get("urn:nuclear:launch:ArmWarhead")
    assert arm_status is None, f"SAFETY VIOLATION: ArmWarhead activated without dual auth! Status: {arm_status}"


def test_safety_abort_always_overrides() -> None:
    """Safety property: Abort signal ALWAYS prevents launch, regardless of other conditions."""
    engine = HybridEngine()

    # Both auths complete, but abort signal is set
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

# BOTH auths complete
nuc:CommanderAuth a yawl:Task ;
    kgc:status "Completed" .
nuc:DeputyAuth a yawl:Task ;
    kgc:status "Completed" .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

# ABORT SIGNAL SET
nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo true .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # Abort path should be taken even though both auths completed
    abort_status = statuses.get("urn:nuclear:launch:AbortSequence")
    assert abort_status in ["Completed", "Archived"], f"Abort should complete when signal set, got {abort_status}"

    # Launch should NOT happen
    launch_status = statuses.get("urn:nuclear:launch:LaunchMissile")
    assert launch_status is None, f"SAFETY: Launch should not happen when abort set, got {launch_status}"


def test_safety_exactly_one_terminal_state() -> None:
    """Safety property: Workflow reaches exactly ONE terminal state."""
    engine = HybridEngine()

    # Full workflow with launch path
    topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix nuc: <urn:nuclear:launch:> .

nuc:Start a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto nuc:flow_start_to_dualkey .

nuc:flow_start_to_dualkey yawl:nextElementRef nuc:DualKeyCheck .

nuc:DualKeyCheck a yawl:Task ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto nuc:flow_to_commander, nuc:flow_to_deputy .

nuc:flow_to_commander yawl:nextElementRef nuc:CommanderAuth .
nuc:flow_to_deputy yawl:nextElementRef nuc:DeputyAuth .

nuc:CommanderAuth a yawl:Task .
nuc:DeputyAuth a yawl:Task .

nuc:DualKeySync a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto nuc:flow_to_abort, nuc:flow_to_arm .

nuc:CommanderAuth yawl:flowsInto nuc:flow_commander_to_sync .
nuc:DeputyAuth yawl:flowsInto nuc:flow_deputy_to_sync .
nuc:flow_commander_to_sync yawl:nextElementRef nuc:DualKeySync .
nuc:flow_deputy_to_sync yawl:nextElementRef nuc:DualKeySync .

# NO abort signal - launch will proceed
nuc:flow_to_abort yawl:nextElementRef nuc:AbortSequence ;
    yawl:hasPredicate nuc:pred_abort .
nuc:pred_abort kgc:evaluatesTo false .

nuc:flow_to_arm yawl:nextElementRef nuc:ArmWarhead ;
    yawl:isDefaultFlow true .

nuc:AbortSequence a yawl:Task ;
    yawl:flowsInto nuc:flow_abort_to_end .
nuc:ArmWarhead a yawl:Task ;
    yawl:flowsInto nuc:flow_arm_to_launch .

nuc:flow_abort_to_end yawl:nextElementRef nuc:End .
nuc:flow_arm_to_launch yawl:nextElementRef nuc:LaunchMissile .

nuc:LaunchMissile a yawl:Task ;
    yawl:flowsInto nuc:flow_launch_to_end .
nuc:flow_launch_to_end yawl:nextElementRef nuc:End .

nuc:End a yawl:Task .
"""

    engine.load_data(topology)
    results = engine.run_to_completion(max_ticks=20)
    statuses = engine.inspect()

    # Count terminal states reached
    terminal_tasks = ["urn:nuclear:launch:AbortSequence", "urn:nuclear:launch:LaunchMissile"]
    activated_terminals = [t for t in terminal_tasks if statuses.get(t) in ["Active", "Completed", "Archived"]]

    assert len(activated_terminals) == 1, f"SAFETY: Exactly one terminal should activate, got {activated_terminals}"

    # End should be reached
    assert statuses.get("urn:nuclear:launch:End") in ["Active", "Completed"], "Workflow should reach End"
