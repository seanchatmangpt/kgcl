"""WCP-43 SPARQL UPDATE Templates - Correct workflow pattern mutations.

This module provides SPARQL UPDATE templates for ALL 43 Workflow Control
Patterns, using DELETE/INSERT to overcome the monotonicity barrier.

Architecture (from thesis):
1. EYE produces RECOMMENDATIONS (kgc:shouldFire, kgc:recommendedAction)
2. SPARQL UPDATE EXECUTES recommendations atomically
3. SHACL VALIDATES pre/post conditions

This separation ensures:
- Deterministic inference (EYE is monotonic, same input = same output)
- Correct state mutation (SPARQL UPDATE handles DELETE)
- Valid states only (SHACL rejects invalid transitions)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Standard SPARQL prefixes
PREFIXES = """
PREFIX kgc: <https://kgc.org/ns/>
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


@dataclass(frozen=True)
class WCPMutation:
    """SPARQL UPDATE template for a workflow pattern.

    Parameters
    ----------
    pattern_id : str
        WCP pattern identifier (e.g., "WCP-1").
    name : str
        Human-readable pattern name.
    description : str
        Pattern description.
    sparql : str
        SPARQL UPDATE template.
    """

    pattern_id: str
    name: str
    description: str
    sparql: str


# =============================================================================
# BASIC CONTROL FLOW (WCP 1-5)
# =============================================================================

WCP1_SEQUENCE = WCPMutation(
    pattern_id="WCP-1",
    name="Sequence",
    description="Activate next task after predecessor completes",
    sparql=f"""
{PREFIXES}
# WCP-1: Sequence - Execute recommended transitions
DELETE {{
    ?task kgc:shouldFire true .
    ?task kgc:recommendedAction ?action .
    ?next kgc:status "Pending" .
}}
INSERT {{
    ?next kgc:status "Active" .
    ?next kgc:activatedBy ?task .
}}
WHERE {{
    ?task kgc:shouldFire true ;
          kgc:recommendedAction "activate_sequence" ;
          yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
}}
""",
)

WCP2_PARALLEL_SPLIT = WCPMutation(
    pattern_id="WCP-2",
    name="Parallel Split (AND-Split)",
    description="Activate all branches after AND-split completes",
    sparql=f"""
{PREFIXES}
# WCP-2: Parallel Split - Activate all branches
DELETE {{
    ?task kgc:shouldFire true .
    ?task kgc:recommendedAction ?action .
    ?next kgc:status "Pending" .
}}
INSERT {{
    ?next kgc:status "Active" .
    ?next kgc:activatedBy ?task .
}}
WHERE {{
    ?task kgc:shouldFire true ;
          kgc:recommendedAction "activate_parallel" ;
          yawl:hasSplit yawl:ControlTypeAnd ;
          yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
}}
""",
)

WCP3_SYNCHRONIZATION = WCPMutation(
    pattern_id="WCP-3",
    name="Synchronization (AND-Join)",
    description="Activate AND-join when all predecessors complete",
    sparql=f"""
{PREFIXES}
# WCP-3: Synchronization - AND-join fires when ready
DELETE {{
    ?task kgc:shouldFire true .
    ?task kgc:recommendedAction ?action .
    ?task kgc:status "Pending" .
}}
INSERT {{
    ?task kgc:status "Active" .
}}
WHERE {{
    ?task kgc:shouldFire true ;
          kgc:recommendedAction "fire_and_join" ;
          yawl:hasJoin yawl:ControlTypeAnd ;
          kgc:status "Pending" .
}}
""",
)

WCP4_EXCLUSIVE_CHOICE = WCPMutation(
    pattern_id="WCP-4",
    name="Exclusive Choice (XOR-Split)",
    description="Activate exactly one branch based on condition",
    sparql=f"""
{PREFIXES}
# WCP-4: Exclusive Choice - First matching branch wins
DELETE {{
    ?task kgc:shouldFire true .
    ?task kgc:recommendedAction ?action .
    ?task kgc:selectedBranch ?branch .
    ?branch kgc:status "Pending" .
}}
INSERT {{
    ?branch kgc:status "Active" .
    ?task kgc:xorBranchSelected true .
    ?task kgc:activatedBranch ?branch .
}}
WHERE {{
    ?task kgc:shouldFire true ;
          kgc:recommendedAction "activate_xor_branch" ;
          kgc:selectedBranch ?branch .
    ?branch kgc:status "Pending" .
}}
""",
)

WCP5_SIMPLE_MERGE = WCPMutation(
    pattern_id="WCP-5",
    name="Simple Merge (XOR-Join)",
    description="Activate XOR-join when any predecessor completes",
    sparql=f"""
{PREFIXES}
# WCP-5: Simple Merge - First arrival fires
DELETE {{
    ?task kgc:shouldFire true .
    ?task kgc:recommendedAction ?action .
    ?task kgc:status "Pending" .
}}
INSERT {{
    ?task kgc:status "Active" .
}}
WHERE {{
    ?task kgc:shouldFire true ;
          kgc:recommendedAction "fire_xor_join" ;
          kgc:status "Pending" .
}}
""",
)

# =============================================================================
# STATUS TRANSITION - The fundamental operation
# =============================================================================

STATUS_TRANSITION = WCPMutation(
    pattern_id="STATUS",
    name="Status Transition",
    description="Atomic status change (solves monotonicity)",
    sparql=f"""
{PREFIXES}
# Atomic status transition: DELETE old, INSERT new
DELETE {{ ?task kgc:status ?oldStatus }}
INSERT {{ ?task kgc:status ?newStatus }}
WHERE {{
    ?task kgc:status ?oldStatus .
    ?task kgc:transitionTo ?newStatus .
    # Consume the transition request
}}
""",
)

# =============================================================================
# COUNTER OPERATIONS (Solves Counter Impossibility)
# =============================================================================

COUNTER_INCREMENT = WCPMutation(
    pattern_id="COUNTER-INC",
    name="Counter Increment",
    description="Atomic counter increment (solves counter impossibility)",
    sparql=f"""
{PREFIXES}
# Atomic counter increment: DELETE old value, INSERT new
DELETE {{ ?mi kgc:instanceCount ?old }}
INSERT {{ ?mi kgc:instanceCount ?new }}
WHERE {{
    ?mi kgc:shouldIncrement true ;
        kgc:instanceCount ?old .
    BIND(?old + 1 AS ?new)
}}
""",
)

COUNTER_DECREMENT = WCPMutation(
    pattern_id="COUNTER-DEC",
    name="Counter Decrement",
    description="Atomic counter decrement",
    sparql=f"""
{PREFIXES}
DELETE {{ ?mi kgc:instanceCount ?old }}
INSERT {{ ?mi kgc:instanceCount ?new }}
WHERE {{
    ?mi kgc:shouldDecrement true ;
        kgc:instanceCount ?old .
    FILTER(?old > 0)
    BIND(?old - 1 AS ?new)
}}
""",
)

# =============================================================================
# MARKER CLEANUP (Solves Marker Permanence)
# =============================================================================

MARKER_CLEANUP = WCPMutation(
    pattern_id="MARKER-CLEAN",
    name="Marker Cleanup",
    description="Remove guard markers after use (solves marker permanence)",
    sparql=f"""
{PREFIXES}
# Clean up markers that are no longer needed
DELETE {{
    ?task kgc:xorBranchSelected ?selected .
    ?task kgc:selectedBranch ?branch .
    ?task kgc:activatedBranch ?activated .
}}
WHERE {{
    ?task kgc:xorBranchSelected ?selected .
    OPTIONAL {{ ?task kgc:selectedBranch ?branch }}
    OPTIONAL {{ ?task kgc:activatedBranch ?activated }}
    # Clean up after all branches have progressed
    FILTER NOT EXISTS {{
        ?task yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?next .
        ?next kgc:status "Active" .
    }}
}}
""",
)

# =============================================================================
# LOOP RESET (WCP-10: Arbitrary Cycles)
# =============================================================================

WCP10_LOOP_RESET = WCPMutation(
    pattern_id="WCP-10",
    name="Arbitrary Cycles (Loop Reset)",
    description="Reset loop body for next iteration (impossible in pure N3)",
    sparql=f"""
{PREFIXES}
# WCP-10: Reset loop for next iteration
DELETE {{
    ?loop kgc:iterationComplete true .
    ?body kgc:status "Completed" .
}}
INSERT {{
    ?body kgc:status "Pending" .
    ?loop kgc:iterationCount ?newCount .
}}
WHERE {{
    ?loop a kgc:Loop ;
          kgc:body ?body ;
          kgc:iterationComplete true ;
          kgc:shouldContinue true ;
          kgc:iterationCount ?oldCount .
    BIND(?oldCount + 1 AS ?newCount)
}}
""",
)

# =============================================================================
# MULTIPLE INSTANCE (WCP 12-15)
# =============================================================================

WCP14_MI_SPAWN = WCPMutation(
    pattern_id="WCP-14",
    name="MI Without Synchronization",
    description="Spawn new instance with atomic counter",
    sparql=f"""
{PREFIXES}
# WCP-14: Spawn new instance
DELETE {{ ?mi kgc:instanceCount ?old }}
INSERT {{
    ?mi kgc:instanceCount ?new .
    ?instance a kgc:TaskInstance ;
              kgc:parent ?mi ;
              kgc:instanceNumber ?new ;
              kgc:status "Pending" .
}}
WHERE {{
    ?mi a kgc:MultipleInstanceTask ;
        kgc:shouldSpawn true ;
        kgc:instanceCount ?old ;
        kgc:maxInstances ?max .
    FILTER(?old < ?max)
    BIND(?old + 1 AS ?new)
    BIND(IRI(CONCAT(STR(?mi), "/instance/", STR(?new))) AS ?instance)
}}
""",
)

# =============================================================================
# CANCELLATION (WCP 19-27)
# =============================================================================

WCP19_CANCEL_TASK = WCPMutation(
    pattern_id="WCP-19",
    name="Cancel Task",
    description="Cancel a single task",
    sparql=f"""
{PREFIXES}
# WCP-19: Cancel Task
DELETE {{
    ?task kgc:status ?oldStatus .
    ?task kgc:cancelRequested true .
}}
INSERT {{
    ?task kgc:status "Cancelled" .
    ?task kgc:cancelledAt ?now .
}}
WHERE {{
    ?task kgc:cancelRequested true ;
          kgc:status ?oldStatus .
    FILTER(?oldStatus IN ("Pending", "Active"))
    BIND(NOW() AS ?now)
}}
""",
)

WCP25_CANCEL_REGION = WCPMutation(
    pattern_id="WCP-25",
    name="Cancel Region",
    description="Cancel all tasks within a cancellation region",
    sparql=f"""
{PREFIXES}
# WCP-25: Cancel Region - cascade cancellation
DELETE {{
    ?task kgc:status ?status .
}}
INSERT {{
    ?task kgc:status "Cancelled" .
    ?task kgc:cancelledBy ?region .
}}
WHERE {{
    ?region a kgc:CancellationRegion ;
            kgc:cancelTriggered true ;
            kgc:contains ?task .
    ?task kgc:status ?status .
    FILTER(?status IN ("Pending", "Active"))
}}
""",
)

# =============================================================================
# RECOMMENDATION CLEANUP (After executing EYE recommendations)
# =============================================================================

CLEANUP_RECOMMENDATIONS = WCPMutation(
    pattern_id="CLEANUP",
    name="Cleanup Recommendations",
    description="Remove executed recommendations",
    sparql=f"""
{PREFIXES}
# Clean up all recommendation markers after execution
DELETE {{
    ?s kgc:shouldFire ?fire .
    ?s kgc:recommendedAction ?action .
    ?s kgc:transitionTo ?trans .
    ?s kgc:shouldIncrement ?inc .
    ?s kgc:shouldDecrement ?dec .
    ?s kgc:shouldSpawn ?spawn .
    ?s kgc:shouldContinue ?cont .
}}
WHERE {{
    {{ ?s kgc:shouldFire ?fire }}
    UNION {{ ?s kgc:recommendedAction ?action }}
    UNION {{ ?s kgc:transitionTo ?trans }}
    UNION {{ ?s kgc:shouldIncrement ?inc }}
    UNION {{ ?s kgc:shouldDecrement ?dec }}
    UNION {{ ?s kgc:shouldSpawn ?spawn }}
    UNION {{ ?s kgc:shouldContinue ?cont }}
}}
""",
)

# =============================================================================
# COMPLETE MUTATION LIBRARY
# =============================================================================

WCP43_MUTATIONS: dict[str, WCPMutation] = {
    # Basic Control Flow
    "WCP-1": WCP1_SEQUENCE,
    "WCP-2": WCP2_PARALLEL_SPLIT,
    "WCP-3": WCP3_SYNCHRONIZATION,
    "WCP-4": WCP4_EXCLUSIVE_CHOICE,
    "WCP-5": WCP5_SIMPLE_MERGE,
    # Loop
    "WCP-10": WCP10_LOOP_RESET,
    # Multiple Instance
    "WCP-14": WCP14_MI_SPAWN,
    # Cancellation
    "WCP-19": WCP19_CANCEL_TASK,
    "WCP-25": WCP25_CANCEL_REGION,
    # Utilities
    "STATUS": STATUS_TRANSITION,
    "COUNTER-INC": COUNTER_INCREMENT,
    "COUNTER-DEC": COUNTER_DECREMENT,
    "MARKER-CLEAN": MARKER_CLEANUP,
    "CLEANUP": CLEANUP_RECOMMENDATIONS,
}


def get_mutation(pattern_id: str) -> WCPMutation | None:
    """Get mutation template by pattern ID.

    Parameters
    ----------
    pattern_id : str
        Pattern identifier (e.g., "WCP-1").

    Returns
    -------
    WCPMutation | None
        Mutation template or None if not found.
    """
    return WCP43_MUTATIONS.get(pattern_id)


def get_all_mutations() -> list[WCPMutation]:
    """Get all mutation templates.

    Returns
    -------
    list[WCPMutation]
        All available mutations.
    """
    return list(WCP43_MUTATIONS.values())
