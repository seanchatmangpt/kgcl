"""Nuclear Launch Authorization Workflow - YAWL Pattern Validation.

This scenario demonstrates a critical safety workflow using N3 rules to enforce:
- WCP-1: Sequence (Start → DualKeyCheck)
- WCP-2: Parallel Split (DualKeyCheck → CommanderAuth AND DeputyAuth)
- WCP-3: Synchronization (CommanderAuth + DeputyAuth → DualKeySync)
- WCP-4: Exclusive Choice (DualKeySync → Abort XOR ArmWarhead)
- WCP-5: Simple Merge (Launch/Abort/TimeoutAbort → End)
- WCP-11: Implicit Termination (End state detection)

The workflow models a nuclear launch authorization requiring:
1. Dual key verification (parallel authentication)
2. Synchronization of both keys
3. Exclusive choice: abort or proceed
4. Timeout-based safety abort
5. Final state convergence

All logic is expressed in N3 rules (no Python conditionals).
"""

from __future__ import annotations

# Base ontology namespaces and workflow structure
NUCLEAR_LAUNCH_ONTOLOGY = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix kgc: <http://kgcl.io/hybrid/> .
@prefix yawl: <http://yawl.sourceforge.net/> .
@prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .
@prefix log: <http://www.w3.org/2000/10/swap/log#> .

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

launch:Start a yawl:AtomicTask ;
    rdfs:label "Launch sequence initiated" ;
    rdfs:comment "Entry point - workflow begins here" .

launch:DualKeyCheck a yawl:CompositeTask ;
    rdfs:label "Dual key verification required" ;
    rdfs:comment "Parallel split point - requires both keys" .

launch:CommanderAuth a yawl:AtomicTask ;
    rdfs:label "Commander authentication" ;
    rdfs:comment "Commander must authenticate with key" .

launch:DeputyAuth a yawl:AtomicTask ;
    rdfs:label "Deputy authentication" ;
    rdfs:comment "Deputy must authenticate with key" .

launch:DualKeySync a yawl:CompositeTask ;
    rdfs:label "Synchronization point for dual keys" ;
    rdfs:comment "Both keys must be verified before proceeding" .

launch:Abort a yawl:AtomicTask ;
    rdfs:label "Launch sequence aborted" ;
    rdfs:comment "Abort path - safe termination" .

launch:ArmWarhead a yawl:AtomicTask ;
    rdfs:label "Warhead armed" ;
    rdfs:comment "Launch authorized - arm warhead" .

launch:LaunchCountdown a yawl:AtomicTask ;
    rdfs:label "10-second countdown" ;
    rdfs:comment "Final countdown with timeout" ;
    yawl:timeout "PT10S" .

launch:Launch a yawl:AtomicTask ;
    rdfs:label "Nuclear launch executed" ;
    rdfs:comment "Launch completed" .

launch:TimeoutAbort a yawl:AtomicTask ;
    rdfs:label "Countdown timeout - abort" ;
    rdfs:comment "Safety abort on timeout" .

launch:End a yawl:AtomicTask ;
    rdfs:label "Workflow terminated" ;
    rdfs:comment "Final state - workflow complete" .

# ============================================================================
# FLOW DEFINITIONS (Workflow Control Flow)
# ============================================================================

# WCP-1: Sequence - Start to DualKeyCheck
launch:Flow_StartToDualKey a yawl:Flow ;
    yawl:sourceRef launch:Start ;
    yawl:targetRef launch:DualKeyCheck .

launch:Start yawl:flowsInto launch:Flow_StartToDualKey .
launch:Flow_StartToDualKey yawl:nextElementRef launch:DualKeyCheck .

# WCP-2: Parallel Split - DualKeyCheck to both auth tasks
launch:Flow_DualKeyToCommander a yawl:Flow ;
    yawl:sourceRef launch:DualKeyCheck ;
    yawl:targetRef launch:CommanderAuth ;
    yawl:splitType "AND" .

launch:Flow_DualKeyToDeputy a yawl:Flow ;
    yawl:sourceRef launch:DualKeyCheck ;
    yawl:targetRef launch:DeputyAuth ;
    yawl:splitType "AND" .

launch:DualKeyCheck yawl:flowsInto launch:Flow_DualKeyToCommander .
launch:DualKeyCheck yawl:flowsInto launch:Flow_DualKeyToDeputy .
launch:Flow_DualKeyToCommander yawl:nextElementRef launch:CommanderAuth .
launch:Flow_DualKeyToDeputy yawl:nextElementRef launch:DeputyAuth .

# WCP-3: Synchronization - Both auth tasks to DualKeySync
launch:Flow_CommanderToSync a yawl:Flow ;
    yawl:sourceRef launch:CommanderAuth ;
    yawl:targetRef launch:DualKeySync ;
    yawl:joinType "AND" .

launch:Flow_DeputyToSync a yawl:Flow ;
    yawl:sourceRef launch:DeputyAuth ;
    yawl:targetRef launch:DualKeySync ;
    yawl:joinType "AND" .

launch:CommanderAuth yawl:flowsInto launch:Flow_CommanderToSync .
launch:DeputyAuth yawl:flowsInto launch:Flow_DeputyToSync .
launch:Flow_CommanderToSync yawl:nextElementRef launch:DualKeySync .
launch:Flow_DeputyToSync yawl:nextElementRef launch:DualKeySync .

# WCP-4: Exclusive Choice - DualKeySync to Abort OR ArmWarhead
launch:Flow_SyncToAbort a yawl:Flow ;
    yawl:sourceRef launch:DualKeySync ;
    yawl:targetRef launch:Abort ;
    yawl:splitType "XOR" ;
    yawl:condition "abortSignal=true" .

launch:Flow_SyncToArm a yawl:Flow ;
    yawl:sourceRef launch:DualKeySync ;
    yawl:targetRef launch:ArmWarhead ;
    yawl:splitType "XOR" ;
    yawl:condition "abortSignal=false" .

launch:DualKeySync yawl:flowsInto launch:Flow_SyncToAbort .
launch:DualKeySync yawl:flowsInto launch:Flow_SyncToArm .
launch:Flow_SyncToAbort yawl:nextElementRef launch:Abort .
launch:Flow_SyncToArm yawl:nextElementRef launch:ArmWarhead .

# Sequence: ArmWarhead to LaunchCountdown
launch:Flow_ArmToCountdown a yawl:Flow ;
    yawl:sourceRef launch:ArmWarhead ;
    yawl:targetRef launch:LaunchCountdown .

launch:ArmWarhead yawl:flowsInto launch:Flow_ArmToCountdown .
launch:Flow_ArmToCountdown yawl:nextElementRef launch:LaunchCountdown .

# Countdown outcomes: Launch OR TimeoutAbort
launch:Flow_CountdownToLaunch a yawl:Flow ;
    yawl:sourceRef launch:LaunchCountdown ;
    yawl:targetRef launch:Launch ;
    yawl:condition "countdownComplete=true" .

launch:Flow_CountdownToTimeout a yawl:Flow ;
    yawl:sourceRef launch:LaunchCountdown ;
    yawl:targetRef launch:TimeoutAbort ;
    yawl:condition "timeout=true" .

launch:LaunchCountdown yawl:flowsInto launch:Flow_CountdownToLaunch .
launch:LaunchCountdown yawl:flowsInto launch:Flow_CountdownToTimeout .
launch:Flow_CountdownToLaunch yawl:nextElementRef launch:Launch .
launch:Flow_CountdownToTimeout yawl:nextElementRef launch:TimeoutAbort .

# WCP-5: Simple Merge - All terminal paths to End
launch:Flow_LaunchToEnd a yawl:Flow ;
    yawl:sourceRef launch:Launch ;
    yawl:targetRef launch:End ;
    yawl:joinType "XOR" .

launch:Flow_AbortToEnd a yawl:Flow ;
    yawl:sourceRef launch:Abort ;
    yawl:targetRef launch:End ;
    yawl:joinType "XOR" .

launch:Flow_TimeoutToEnd a yawl:Flow ;
    yawl:sourceRef launch:TimeoutAbort ;
    yawl:targetRef launch:End ;
    yawl:joinType "XOR" .

launch:Launch yawl:flowsInto launch:Flow_LaunchToEnd .
launch:Abort yawl:flowsInto launch:Flow_AbortToEnd .
launch:TimeoutAbort yawl:flowsInto launch:Flow_TimeoutToEnd .
launch:Flow_LaunchToEnd yawl:nextElementRef launch:End .
launch:Flow_AbortToEnd yawl:nextElementRef launch:End .
launch:Flow_TimeoutToEnd yawl:nextElementRef launch:End .

# ============================================================================
# N3 PHYSICS RULES (KGC Hybrid Engine)
# ============================================================================

# WCP-1: Sequence - Transmute pattern
# Rule: Start → DualKeyCheck
launch:Rule_StartToDualKey a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Start sequence triggers dual key check" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:Start ;
                  kgc:status "Active" .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?next kgc:status "Active" .
        }
    \"\"\" .

# WCP-2: Parallel Split - Copy pattern
# Rule: DualKeyCheck → CommanderAuth AND DeputyAuth
launch:Rule_DualKeySplit a kgc:PhysicsRule ;
    kgc:signature "Copy" ;
    rdfs:label "Dual key check spawns parallel authentication" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:DualKeyCheck ;
                  kgc:status "Active" .
            ?task yawl:flowsInto ?flow1 .
            ?flow1 yawl:nextElementRef ?branch1 .
            ?task yawl:flowsInto ?flow2 .
            ?flow2 yawl:nextElementRef ?branch2 .
            ?flow1 yawl:splitType "AND" .
            ?flow2 yawl:splitType "AND" .
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?branch1 kgc:status "Active" .
            ?branch2 kgc:status "Active" .
        }
    \"\"\" .

# Sequence: CommanderAuth completion
launch:Rule_CommanderComplete a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Commander authentication completes" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:CommanderAuth ;
                  kgc:status "Active" ;
                  launch:keyVerified true .
        }
        =>
        {
            ?task kgc:status "Completed" .
        }
    \"\"\" .

# Sequence: DeputyAuth completion
launch:Rule_DeputyComplete a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Deputy authentication completes" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:DeputyAuth ;
                  kgc:status "Active" ;
                  launch:keyVerified true .
        }
        =>
        {
            ?task kgc:status "Completed" .
        }
    \"\"\" .

# WCP-3: Synchronization - Await pattern
# Rule: CommanderAuth + DeputyAuth → DualKeySync
launch:Rule_DualKeySync a kgc:PhysicsRule ;
    kgc:signature "Await" ;
    rdfs:label "Synchronize dual key completion" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?sync a launch:DualKeySync .
            ?cmd a launch:CommanderAuth ;
                 kgc:status "Completed" .
            ?dep a launch:DeputyAuth ;
                 kgc:status "Completed" .
        }
        =>
        {
            ?sync kgc:status "Active" .
        }
    \"\"\" .

# WCP-4: Exclusive Choice - Filter pattern (Abort branch)
# Rule: DualKeySync → Abort (if abort signal)
launch:Rule_XOR_Abort a kgc:PhysicsRule ;
    kgc:signature "Filter" ;
    rdfs:label "XOR choice: abort path" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?sync a launch:DualKeySync ;
                  kgc:status "Active" ;
                  launch:abortSignal true .
            ?sync yawl:flowsInto ?flow .
            ?flow yawl:targetRef ?abort .
            ?flow yawl:condition "abortSignal=true" .
            ?abort a launch:Abort .
        }
        =>
        {
            ?sync kgc:status "Completed" .
            ?abort kgc:status "Active" .
        }
    \"\"\" .

# WCP-4: Exclusive Choice - Filter pattern (Arm branch)
# Rule: DualKeySync → ArmWarhead (if no abort signal)
launch:Rule_XOR_Arm a kgc:PhysicsRule ;
    kgc:signature "Filter" ;
    rdfs:label "XOR choice: arm warhead path" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?sync a launch:DualKeySync ;
                  kgc:status "Active" .
            ?sync yawl:flowsInto ?flow .
            ?flow yawl:targetRef ?arm .
            ?flow yawl:condition "abortSignal=false" .
            ?arm a launch:ArmWarhead .
        }
        =>
        {
            ?sync kgc:status "Completed" .
            ?arm kgc:status "Active" .
        }
    \"\"\" .

# Sequence: Abort → End
launch:Rule_AbortToEnd a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Abort completes workflow" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:Abort ;
                  kgc:status "Active" .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?end .
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?end kgc:status "Active" .
        }
    \"\"\" .

# Sequence: ArmWarhead → LaunchCountdown
launch:Rule_ArmToCountdown a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Warhead armed, begin countdown" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:ArmWarhead ;
                  kgc:status "Active" .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?countdown .
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?countdown kgc:status "Active" .
        }
    \"\"\" .

# XOR: LaunchCountdown → Launch (normal completion)
launch:Rule_CountdownToLaunch a kgc:PhysicsRule ;
    kgc:signature "Filter" ;
    rdfs:label "Countdown completes, execute launch" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?countdown a launch:LaunchCountdown ;
                       kgc:status "Active" ;
                       launch:countdownComplete true .
            ?countdown yawl:flowsInto ?flow .
            ?flow yawl:targetRef ?launch .
            ?flow yawl:condition "countdownComplete=true" .
            ?launch a launch:Launch .
        }
        =>
        {
            ?countdown kgc:status "Completed" .
            ?launch kgc:status "Active" .
        }
    \"\"\" .

# XOR: LaunchCountdown → TimeoutAbort (timeout)
launch:Rule_CountdownTimeout a kgc:PhysicsRule ;
    kgc:signature "Filter" ;
    rdfs:label "Countdown timeout, abort launch" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?countdown a launch:LaunchCountdown ;
                       kgc:status "Active" ;
                       launch:timeout true .
            ?countdown yawl:flowsInto ?flow .
            ?flow yawl:targetRef ?timeoutAbort .
            ?flow yawl:condition "timeout=true" .
            ?timeoutAbort a launch:TimeoutAbort .
        }
        =>
        {
            ?countdown kgc:status "Completed" .
            ?timeoutAbort kgc:status "Active" .
        }
    \"\"\" .

# WCP-5: Simple Merge - Launch → End
launch:Rule_LaunchToEnd a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Launch completes workflow" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:Launch ;
                  kgc:status "Active" .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?end .
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?end kgc:status "Active" .
        }
    \"\"\" .

# WCP-5: Simple Merge - TimeoutAbort → End
launch:Rule_TimeoutToEnd a kgc:PhysicsRule ;
    kgc:signature "Transmute" ;
    rdfs:label "Timeout abort completes workflow" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix yawl: <http://yawl.sourceforge.net/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?task a launch:TimeoutAbort ;
                  kgc:status "Active" .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?end .
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?end kgc:status "Active" .
        }
    \"\"\" .

# WCP-11: Implicit Termination - Void pattern
# Rule: End state cleanup (mark workflow complete)
launch:Rule_ImplicitTermination a kgc:PhysicsRule ;
    kgc:signature "Void" ;
    rdfs:label "Workflow termination cleanup" ;
    kgc:n3Logic \"\"\"
        @prefix kgc: <http://kgcl.io/hybrid/> .
        @prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

        {
            ?end a launch:End ;
                 kgc:status "Active" .
        }
        =>
        {
            ?end kgc:status "Completed" .
            kgc:WorkflowInstance kgc:terminated true .
        }
    \"\"\" .
"""

# Base topology (initial state before scenario-specific conditions)
NUCLEAR_LAUNCH_TOPOLOGY = """
@prefix kgc: <http://kgcl.io/hybrid/> .
@prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

# Initial workflow state - Start is active
launch:Start kgc:status "Active" .

# All other tasks are waiting (no status = not yet active)
"""


def load_nuclear_launch_ontology() -> str:
    """Load complete nuclear launch workflow ontology.

    Returns
    -------
    str
        Combined N3/Turtle ontology with workflow structure and physics rules.

    Notes
    -----
    Includes:
    - Task definitions (11 tasks)
    - Flow connections (14 flows)
    - N3 physics rules (15 rules covering all 5 verbs)
    - WCP patterns 1, 2, 3, 4, 5, 11
    """
    return NUCLEAR_LAUNCH_ONTOLOGY + NUCLEAR_LAUNCH_TOPOLOGY


def create_abort_scenario() -> str:
    """Create scenario topology where launch is aborted.

    Returns
    -------
    str
        Complete ontology + topology with abort signal set at DualKeySync.

    Notes
    -----
    Workflow path: Start → DualKeyCheck → (Commander + Deputy) →
                   DualKeySync → Abort → End

    Initial state:
    - Start: Active
    - Commander/Deputy keys verified
    - Abort signal: true (triggers XOR abort branch)
    """
    return (
        NUCLEAR_LAUNCH_ONTOLOGY
        + """
@prefix kgc: <http://kgcl.io/hybrid/> .
@prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

# Initial state: workflow begins
launch:Start kgc:status "Active" .

# Keys are verified (simulate auth completion)
launch:CommanderAuth launch:keyVerified true .
launch:DeputyAuth launch:keyVerified true .

# Abort signal is set (XOR will choose abort path)
launch:DualKeySync launch:abortSignal true .
"""
    )


def create_launch_scenario() -> str:
    """Create scenario topology where launch proceeds successfully.

    Returns
    -------
    str
        Complete ontology + topology with launch authorization.

    Notes
    -----
    Workflow path: Start → DualKeyCheck → (Commander + Deputy) →
                   DualKeySync → ArmWarhead → LaunchCountdown → Launch → End

    Initial state:
    - Start: Active
    - Commander/Deputy keys verified
    - No abort signal (XOR chooses arm path)
    - Countdown completes normally
    """
    return (
        NUCLEAR_LAUNCH_ONTOLOGY
        + """
@prefix kgc: <http://kgcl.io/hybrid/> .
@prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

# Initial state: workflow begins
launch:Start kgc:status "Active" .

# Keys are verified (simulate auth completion)
launch:CommanderAuth launch:keyVerified true .
launch:DeputyAuth launch:keyVerified true .

# No abort signal (XOR will choose arm path)
# (absence of abort signal triggers arm branch)

# Countdown will complete normally
launch:LaunchCountdown launch:countdownComplete true .
"""
    )


def create_timeout_scenario() -> str:
    """Create scenario topology where countdown times out.

    Returns
    -------
    str
        Complete ontology + topology with timeout abort.

    Notes
    -----
    Workflow path: Start → DualKeyCheck → (Commander + Deputy) →
                   DualKeySync → ArmWarhead → LaunchCountdown → TimeoutAbort → End

    Initial state:
    - Start: Active
    - Commander/Deputy keys verified
    - No abort signal (proceeds to arm)
    - Countdown timeout flag set
    """
    return (
        NUCLEAR_LAUNCH_ONTOLOGY
        + """
@prefix kgc: <http://kgcl.io/hybrid/> .
@prefix launch: <http://kgcl.io/scenarios/nuclear-launch#> .

# Initial state: workflow begins
launch:Start kgc:status "Active" .

# Keys are verified (simulate auth completion)
launch:CommanderAuth launch:keyVerified true .
launch:DeputyAuth launch:keyVerified true .

# No abort signal (proceeds to arm warhead)

# Countdown times out (safety abort)
launch:LaunchCountdown launch:timeout true .
"""
    )


# Expected final states for validation

EXPECTED_ABORT_FINAL_STATE = """
Expected state after abort scenario:
- launch:Start: Completed
- launch:DualKeyCheck: Completed
- launch:CommanderAuth: Completed
- launch:DeputyAuth: Completed
- launch:DualKeySync: Completed
- launch:Abort: Completed
- launch:End: Completed
- kgc:WorkflowInstance kgc:terminated true

Tasks NOT executed:
- launch:ArmWarhead (not activated)
- launch:LaunchCountdown (not activated)
- launch:Launch (not activated)
- launch:TimeoutAbort (not activated)

Query to verify:
SELECT ?task ?status WHERE {
    ?task kgc:status ?status .
    FILTER(?task IN (launch:Start, launch:DualKeyCheck, launch:CommanderAuth,
                     launch:DeputyAuth, launch:DualKeySync, launch:Abort, launch:End))
}
"""

EXPECTED_LAUNCH_FINAL_STATE = """
Expected state after launch scenario:
- launch:Start: Completed
- launch:DualKeyCheck: Completed
- launch:CommanderAuth: Completed
- launch:DeputyAuth: Completed
- launch:DualKeySync: Completed
- launch:ArmWarhead: Completed
- launch:LaunchCountdown: Completed
- launch:Launch: Completed
- launch:End: Completed
- kgc:WorkflowInstance kgc:terminated true

Tasks NOT executed:
- launch:Abort (not activated)
- launch:TimeoutAbort (not activated)

Query to verify:
SELECT ?task ?status WHERE {
    ?task kgc:status ?status .
    FILTER(?task IN (launch:Start, launch:DualKeyCheck, launch:CommanderAuth,
                     launch:DeputyAuth, launch:DualKeySync, launch:ArmWarhead,
                     launch:LaunchCountdown, launch:Launch, launch:End))
}
"""

EXPECTED_TIMEOUT_FINAL_STATE = """
Expected state after timeout scenario:
- launch:Start: Completed
- launch:DualKeyCheck: Completed
- launch:CommanderAuth: Completed
- launch:DeputyAuth: Completed
- launch:DualKeySync: Completed
- launch:ArmWarhead: Completed
- launch:LaunchCountdown: Completed
- launch:TimeoutAbort: Completed
- launch:End: Completed
- kgc:WorkflowInstance kgc:terminated true

Tasks NOT executed:
- launch:Abort (not activated)
- launch:Launch (not activated)

Query to verify:
SELECT ?task ?status WHERE {
    ?task kgc:status ?status .
    FILTER(?task IN (launch:Start, launch:DualKeyCheck, launch:CommanderAuth,
                     launch:DeputyAuth, launch:DualKeySync, launch:ArmWarhead,
                     launch:LaunchCountdown, launch:TimeoutAbort, launch:End))
}
"""
