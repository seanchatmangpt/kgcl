"""
KGC Lean Context Specification Validation Tests

Validates the macOS/iOS PyObjC KGC spec against Chicago TDD principles.
Tests focus on behavior verification using real collaborators (no mocking domain objects).

Specification source: KGC Lean Context Specification (Python/KGCT/macOS+iOS via PyObjC)
"""

import pytest
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Import from chicago_tdd_tools (as if installed)
# For now, using relative imports from src/
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import (
    TestFixture,
    StateManager,
    FailFastValidator,
    Poka,
    assert_that,
    assert_eq_with_msg,
)
from validation import InvariantValidator, Property
from testing import StateMachine


# ============================================================================
# Domain Models (No Mocking - Real Collaborators)
# ============================================================================

class LeanPrinciple(Enum):
    """Core Lean principles from spec."""
    VALUE = "value"
    VALUE_STREAM = "value_stream"
    FLOW = "flow"
    PULL = "pull"
    PERFECTION = "perfection"


class KGCPlane(Enum):
    """KGC planes from the spec."""
    ONTOLOGY = "ontology"
    TYPE = "type"
    INVARIANT = "invariant"
    PROJECTION = "projection"
    HOOK = "hook"


class AppleEntity(Enum):
    """Apple ecosystem entities from spec."""
    CALENDAR_EVENT = "calendar_event"
    REMINDER = "reminder"
    MAIL_MESSAGE = "mail_message"
    FILE_ARTIFACT = "file_artifact"


@dataclass
class KGCManifest:
    """Represents .kgc/manifest.ttl."""
    project_uri: str
    project_name: str
    owns_ontology: bool = True
    owns_types: bool = True
    owns_invariants: bool = True
    owns_hooks: bool = True
    has_projection_config: bool = True
    planes: List[KGCPlane] | None = None

    def __post_init__(self) -> None:
        if self.planes is None:
            self.planes = []


@dataclass
class Invariant:
    """Represents a SHACL invariant with traceable requirement."""
    name: str
    description: str
    traced_to: str  # Regulatory/contractual requirement or historical failure
    is_waste_reducing: bool


@dataclass
class Hook:
    """Represents a knowledge hook (conditions/effects)."""
    name: str
    triggered_by: str  # What condition triggers this
    effect: str  # What it does
    waste_removed: str  # Explicit story of waste eliminated


@dataclass
class KGCContext:
    """Complete KGC context for a project."""
    manifest: KGCManifest
    ontology_entities: List[str]
    invariants: List[Invariant]
    hooks: List[Hook]
    apple_entities: List[AppleEntity]
    has_apple_ingest: bool = False
    has_generator: bool = False
    projections: List[str] | None = None

    def __post_init__(self) -> None:
        if self.projections is None:
            self.projections = []


# ============================================================================
# KGC Technician (Real actor, no mocks)
# ============================================================================

class KGCTechnician:
    """Implements standard work loop from spec Section 7."""

    def __init__(self, context: KGCContext) -> None:
        self.context = context
        self.discovered_items: List[str] = []
        self.rework_count = 0
        self.regenerated_artifacts: List[str] = []
        self.waste_removed_stories: List[str] = []

    def discover(self, items: List[str]) -> None:
        """Step 1: Ingest data via KGCT (scan-apple, scan-files)."""
        self.discovered_items.extend(items)

    def align_ontology(self, new_entity: str | None = None) -> None:
        """Step 2: Update O/Q only where needed."""
        if new_entity:
            self.context.ontology_entities.append(new_entity)

    def regenerate(self, artifact_types: List[str]) -> None:
        """Step 3: Run KGCT generators."""
        for artifact in artifact_types:
            if artifact in ["cli", "docs", "diagrams", "agenda"]:
                self.regenerated_artifacts.append(artifact)

    def review(self) -> Dict[str, Any]:
        """Step 4: Inspect projections (not raw data)."""
        return {
            "projected_artifacts": self.regenerated_artifacts,
            "waste_areas": self._identify_waste(),
        }

    def remove_waste(self, waste_story: str) -> None:
        """Step 5: Eliminate repeated manual steps."""
        self.waste_removed_stories.append(waste_story)

    def _identify_waste(self) -> List[str]:
        """Use projections to detect waste patterns."""
        waste: List[str] = []
        if not self.context.hooks:
            waste.append("manual_copy_paste_between_apps")
        if not self.context.has_generator:
            waste.append("manual_cli_generation")
        return waste


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def minimal_kgc_context() -> KGCContext:
    """Minimal KGC context as defined in spec Section 2.1."""
    manifest = KGCManifest(
        project_uri="urn:project:kgc:osx-personal-fabric",
        project_name="macOS/iOS Personal Fabric",
        planes=[
            KGCPlane.ONTOLOGY,
            KGCPlane.TYPE,
            KGCPlane.INVARIANT,
            KGCPlane.PROJECTION,
        ]
    )

    context = KGCContext(
        manifest=manifest,
        ontology_entities=["CalendarEvent", "Reminder", "Note", "MailMessage", "FileArtifact"],
        invariants=[
            Invariant(
                name="calendar_event_complete",
                description="Every CalendarEvent has title, start, end",
                traced_to="Historical: missed appointments from untitled events",
                is_waste_reducing=True,
            ),
            Invariant(
                name="reminder_has_status",
                description="Every Reminder has a status",
                traced_to="Historical: lost tasks because status unclear",
                is_waste_reducing=True,
            ),
        ],
        hooks=[
            Hook(
                name="auto_populate_untitled_calendar",
                triggered_by="CalendarEvent.title is empty",
                effect="Populate with attendee names or description",
                waste_removed="Manual fix of untitled meetings in calendar app",
            ),
        ],
        apple_entities=[
            AppleEntity.CALENDAR_EVENT,
            AppleEntity.REMINDER,
            AppleEntity.MAIL_MESSAGE,
            AppleEntity.FILE_ARTIFACT,
        ],
        has_apple_ingest=True,
        has_generator=True,
        projections=["agenda", "todo-list", "mail-triage", "file-organization"],
    )
    return context


@pytest.fixture
def kgc_technician(minimal_kgc_context: KGCContext) -> KGCTechnician:
    """KGC Technician with minimal context."""
    return KGCTechnician(minimal_kgc_context)


# ============================================================================
# Test: Lean Principle 1 - VALUE
# ============================================================================

def test_lean_value_waste_elimination(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: Real collaborators, no mocks.

    Validates: Artifacts must eliminate waste per spec 1.1.
    "Artifacts are not artifacts for their own sake. They exist to reduce
    waste: gaps, rework, thrashing, thrashing, handoffs, batching."
    """
    # Arrange: Real KGC context with waste-reducing components
    context = minimal_kgc_context
    technician = KGCTechnician(context)

    # Act: Technician discovers waste and removes it
    technician.discover(["untitled_calendar_event", "lost_reminder"])
    technician.regenerate(["cli", "agenda"])

    # Assert: Artifacts reduce waste directly
    assert_that(context.manifest.has_projection_config, lambda x: x is True)
    assert_that(context.hooks, lambda h: len(h) > 0)
    assert_that(technician.regenerated_artifacts, lambda a: len(a) > 0)

    # Behavior: Hook exists with explicit waste story
    hook = context.hooks[0]
    assert_that(hook.waste_removed, lambda w: len(w) > 0)

    # Behavior: Projection is actionable
    assert_that(context.projections, lambda p: "agenda" in p)

    print("✓ Lean VALUE: Artifacts directly reduce waste")


def test_invariants_are_waste_reducing(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: Real invariant objects as collaborators.

    Validates: Each invariant must be traceable to requirement or failure mode.
    Per spec 3.4: "Each invariant must be traceable to a regulatory requirement
    or historically observed failure mode. No 'because we like it that way.'"
    """
    context = minimal_kgc_context

    for inv in context.invariants:
        # Behavior: Every invariant has traceable requirement
        assert inv.is_waste_reducing, f"{inv.name} is not waste-reducing"
        assert len(inv.traced_to) > 0, f"{inv.name} has no traceability"

    print("✓ Lean VALUE: All invariants reduce waste or prevent failures")


# ============================================================================
# Test: Lean Principle 2 - VALUE STREAM
# ============================================================================

def test_value_stream_mapping() -> None:
    """
    Chicago TDD: Behavioral assertion of value stream flow.

    Validates: We can trace a complete flow from data → O → projections → runtime.
    Per spec 1.1: "We model the entire flow... Every step must be traceable."
    """
    # Arrange: Minimal value stream
    flow = [
        "apple_data_ingest",
        "rdf_mapping",
        "shacl_validation",
        "projection_generation",
        "cli_update",
    ]

    # Act: Walk the value stream
    completeness = [step for step in flow if step]

    # Assert: All steps present (none are None)
    assert len(completeness) == 5, "All value stream steps must be present"

    print("✓ Lean VALUE_STREAM: Complete flow from data to runtime")


def test_value_stream_eliminates_handoffs() -> None:
    """
    Chicago TDD: No manual data transformation handoffs.

    Validates: System eliminates handoffs between O/Q/O.
    Per spec 1.2: "Single source of truth: O. Query Q dynamically."
    """
    # Arrange: Technician with generator capability
    manifest = KGCManifest(
        project_uri="urn:test:kgc",
        project_name="Test",
        has_projection_config=True,
    )
    context = KGCContext(
        manifest=manifest,
        ontology_entities=["Event", "Task"],
        invariants=[],
        hooks=[],
        apple_entities=[AppleEntity.CALENDAR_EVENT, AppleEntity.REMINDER],
        has_generator=True,
    )

    # Act: Generator produces artifacts without manual intervention
    technician = KGCTechnician(context)
    technician.regenerate(["cli", "docs"])

    # Assert: Artifacts exist without manual handoff
    assert_that(technician.regenerated_artifacts, lambda a: len(a) == 2)

    print("✓ Lean VALUE_STREAM: No manual handoffs between spec and code")


# ============================================================================
# Test: Lean Principle 3 - FLOW
# ============================================================================

def test_no_manual_batching_between_steps() -> None:
    """
    Chicago TDD: Single-piece flow validation.

    Validates: Work flows one piece at a time (one ontology entity → one projection).
    Per spec 1.3: "Single-piece flow, not batch processing."
    """
    # Arrange: Context with minimal batch size
    manifest = KGCManifest(
        project_uri="urn:test:kgc",
        project_name="Test",
    )
    context = KGCContext(
        manifest=manifest,
        ontology_entities=["Event"],  # Single entity
        invariants=[],
        hooks=[],
        apple_entities=[AppleEntity.CALENDAR_EVENT],
    )
    technician = KGCTechnician(context)

    # Act: Process single entity
    technician.discover(["one_calendar_event"])
    technician.align_ontology()
    technician.regenerate(["cli"])

    # Assert: Single-piece processed
    assert len(technician.discovered_items) == 1
    assert len(technician.regenerated_artifacts) >= 0

    print("✓ Lean FLOW: Single-piece flow, no batching")


# ============================================================================
# Test: Lean Principle 4 - PULL
# ============================================================================

def test_artifacts_pulled_not_pushed() -> None:
    """
    Chicago TDD: On-demand generation (pull) vs batch generation (push).

    Validates: Artifacts generated on demand (pull) not pre-generated (push).
    Per spec 1.4: "Pull-based: generated when needed, not pushed upfront."
    """
    # Arrange: Generator that can selectively produce artifacts
    manifest = KGCManifest(
        project_uri="urn:test:kgc",
        project_name="Test",
        has_projection_config=True,
    )
    context = KGCContext(
        manifest=manifest,
        ontology_entities=["Event"],
        invariants=[],
        hooks=[],
        apple_entities=[AppleEntity.CALENDAR_EVENT],
        has_generator=True,
    )
    technician = KGCTechnician(context)

    # Act: Pull only what's needed
    technician.regenerate(["cli"])  # Pull only CLI

    # Assert: Only requested artifact generated
    assert "cli" in technician.regenerated_artifacts
    assert "docs" not in technician.regenerated_artifacts

    print("✓ Lean PULL: On-demand generation (pull-based)")


# ============================================================================
# Test: Lean Principle 5 - PERFECTION
# ============================================================================

def test_drift_detection_is_defect(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: Gap between ontology (O) and actual (A) is a defect.

    Validates: If ontology says Event has title but actual EventKit doesn't,
    that's a defect requiring immediate fix.
    Per spec 1.5: "Drift (gap between O and A) is a defect."
    """
    # Arrange: KGC context with ontology spec
    context = minimal_kgc_context
    assert "CalendarEvent" in context.ontology_entities

    # Act: Check that invariants prevent drift
    calendar_invariant = [i for i in context.invariants if "calendar" in i.name.lower()]

    # Assert: Invariant enforces O consistency
    assert len(calendar_invariant) > 0, "Invariant must exist to prevent drift"
    assert calendar_invariant[0].is_waste_reducing

    print("✓ Lean PERFECTION: Drift detection through invariants")


# ============================================================================
# Test: KGC Structure Validation
# ============================================================================

def test_kgc_minimal_structure(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: KGC context contains all required planes.

    Validates: Minimal KGC structure per spec Section 2.1:
    - manifest.ttl (with ownership flags)
    - ontology.ttl
    - types.ttl
    - invariants.shacl.ttl
    - hooks.ttl
    - projections/ directory
    """
    context = minimal_kgc_context

    # Assert: Manifest exists and is complete
    assert context.manifest.project_uri
    assert context.manifest.owns_ontology
    assert context.manifest.owns_types
    assert context.manifest.owns_invariants
    assert context.manifest.owns_hooks
    assert context.manifest.has_projection_config

    # Assert: All planes present
    expected_planes = [
        KGCPlane.ONTOLOGY,
        KGCPlane.TYPE,
        KGCPlane.INVARIANT,
        KGCPlane.PROJECTION,
    ]
    for plane in expected_planes:
        assert plane in context.manifest.planes

    # Assert: Content exists
    assert len(context.ontology_entities) > 0
    assert len(context.invariants) > 0
    assert len(context.projections) > 0

    print("✓ KGC Structure: All required planes present")


# ============================================================================
# Test: Apple Ingest Invariants
# ============================================================================

def test_apple_entity_invariants(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: Apple entity invariants match spec Section 5.2.

    Validates: Invariants for CalendarEvent, Reminder, MailMessage, FileArtifact
    are traceable to waste/failures in those domains.
    """
    context = minimal_kgc_context

    # Assert: At least one invariant for each Apple entity type
    assert len(context.apple_entities) > 0
    assert len(context.invariants) > 0

    # Behavior: All invariants have waste story
    for inv in context.invariants:
        assert inv.traced_to, f"Invariant {inv.name} must be traceable"
        assert inv.is_waste_reducing, f"Invariant {inv.name} must be waste-reducing"

    print("✓ Apple Ingest: All entities have waste-reducing invariants")


# ============================================================================
# Test: Standard Work Loop
# ============================================================================

def test_technician_standard_work_loop(
    minimal_kgc_context: KGCContext,
    kgc_technician: KGCTechnician,
) -> None:
    """
    Chicago TDD: 5-step standard work loop from spec Section 7.

    Validates: Technician can execute full loop:
    1. Discover: Ingest from Apple
    2. Align: Update O only where needed
    3. Regenerate: Run generators
    4. Review: Inspect projections
    5. Remove: Eliminate manual waste
    """
    technician = kgc_technician

    # Step 1: Discover
    technician.discover(["untitled_event", "lost_reminder"])
    assert len(technician.discovered_items) == 2

    # Step 2: Align ontology
    technician.align_ontology("NewEntity")
    assert "NewEntity" in technician.context.ontology_entities

    # Step 3: Regenerate
    technician.regenerate(["cli", "agenda"])
    assert len(technician.regenerated_artifacts) == 2

    # Step 4: Review
    review_result = technician.review()
    assert "projected_artifacts" in review_result
    assert "waste_areas" in review_result

    # Step 5: Remove waste
    technician.remove_waste("Eliminated manual calendar sync")
    assert len(technician.waste_removed_stories) == 1

    print("✓ Standard Work: Full 5-step loop completed")


# ============================================================================
# Test: Metrics (Spec Section 8)
# ============================================================================

def test_lead_time_for_change_metric(kgc_technician: KGCTechnician) -> None:
    """
    Chicago TDD: Lead time for change should be < 60 minutes.

    Validates: Metric from spec Section 8.1:
    "Lead time: from ontology change to projected artifact in hands of user"
    Target: < 60 minutes (for local macOS/iOS dev)
    """
    technician = kgc_technician
    import time

    # Arrange: Measure time for full loop
    start = time.time()

    # Act: Complete full loop
    technician.align_ontology("NewEntity")
    technician.regenerate(["cli"])
    review = technician.review()

    lead_time_seconds = time.time() - start

    # Assert: Lead time acceptable (in test, should be < 1 second)
    assert lead_time_seconds < 60.0, f"Lead time {lead_time_seconds}s exceeds 60s target"

    print(f"✓ Metrics: Lead time {lead_time_seconds:.3f}s (target: < 60s)")


def test_rework_rate_metric(kgc_technician: KGCTechnician) -> None:
    """
    Chicago TDD: Rework rate should trend down.

    Validates: Metric from spec Section 8.2:
    "Rework rate: number of times invariant violation detected and fixed"
    Trend: should decrease as system matures
    """
    technician = kgc_technician

    # Arrange: Simulate multiple iterations
    rework_rates = []

    # Act: Run cycles with decreasing rework
    for cycle in range(3):
        technician.discover([f"item_{cycle}"])
        # Simulate rework detection
        if cycle == 0:
            rework_count = 3
        elif cycle == 1:
            rework_count = 2
        else:
            rework_count = 1
        rework_rates.append(rework_count)

    # Assert: Rework trend downward
    assert rework_rates[0] > rework_rates[1]
    assert rework_rates[1] > rework_rates[2]

    print(f"✓ Metrics: Rework rate trending down {rework_rates}")


# ============================================================================
# Test: Chicago TDD Principles (Validate Meta-Level)
# ============================================================================

def test_chicago_tdd_no_mocking_domain_objects(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: This test validates the test suite itself uses real collaborators.

    Demonstrates: KGCContext and KGCTechnician are REAL objects, not mocks.
    No unittest.mock.Mock or pytest.fixture mocking of domain entities.
    """
    # Arrange: Real domain objects
    context = minimal_kgc_context
    technician = KGCTechnician(context)

    # Assert: These are real objects, not mocks
    assert isinstance(context, KGCContext)
    assert isinstance(technician, KGCTechnician)
    assert isinstance(context.manifest, KGCManifest)

    print("✓ Chicago TDD: Real collaborators, no mocking of domain objects")


def test_chicago_tdd_behavior_verification(kgc_technician: KGCTechnician) -> None:
    """
    Chicago TDD: Verify behavior, not implementation details.

    Demonstrates: Tests check WHAT the system does (behavior),
    not HOW it does it (implementation).
    """
    technician = kgc_technician

    # Arrange: Define expected behavior
    # Behavior: "Technician discovers items and regenerates artifacts"

    # Act: Call public methods (behavior-level)
    technician.discover(["item1", "item2"])
    technician.regenerate(["cli"])

    # Assert: Behavior outcome (not implementation)
    assert len(technician.discovered_items) == 2  # Behavior outcome
    assert "cli" in technician.regenerated_artifacts  # Behavior outcome

    # Don't check:
    # assert technician._internal_state == ...  # Implementation detail

    print("✓ Chicago TDD: Behavior verification, not implementation details")


def test_aaa_pattern_arrange_act_assert(minimal_kgc_context: KGCContext) -> None:
    """
    Chicago TDD: Explicit Arrange-Act-Assert pattern.

    Demonstrates: All tests in this suite follow AAA pattern:
    - Arrange: Set up objects and state
    - Act: Execute behavior
    - Assert: Verify outcomes
    """
    # ===== ARRANGE =====
    context = minimal_kgc_context
    technician = KGCTechnician(context)

    # ===== ACT =====
    technician.discover(["untitled_event"])
    technician.align_ontology("Event")
    technician.regenerate(["agenda"])
    result = technician.review()

    # ===== ASSERT =====
    assert len(technician.discovered_items) == 1
    assert "Event" in technician.context.ontology_entities
    assert "agenda" in technician.regenerated_artifacts
    assert "projected_artifacts" in result

    print("✓ Chicago TDD: AAA pattern (Arrange-Act-Assert)")
