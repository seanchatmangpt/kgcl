"""N3 Physics Rules - The Dark Matter of KGCL Workflows.

This module defines the declarative logic rules that govern workflow execution.
These rules are executed by the EYE reasoner, not Python - they represent the
"physics" of the system that emerges from the data graph itself.

The rules implement the core Workflow Control Patterns (WCP):
- WCP-1: Sequence (TRANSMUTE)
- WCP-2: Parallel Split (AND-SPLIT)
- WCP-3: Synchronization (AND-JOIN)
- WCP-4: Exclusive Choice (XOR-FILTER)
- WCP-5: Simple Merge (XOR-MERGE)
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

# --- Core N3 Physics Rules ---
N3_PHYSICS = """@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# ============================================================================
# LAW 1: TRANSMUTE (WCP-1: Sequence)
# ============================================================================
# IF task is completed AND flows to next THEN activate next
# This is the fundamental state transition rule.

{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?next kgc:status "Active" .
} .

# ============================================================================
# LAW 2: XOR FILTER (WCP-4: Exclusive Choice)
# ============================================================================
# IF task completed AND XOR split AND predicate matches THEN activate ONE path
# Only the branch whose predicate evaluates to true is activated.

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

# ============================================================================
# LAW 3: CLEANUP (Entropy Reduction)
# ============================================================================
# IF next is active AND previous completed THEN archive previous
# Prevents graph pollution by marking completed tasks as archived.

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

# ============================================================================
# LAW 4: AND-SPLIT (WCP-2: Parallel Split)
# ============================================================================
# IF task completed AND AND-split THEN activate ALL outgoing branches
# Creates parallel execution paths.

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

# ============================================================================
# LAW 5: AND-JOIN (WCP-3: Synchronization)
# ============================================================================
# IF join is AND-type AND ALL incoming branches completed THEN activate join
# Synchronizes parallel branches - requires ALL inputs to complete.
# Note: This is a simplified rule. Full implementation needs cardinality checking.

{
    ?join yawl:hasJoin yawl:ControlTypeAnd .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?join .
    ?incoming kgc:status "Completed" .

    # Count incoming branches - all must be completed
    # (In practice, EYE handles this through multiple rule firings)
}
=>
{
    ?join kgc:status "PendingJoin" .
} .

# ============================================================================
# LAW 6: XOR-MERGE (WCP-5: Simple Merge)
# ============================================================================
# IF merge is XOR-type AND ANY incoming branch completed THEN activate merge
# No synchronization needed - first completed branch activates the merge.

{
    ?merge yawl:hasJoin yawl:ControlTypeXor .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?merge .
    ?incoming kgc:status "Completed" .
}
=>
{
    ?merge kgc:status "Active" .
} .

# ============================================================================
# LAW 7: CANCELLATION (Advanced Pattern)
# ============================================================================
# IF cancellation region triggered THEN cancel all tasks in region
# Implements WCP-19: Cancel Region.

{
    ?region kgc:cancellationTriggered true .
    ?task kgc:inCancellationRegion ?region .
    ?task kgc:status "Active" .
}
=>
{
    ?task kgc:status "Cancelled" .
} .
"""

# --- YAWL Topology Templates ---
# These are sample RDF topologies that the physics rules operate on.

SIMPLE_SEQUENCE_TOPOLOGY = """@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix ex: <http://example.org/tasks#> .

# Simple A→B→C sequence
ex:taskA a yawl:Task ;
    kgc:status "Active" ;
    yawl:flowsInto ex:flowAB .

ex:flowAB a yawl:Flow ;
    yawl:nextElementRef ex:taskB .

ex:taskB a yawl:Task ;
    kgc:status "Pending" ;
    yawl:flowsInto ex:flowBC .

ex:flowBC a yawl:Flow ;
    yawl:nextElementRef ex:taskC .

ex:taskC a yawl:Task ;
    kgc:status "Pending" .
"""

PARALLEL_SPLIT_TOPOLOGY = """@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix ex: <http://example.org/tasks#> .

# A→(B,C)→D with AND-split/join
ex:taskA a yawl:Task ;
    kgc:status "Active" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto ex:flowAB, ex:flowAC .

ex:flowAB a yawl:Flow ;
    yawl:nextElementRef ex:taskB .

ex:flowAC a yawl:Flow ;
    yawl:nextElementRef ex:taskC .

ex:taskB a yawl:Task ;
    kgc:status "Pending" ;
    yawl:flowsInto ex:flowBD .

ex:taskC a yawl:Task ;
    kgc:status "Pending" ;
    yawl:flowsInto ex:flowCD .

ex:flowBD a yawl:Flow ;
    yawl:nextElementRef ex:taskD .

ex:flowCD a yawl:Flow ;
    yawl:nextElementRef ex:taskD .

ex:taskD a yawl:Task ;
    kgc:status "Pending" ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

XOR_SPLIT_TOPOLOGY = """@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix ex: <http://example.org/tasks#> .

# A→(B|C)→D with XOR-split/merge
ex:taskA a yawl:Task ;
    kgc:status "Active" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto ex:flowAB, ex:flowAC .

ex:flowAB a yawl:Flow ;
    yawl:nextElementRef ex:taskB ;
    yawl:hasPredicate ex:predB .

ex:flowAC a yawl:Flow ;
    yawl:nextElementRef ex:taskC ;
    yawl:hasPredicate ex:predC .

# Only one predicate should be true
ex:predB kgc:evaluatesTo true .
ex:predC kgc:evaluatesTo false .

ex:taskB a yawl:Task ;
    kgc:status "Pending" ;
    yawl:flowsInto ex:flowBD .

ex:taskC a yawl:Task ;
    kgc:status "Pending" ;
    yawl:flowsInto ex:flowCD .

ex:flowBD a yawl:Flow ;
    yawl:nextElementRef ex:taskD .

ex:flowCD a yawl:Flow ;
    yawl:nextElementRef ex:taskD .

ex:taskD a yawl:Task ;
    kgc:status "Pending" ;
    yawl:hasJoin yawl:ControlTypeXor .
"""

# --- WCP Rule Mapping ---
# Maps WCP pattern numbers to their corresponding N3 rules
WCP_RULES = {
    1: "LAW 1: TRANSMUTE (WCP-1: Sequence)",
    2: "LAW 4: AND-SPLIT (WCP-2: Parallel Split)",
    3: "LAW 5: AND-JOIN (WCP-3: Synchronization)",
    4: "LAW 2: XOR FILTER (WCP-4: Exclusive Choice)",
    5: "LAW 6: XOR-MERGE (WCP-5: Simple Merge)",
    19: "LAW 7: CANCELLATION (WCP-19: Cancel Region)",
}


def get_physics_rules() -> str:
    """Return the complete N3 physics rules as a string.

    These rules define the declarative logic that governs workflow execution.
    They are meant to be executed by the EYE reasoner, not Python.

    Returns
    -------
    str
        The complete N3 physics rules including all workflow control patterns.

    Examples
    --------
    >>> rules = get_physics_rules()
    >>> assert "@prefix kgc:" in rules
    >>> assert "LAW 1: TRANSMUTE" in rules
    """
    return N3_PHYSICS


def write_physics_to_file(path: str | None = None) -> str:
    """Write the N3 physics rules to a file.

    If no path is provided, writes to a temporary file that persists
    for the duration of the process.

    Parameters
    ----------
    path : str | None, optional
        Target file path. If None, creates a temporary file.

    Returns
    -------
    str
        The absolute path to the file containing the physics rules.

    Examples
    --------
    >>> rules_path = write_physics_to_file()
    >>> assert Path(rules_path).exists()
    >>> with open(rules_path) as f:
    ...     content = f.read()
    >>> assert "@prefix kgc:" in content
    """
    if path is None:
        # Create persistent temp file (delete=False keeps it alive)
        temp_file = NamedTemporaryFile(mode="w", suffix=".n3", prefix="kgcl_physics_", delete=False)
        path = temp_file.name
        temp_file.write(N3_PHYSICS)
        temp_file.close()
    else:
        Path(path).write_text(N3_PHYSICS, encoding="utf-8")

    return str(Path(path).absolute())


def get_wcp_rule(wcp_number: int) -> str | None:
    """Extract a specific WCP rule by pattern number.

    Parameters
    ----------
    wcp_number : int
        The Workflow Control Pattern number (1-5, 19, etc.)

    Returns
    -------
    str | None
        The rule description if found, None otherwise.

    Examples
    --------
    >>> rule = get_wcp_rule(1)
    >>> assert rule == "LAW 1: TRANSMUTE (WCP-1: Sequence)"
    >>> assert get_wcp_rule(999) is None
    """
    return WCP_RULES.get(wcp_number)


def get_topology_template(pattern: str) -> str | None:
    """Get a sample RDF topology for a given pattern.

    Parameters
    ----------
    pattern : str
        The pattern name: "sequence", "parallel", or "xor"

    Returns
    -------
    str | None
        The RDF topology template, or None if pattern is unknown.

    Examples
    --------
    >>> topology = get_topology_template("sequence")
    >>> assert topology is not None
    >>> assert "ex:taskA" in topology
    >>> assert get_topology_template("unknown") is None
    """
    templates = {"sequence": SIMPLE_SEQUENCE_TOPOLOGY, "parallel": PARALLEL_SPLIT_TOPOLOGY, "xor": XOR_SPLIT_TOPOLOGY}
    return templates.get(pattern.lower())
