"""TRUE Hybrid KGC Engine - PyOxigraph + EYE Reasoner.

This module implements the RESEARCH-POC.md architecture:
- PyOxigraph = Matter (Inert State Storage in Rust)
- EYE Reasoner = Physics (External Force via subprocess)
- Python = Time (Tick Controller/Orchestrator)

Philosophy
----------
Hard Separation:
- PyOxigraph is purely a container for facts. It has no reasoning capabilities.
- EYE is a dedicated inference engine. It accepts Matter + Rules and outputs New Matter.
- Python creates the Epochs (Ticks) and orchestrates the feedback loop.

Architecture
------------
1. State ($T_0$): Facts stored in PyOxigraph
2. Logic Application: Python exports State + Rules → EYE
3. Deduction: EYE returns the Implication (The Delta)
4. Evolution ($T_1$): Python inserts Delta → PyOxigraph

This visualizes Logic as a Force applied to State as Mass.

Prerequisites
-------------
- pyoxigraph: pip install pyoxigraph
- eye: Euler reasoner installed and in system PATH

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>>
>>> # Create engine with in-memory store
>>> engine = HybridEngine()
>>>
>>> # Load initial topology
>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
...
... <urn:task:Start> a yawl:Task ;
...     kgc:status "Completed" ;
...     yawl:flowsInto <urn:flow:1> .
...
... <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
... <urn:task:Next> a yawl:Task .
... '''
>>> engine.load_data(topology)
>>>
>>> # Apply physics (one tick)
>>> result = engine.apply_physics()
>>> result.tick_number
1
>>> result.delta > 0  # New triples were inferred
True
>>>
>>> # Run to completion
>>> results = engine.run_to_completion(max_ticks=10)
>>> len(results)
2
>>> all(r.delta >= 0 for r in results)
True
"""

from __future__ import annotations

import io
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyoxigraph as ox

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ==============================================================================
# STRATUM 1: DARK MATTER (N3 Physics Rules)
# ==============================================================================
# N3 (Notation3) supports Implication (=>), making it far more powerful than
# SPARQL for defining "Laws" that govern knowledge graph evolution.

N3_PHYSICS = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix string: <http://www.w3.org/2000/10/swap/string#> .
@prefix list: <http://www.w3.org/2000/10/swap/list#> .
@prefix math: <http://www.w3.org/2000/10/swap/math#> .

# =============================================================================
# WORKFLOW PHYSICS FOR NUCLEAR LAUNCH SCENARIO
# =============================================================================
# These rules implement YAWL Workflow Control Patterns using monotonic reasoning.
# Each status transition creates a new status assertion with higher version.
# The inspect() method queries for the maximum version per task.
#
# CRITICAL: XOR-split handling requires careful rule design to ensure exclusivity.
# Only ONE branch of an XOR should activate - either the predicated path (if true)
# or the default path (if predicate is false).

# =============================================================================
# LAW 1: SIMPLE SEQUENCE (WCP-1: Tasks without split control)
# =============================================================================
# For tasks that do NOT have any split control, just flow to next.
# This rule uses scoped negation-as-failure via log:notIncludes.
# CRITICAL: Do NOT fire if:
#   1. The current task has a split control (handled by LAW 2/4)
#   2. The next task has a join control (handled by LAW 3)
#   3. The next task requires a milestone (handled by LAW 16)
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    # Guard 1: Only fire if task has NO split type (simple sequence)
    ?scope log:notIncludes { ?task yawl:hasSplit ?anySplit } .
    # Guard 2: Only fire if NEXT task has NO join type (let AND-JOIN handle it)
    ?scope log:notIncludes { ?next yawl:hasJoin ?anyJoin } .
    # Guard 3: Only fire if NEXT task has NO milestone requirement (let LAW 16 handle it)
    ?scope log:notIncludes { ?next kgc:requiresMilestone ?anyMilestone } .
}
=>
{
    ?next kgc:status "Active" .
} .

# =============================================================================
# LAW 2: AND-SPLIT (WCP-2: Parallel Split)
# =============================================================================
# If task has AND-split, activate ALL outgoing branches in parallel
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

# =============================================================================
# LAW 3: AND-JOIN (WCP-3: Synchronization)
# =============================================================================
# Join task activates only when ALL incoming branches are completed.
# CRITICAL: prev1 and prev2 MUST be DIFFERENT tasks.
# Uses log:uri + string:notEqualIgnoringCase for EYE-compatible inequality.
{
    ?join yawl:hasJoin yawl:ControlTypeAnd .
    ?prev1 yawl:flowsInto ?flow1 .
    ?flow1 yawl:nextElementRef ?join .
    ?prev1 kgc:status "Completed" .
    ?prev2 yawl:flowsInto ?flow2 .
    ?flow2 yawl:nextElementRef ?join .
    ?prev2 kgc:status "Completed" .
    # CRITICAL: Ensure prev1 and prev2 are DISTINCT tasks
    # EYE requires log:uri + string comparison for IRI inequality
    ?prev1 log:uri ?prev1uri .
    ?prev2 log:uri ?prev2uri .
    ?prev1uri string:notEqualIgnoringCase ?prev2uri .
}
=>
{
    ?join kgc:status "Active" .
} .

# =============================================================================
# LAW 4: XOR-SPLIT WITH TRUE PREDICATE (WCP-4: Exclusive Choice)
# =============================================================================
# If predicate evaluates to TRUE, take that branch (exclusive)
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

# =============================================================================
# LAW 4b: XOR-SPLIT DEFAULT PATH (when predicate is FALSE)
# =============================================================================
# If predicate evaluates to FALSE, take the default path instead
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeXor .
    ?task yawl:flowsInto ?defaultFlow .
    ?defaultFlow yawl:nextElementRef ?next .
    ?defaultFlow yawl:isDefaultFlow true .
    # Verify the predicate flow evaluates to false
    ?task yawl:flowsInto ?predicateFlow .
    ?predicateFlow yawl:hasPredicate ?pred .
    ?pred kgc:evaluatesTo false .
}
=>
{
    ?next kgc:status "Active" .
} .

# =============================================================================
# LAW 5: AUTO-COMPLETE (Tasks with outgoing flows, NOT manual)
# =============================================================================
# Active tasks with outgoing flows complete automatically (instant task).
# EXCLUDES tasks marked as kgc:requiresManualCompletion (e.g., human auth).
# EXCLUDES tasks that require a milestone (handled by LAW 16).
{
    ?task kgc:status "Active" .
    ?task yawl:flowsInto ?flow .
    # Guard: Only auto-complete if NOT a manual task
    ?scope log:notIncludes { ?task kgc:requiresManualCompletion true } .
    # Guard: Only auto-complete if NOT requiring a milestone
    ?scope log:notIncludes { ?task kgc:requiresMilestone ?anyMilestone } .
}
=>
{
    ?task kgc:status "Completed" .
} .

# =============================================================================
# LAW 6: TERMINAL COMPLETION (End Tasks, NOT manual)
# =============================================================================
# Active tasks that are typed as Task complete (terminal states).
# EXCLUDES tasks marked as kgc:requiresManualCompletion.
# EXCLUDES tasks that require a milestone (handled by LAW 16).
{
    ?task kgc:status "Active" .
    ?task a yawl:Task .
    # Guard: Only auto-complete if NOT a manual task
    ?scope log:notIncludes { ?task kgc:requiresManualCompletion true } .
    # Guard: Only auto-complete if NOT requiring a milestone
    ?scope log:notIncludes { ?task kgc:requiresMilestone ?anyMilestone } .
}
=>
{
    ?task kgc:status "Completed" .
} .

# =============================================================================
# LAW 7: ARCHIVE (Status Progression for observability)
# =============================================================================
# Completed tasks get archived when their successors become active
{
    ?prev kgc:status "Completed" .
    ?prev yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Active" .
}
=>
{
    ?prev kgc:status "Archived" .
} .

# =============================================================================
# TIER V LAWS: ADVANCED WORKFLOW PATTERNS (WCP-17, 28-38)
# =============================================================================
# These patterns require GLOBAL knowledge (aggregation across multiple paths).
# Implemented using EYE builtins: log:collectAllIn, list:length, list:first, math:*
# ALL STATE IS STORED IN THE GRAPH - NO EXTERNAL PYTHON STATE.

# =============================================================================
# LAW 8: N-WAY AND-JOIN (WCP-3 Generalized: n predecessors)
# =============================================================================
# Join activates when ALL expected predecessors are completed.
# Uses log:collectAllIn to gather all completed predecessors and count them.
# State: kgc:expectedPredecessors stored in graph.
{
    ?join yawl:hasJoin yawl:ControlTypeAnd .
    ?join kgc:expectedPredecessors ?expected .

    # Collect all completed predecessors into a list
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?join . ?pred kgc:status "Completed" } ?preds ) log:collectAllIn _:scope .

    # Count them
    ?preds list:length ?count .

    # Fire only when count equals expected
    ?count math:equalTo ?expected .
}
=>
{
    ?join kgc:status "Active" .
    ?join kgc:predecessorCount ?count .
} .

# =============================================================================
# LAW 9: K-OF-N PARTIAL JOIN (WCP-30: Partial Join)
# =============================================================================
# Join activates when K or more predecessors are completed (out of N total).
# State: kgc:requiredPredecessors (k) stored in graph.
{
    ?join yawl:hasJoin kgc:PartialJoin .
    ?join kgc:requiredPredecessors ?k .

    # Collect all completed predecessors
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?join . ?pred kgc:status "Completed" } ?completed ) log:collectAllIn _:scope .

    # Count completed
    ?completed list:length ?count .

    # Fire when count >= k (notLessThan means >=)
    ?count math:notLessThan ?k .
}
=>
{
    ?join kgc:status "Active" .
    ?join kgc:completedCount ?count .
} .

# =============================================================================
# LAW 10: BLOCKING DISCRIMINATOR (WCP-28: Blocking Discriminator)
# =============================================================================
# First completed predecessor wins; others are blocked.
# Uses list:first for DETERMINISTIC selection (lexicographic order by IRI).
# State: kgc:winner stored in graph.
{
    ?discrim yawl:hasJoin kgc:BlockingDiscriminator .

    # Collect all completed predecessors
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?discrim . ?pred kgc:status "Completed" } ?completed ) log:collectAllIn _:scope .

    # Must have at least one completed
    ?completed list:length ?count .
    ?count math:greaterThan 0 .

    # Pick the first one (deterministic - list is sorted by IRI)
    ?completed list:first ?winner .
}
=>
{
    ?discrim kgc:status "Active" .
    ?discrim kgc:winner ?winner .
} .

# =============================================================================
# LAW 11: SYNCHRONIZING MERGE (WCP-37: Local Synchronizing Merge)
# =============================================================================
# Merge activates when ALL ACTIVATED paths are completed.
# State: kgc:wasActivated marker stored IN THE GRAPH (not external Python).
# This handles dynamic path activation from OR-splits.
{
    ?merge yawl:hasJoin kgc:SynchronizingMerge .

    # Collect all ACTIVATED predecessors (marked in graph)
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?merge . ?pred kgc:wasActivated true } ?activated ) log:collectAllIn _:s1 .

    # Collect all COMPLETED predecessors
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?merge . ?pred kgc:status "Completed" } ?completed ) log:collectAllIn _:s2 .

    # Count both
    ?activated list:length ?activatedCount .
    ?completed list:length ?completedCount .

    # Fire only when ALL activated paths are completed
    ?completedCount math:equalTo ?activatedCount .
    ?activatedCount math:greaterThan 0 .
}
=>
{
    ?merge kgc:status "Active" .
    ?merge kgc:activatedPaths ?activatedCount .
    ?merge kgc:completedPaths ?completedCount .
} .

# =============================================================================
# LAW 12: ACTIVATION MARKER (State stored in graph, not Python)
# =============================================================================
# When a task becomes Active, mark it as wasActivated for sync merge tracking.
# This ensures ALL state is in the RDF graph, enabling pure N3 reasoning.
{
    ?task kgc:status "Active" .
}
=>
{
    ?task kgc:wasActivated true .
} .

# =============================================================================
# LAW 13: CANCELLING DISCRIMINATOR (WCP-29: Cancelling Discriminator)
# =============================================================================
# First completed predecessor wins; others are CANCELLED.
# Similar to blocking, but explicitly marks non-winners as cancelled.
{
    ?discrim yawl:hasJoin kgc:CancellingDiscriminator .

    # Collect all completed predecessors
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?discrim . ?pred kgc:status "Completed" } ?completed ) log:collectAllIn _:s1 .

    # Collect all active (non-completed) predecessors
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?discrim . ?pred kgc:status "Active" } ?active ) log:collectAllIn _:s2 .

    # Must have at least one completed
    ?completed list:length ?completedCount .
    ?completedCount math:greaterThan 0 .

    # Pick the winner
    ?completed list:first ?winner .
}
=>
{
    ?discrim kgc:status "Active" .
    ?discrim kgc:winner ?winner .
} .

# LAW 13b: Cancel non-winners for cancelling discriminator
{
    ?discrim yawl:hasJoin kgc:CancellingDiscriminator .
    ?discrim kgc:winner ?winner .
    ?other yawl:flowsInto ?f .
    ?f yawl:nextElementRef ?discrim .
    ?other kgc:status "Active" .
    # Ensure other is NOT the winner
    ?other log:uri ?otherUri .
    ?winner log:uri ?winnerUri .
    ?otherUri string:notEqualIgnoringCase ?winnerUri .
}
=>
{
    ?other kgc:status "Cancelled" .
} .

# =============================================================================
# LAW 14: STRUCTURED DISCRIMINATOR (WCP-9: Structured Discriminator)
# =============================================================================
# Wait for first N completions before activating (N configurable).
# State: kgc:discriminatorThreshold stored in graph.
{
    ?discrim yawl:hasJoin kgc:StructuredDiscriminator .
    ?discrim kgc:discriminatorThreshold ?threshold .

    # Collect all completed predecessors
    ( ?pred { ?pred yawl:flowsInto ?f . ?f yawl:nextElementRef ?discrim . ?pred kgc:status "Completed" } ?completed ) log:collectAllIn _:scope .

    # Count completed
    ?completed list:length ?count .

    # Fire when count >= threshold
    ?count math:notLessThan ?threshold .
}
=>
{
    ?discrim kgc:status "Active" .
    ?discrim kgc:completedCount ?count .
} .

# =============================================================================
# LAW 15: OR-SPLIT (WCP-6: Multi-Choice)
# =============================================================================
# Unlike XOR (exclusive), OR-split activates ALL branches whose predicates are true.
# Multiple branches can be activated simultaneously.
# This enables modeling scenarios like multiple amendments being active.
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeOr .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:hasPredicate ?pred .
    ?pred kgc:evaluatesTo true .
}
=>
{
    ?next kgc:status "Active" .
} .

# LAW 15b: OR-SPLIT DEFAULT (when no predicates are true)
# If OR-split has no true predicates, take the default path
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeOr .
    ?task yawl:flowsInto ?defaultFlow .
    ?defaultFlow yawl:nextElementRef ?next .
    ?defaultFlow yawl:isDefaultFlow true .
    # Only fire if ALL other predicates are false
    # This requires checking no predicate flow has evaluatesTo true
    ?scope log:notIncludes {
        ?task yawl:flowsInto ?anyFlow .
        ?anyFlow yawl:hasPredicate ?anyPred .
        ?anyPred kgc:evaluatesTo true
    } .
}
=>
{
    ?next kgc:status "Active" .
} .

# =============================================================================
# LAW 16: MILESTONE (WCP-18: Milestone)
# =============================================================================
# Tasks can require milestones to be reached before activation.
# State: kgc:requiresMilestone links task to milestone, milestone has kgc:reached.
{
    ?task kgc:requiresMilestone ?milestone .
    ?milestone kgc:status "Reached" .
    ?predecessor kgc:status "Completed" .
    ?predecessor yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?task .
}
=>
{
    ?task kgc:status "Active" .
} .

# LAW 16b: MILESTONE BLOCK (task blocked until milestone reached)
# When a task requires a milestone that hasn't been reached, it stays Waiting
{
    ?task kgc:requiresMilestone ?milestone .
    ?scope log:notIncludes { ?milestone kgc:status "Reached" } .
    ?predecessor kgc:status "Completed" .
    ?predecessor yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?task .
}
=>
{
    ?task kgc:status "Waiting" .
} .

# =============================================================================
# LAW 17: OR-JOIN (WCP-7: Structured Synchronizing Merge)
# =============================================================================
# OR-join activates when ANY predecessor completes (unlike AND-join which waits for all).
# This is the merge counterpart to OR-split.
{
    ?join yawl:hasJoin yawl:ControlTypeOr .
    ?prev yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?join .
    ?prev kgc:status "Completed" .
}
=>
{
    ?join kgc:status "Active" .
} .
"""


@dataclass(frozen=True)
class PhysicsResult:
    """Result of applying physics (one tick).

    Parameters
    ----------
    tick_number : int
        Sequential tick identifier.
    duration_ms : float
        Time taken for physics application in milliseconds.
    triples_before : int
        Triple count before physics application.
    triples_after : int
        Triple count after physics application.
    delta : int
        Change in triple count (triples_after - triples_before).

    Examples
    --------
    >>> result = PhysicsResult(tick_number=1, duration_ms=12.5, triples_before=100, triples_after=105, delta=5)
    >>> result.delta
    5
    >>> result.converged
    False
    """

    tick_number: int
    duration_ms: float
    triples_before: int
    triples_after: int
    delta: int

    @property
    def converged(self) -> bool:
        """Check if system reached fixed point (no changes).

        Returns
        -------
        bool
            True if delta is zero (no new triples inferred).

        Examples
        --------
        >>> result = PhysicsResult(1, 10.0, 100, 100, 0)
        >>> result.converged
        True
        >>> result2 = PhysicsResult(1, 10.0, 100, 105, 5)
        >>> result2.converged
        False
        """
        return self.delta == 0


class HybridEngine:
    """Hybrid KGC Engine with PyOxigraph storage and EYE reasoning.

    This engine implements the Hard Separation principle:
    - PyOxigraph stores the Inert State (Matter)
    - EYE reasoner applies the Physics (Force)
    - Python orchestrates the Time (Ticks)

    Parameters
    ----------
    store_path : str | None, optional
        Path for persistent storage. If None, uses in-memory store.

    Attributes
    ----------
    store : ox.Store
        PyOxigraph triple store (Rust-based).
    physics_file : str
        Path to temporary file containing N3 physics rules.
    tick_count : int
        Number of ticks executed.

    Examples
    --------
    >>> # In-memory engine
    >>> engine = HybridEngine()
    >>> engine.store
    <pyoxigraph.Store object at ...>
    >>>
    >>> # Persistent engine
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     engine = HybridEngine(store_path=tmpdir)
    ...     # Engine will persist to disk
    """

    def __init__(self, store_path: str | None = None) -> None:
        """Initialize the hybrid engine with PyOxigraph store.

        Parameters
        ----------
        store_path : str | None, optional
            Path for persistent storage. If None, uses in-memory store.
        """
        # 1. The Inert Store (PyOxigraph)
        if store_path is None:
            self.store = ox.Store()
            logger.info("Initialized in-memory PyOxigraph store")
        else:
            self.store = ox.Store(store_path)
            logger.info(f"Initialized persistent PyOxigraph store at {store_path}")

        # 2. Write Physics to Disk (For EYE)
        self._physics_fd, self.physics_file = tempfile.mkstemp(suffix=".n3", text=True)
        with os.fdopen(self._physics_fd, "w") as f:
            f.write(N3_PHYSICS)
        logger.info(f"Wrote N3 physics rules to {self.physics_file}")

        # 3. Track execution state
        self.tick_count = 0

    def __del__(self) -> None:
        """Cleanup physics file on destruction."""
        if hasattr(self, "physics_file") and os.path.exists(self.physics_file):
            os.unlink(self.physics_file)
            logger.debug(f"Cleaned up physics file {self.physics_file}")

    def load_data(self, turtle_data: str) -> None:
        """Ingest initial state from Turtle data.

        Parameters
        ----------
        turtle_data : str
            RDF data in Turtle format.

        Examples
        --------
        >>> engine = HybridEngine()
        >>> data = '''
        ... @prefix ex: <http://example.org/> .
        ... ex:task1 ex:status "pending" .
        ... '''
        >>> engine.load_data(data)
        >>> len(list(engine.store)) > 0
        True
        """
        self.store.load(input=turtle_data.encode("utf-8"), format=ox.RdfFormat.TURTLE)
        triple_count = len(list(self.store))
        logger.info(f"Loaded {triple_count} triples into store")

    def _dump_state(self) -> str:
        """Snapshot the current reality as Turtle.

        Returns
        -------
        str
            Current graph state serialized as Turtle.

        Examples
        --------
        >>> engine = HybridEngine()
        >>> engine.load_data("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        >>> state = engine._dump_state()
        >>> "ex:a" in state
        True
        """
        # PyOxigraph dumps to bytes, we need string for EYE input
        # Use TRIG format (supports datasets, Turtle-like syntax)
        result = self.store.dump(format=ox.RdfFormat.TRIG)
        if result is None:
            return ""
        return result.decode("utf-8")

    def apply_physics(self) -> PhysicsResult:
        """Execute one tick: Export → Reason → Ingest.

        This is the core Feedback Loop that demonstrates Gall's Law:
        1. Export State ($T_0$) from PyOxigraph
        2. Apply Logic (Rules) via EYE reasoner
        3. Ingest Delta back into PyOxigraph ($T_1$)

        Returns
        -------
        PhysicsResult
            Result of physics application with timing and delta metrics.

        Raises
        ------
        FileNotFoundError
            If EYE reasoner is not found in system PATH.
        subprocess.CalledProcessError
            If EYE reasoner fails during execution.

        Examples
        --------
        >>> engine = HybridEngine()
        >>> engine.load_data('''
        ... @prefix kgc: <https://kgc.org/ns/> .
        ... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        ... <urn:task:Start> kgc:status "Completed" ;
        ...     yawl:flowsInto <urn:flow:1> .
        ... <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        ... <urn:task:Next> a yawl:Task .
        ... ''')
        >>> result = engine.apply_physics()
        >>> result.tick_number
        1
        >>> result.delta > 0
        True
        >>> result.converged
        False
        """
        start_time = time.perf_counter()
        self.tick_count += 1

        # 1. EXPORT (Materialize State)
        triples_before = len(list(self.store))
        current_state_str = self._dump_state()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as tmp_state:
            tmp_state.write(current_state_str)
            tmp_state_path = tmp_state.name

        try:
            # 2. REASON (Apply Force)
            # eye --nope --pass state.ttl physics.n3
            # --pass: Output the deductive closure (implications)
            # --nope: Don't output the proof trace
            cmd = ["eye", "--nope", "--pass", tmp_state_path, self.physics_file]

            logger.info(f"Tick {self.tick_count}: Invoking EYE Reasoner...")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            except FileNotFoundError as e:
                logger.error("EYE reasoner not found. Install via: apt-get install eye or brew install eye")
                raise FileNotFoundError(
                    "EYE reasoner not found in PATH. Install from: https://github.com/eyereasoner/eye"
                ) from e
            except subprocess.TimeoutExpired as e:
                logger.error("EYE reasoner timed out after 30 seconds")
                raise RuntimeError("EYE reasoner timed out. Graph may be too large or rules too complex.") from e

            # 3. INGEST (Evolution)
            # Load the *Deductions* back into the store.
            # Note: EYE outputs the FULL state + New Deductions.
            # PyOxigraph handles the merge (idempotent adds).
            self.store.load(input=result.stdout.encode("utf-8"), format=ox.RdfFormat.N3)

            triples_after = len(list(self.store))
            delta = triples_after - triples_before

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Tick {self.tick_count}: Physics applied in {duration_ms:.2f}ms, delta={delta} triples")

            return PhysicsResult(
                tick_number=self.tick_count,
                duration_ms=duration_ms,
                triples_before=triples_before,
                triples_after=triples_after,
                delta=delta,
            )

        finally:
            os.unlink(tmp_state_path)

    def inspect(self) -> dict[str, str]:
        """Query current task statuses (returning highest-priority status).

        Due to monotonic reasoning, tasks may accumulate multiple statuses
        (Active, Completed, Archived). This method returns the highest-priority
        status for each task.

        Priority order: Archived > Completed > Active (highest wins)

        Returns
        -------
        dict[str, str]
            Mapping of task IRI to highest-priority status string.

        Examples
        --------
        >>> engine = HybridEngine()
        >>> engine.load_data('''
        ... @prefix kgc: <https://kgc.org/ns/> .
        ... <urn:task:A> kgc:status "Active" .
        ... <urn:task:B> kgc:status "Completed" .
        ... ''')
        >>> statuses = engine.inspect()
        >>> statuses["urn:task:A"]
        'Active'
        >>> statuses["urn:task:B"]
        'Completed'
        """
        # Status priority (higher = more progressed in workflow)
        status_priority = {"Active": 1, "Completed": 2, "Archived": 3}

        query = """
            PREFIX kgc: <https://kgc.org/ns/>
            SELECT ?s ?status WHERE { ?s kgc:status ?status }
        """
        results: dict[str, str] = {}
        for solution in self.store.query(query):
            # PyOxigraph returns URIs as "<uri>" and literals as "\"value\""
            # Strip these wrappers for cleaner output
            subject_raw = str(solution["s"])
            status_raw = str(solution["status"])

            # Strip angle brackets from URIs
            subject = subject_raw.strip("<>")
            # Strip quotes from literals
            status = status_raw.strip('"')

            # Keep highest-priority status for each task
            current = results.get(subject)
            if current is None:
                results[subject] = status
            else:
                current_priority = status_priority.get(current, 0)
                new_priority = status_priority.get(status, 0)
                if new_priority > current_priority:
                    results[subject] = status

        logger.debug(f"Inspected {len(results)} task statuses")
        return results

    def run_to_completion(self, max_ticks: int = 100) -> list[PhysicsResult]:
        """Execute ticks until fixed point or maximum ticks reached.

        Parameters
        ----------
        max_ticks : int, optional
            Maximum number of ticks to execute, by default 100.

        Returns
        -------
        list[PhysicsResult]
            Results from each tick executed.

        Raises
        ------
        RuntimeError
            If maximum ticks reached without convergence.

        Examples
        --------
        >>> engine = HybridEngine()
        >>> engine.load_data('''
        ... @prefix kgc: <https://kgc.org/ns/> .
        ... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        ... <urn:task:Start> kgc:status "Completed" ;
        ...     yawl:flowsInto <urn:flow:1> .
        ... <urn:flow:1> yawl:nextElementRef <urn:task:Next> .
        ... <urn:task:Next> a yawl:Task .
        ... ''')
        >>> results = engine.run_to_completion(max_ticks=10)
        >>> len(results) > 0
        True
        >>> results[-1].converged
        True
        """
        results: list[PhysicsResult] = []

        logger.info(f"Starting run_to_completion (max_ticks={max_ticks})")

        for _ in range(max_ticks):
            result = self.apply_physics()
            results.append(result)

            if result.converged:
                logger.info(f"Converged at tick {result.tick_number} (delta=0, fixed point reached)")
                break
        else:
            logger.warning(f"Maximum ticks ({max_ticks}) reached without convergence. Last delta: {results[-1].delta}")
            raise RuntimeError(
                f"System did not converge after {max_ticks} ticks. "
                f"Consider increasing max_ticks or reviewing physics rules."
            )

        total_duration = sum(r.duration_ms for r in results)
        total_delta = sum(r.delta for r in results)
        logger.info(f"Completed {len(results)} ticks in {total_duration:.2f}ms, total_delta={total_delta} triples")

        return results
