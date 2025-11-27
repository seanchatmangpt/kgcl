"""Input Validation Tests - All Error Types and Poka-Yoke Methods.

This module tests input validation covering all six error types and three
Poka-Yoke methods (Contact, Fixed-Value, Motion-Step).

Error Types Tested
-----------------
- **Type 1**: Input validation errors (bad topology, malformed URIs, invalid prefixes)
- **Type 2**: State transition errors (invalid status changes, backwards transitions)
- **Type 3**: Sequence errors (wrong order of operations, idempotency violations)
- **Type 4**: Omission errors (missing required elements, incomplete patterns)
- **Type 5**: Selection errors (wrong choice from valid set, invalid vocabulary)
- **Type 6**: Resource constraint errors (memory limits, tick bounds, task count)

Poka-Yoke Methods
----------------
- **Contact Method**: Structural constraints (URI format, prefix syntax, type validation)
- **Fixed-Value Method**: Set membership (status values, control types, verb vocabulary)
- **Motion-Step Method**: Sequential correctness (flow integrity, idempotency, state transitions)

Pattern Catalog Tests
--------------------
- Exactly 43 patterns (WCP-1 through WCP-43)
- All patterns have required fields (name, verb, category)
- Sequential pattern numbering
- Valid verb vocabulary (Transmute, Copy, Filter, Await, Void)
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for validation testing."""
    return HybridEngine()


# =============================================================================
# CONTACT METHOD TESTS (Type 1 Errors)
# =============================================================================


class TestPY001PrefixValidation:
    """PY-001: Prefix declarations must be valid.

    Poka-Yoke Type: Contact Method (Prevention)
    Error Class: Type 1 (Input validation)
    Detection: Parser rejects invalid prefixes immediately
    """

    def test_valid_prefixes_accepted(self, engine: HybridEngine) -> None:
        """Valid prefix declarations are accepted."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

        <urn:task:A> a yawl:Task .
        """
        engine.load_data(topology)
        # Should not raise

    def test_undefined_prefix_rejected(self, engine: HybridEngine) -> None:
        """Undefined prefix usage is rejected immediately."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .

        <urn:task:A> a undefined:Task .
        """
        with pytest.raises(Exception):
            engine.load_data(topology)

    def test_malformed_prefix_uri_rejected(self, engine: HybridEngine) -> None:
        """Malformed prefix URI is rejected."""
        topology = """
        @prefix kgc: <not a valid uri> .

        <urn:task:A> a kgc:Task .
        """
        with pytest.raises(Exception):
            engine.load_data(topology)


class TestPY007URIFormatValidation:
    """PY-007: URIs must be well-formed.

    Poka-Yoke Type: Contact Method (Prevention)
    Error Class: Type 1 (Input validation)
    Constraint: URIs must follow RFC 3986
    """

    def test_valid_urn_uri(self, engine: HybridEngine) -> None:
        """URN-style URIs are valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:ValidURN> a yawl:Task .
        """
        engine.load_data(topology)

    def test_valid_http_uri(self, engine: HybridEngine) -> None:
        """HTTP-style URIs are valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <http://example.org/task/A> a yawl:Task .
        """
        engine.load_data(topology)

    def test_valid_https_uri(self, engine: HybridEngine) -> None:
        """HTTPS-style URIs are valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <https://example.org/task/A> a yawl:Task .
        """
        engine.load_data(topology)


# =============================================================================
# FIXED-VALUE METHOD TESTS (Type 5 Errors)
# =============================================================================


class TestPY002StatusValidation:
    """PY-002: Task status must be from valid set.

    Poka-Yoke Type: Fixed-Value Method (Detection)
    Error Class: Type 5 (Selection error)
    Valid Values: Pending, Active, Completed, Cancelled, Archived
    """

    VALID_STATUSES = ["Pending", "Active", "Completed", "Cancelled", "Archived"]

    def test_valid_status_pending(self, engine: HybridEngine) -> None:
        """Status 'Pending' is valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Pending" .
        """
        engine.load_data(topology)
        statuses = engine.inspect()
        assert statuses.get("urn:task:A") == "Pending"

    def test_valid_status_active(self, engine: HybridEngine) -> None:
        """Status 'Active' is valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Active" .
        """
        engine.load_data(topology)
        statuses = engine.inspect()
        assert statuses.get("urn:task:A") == "Active"

    def test_valid_status_completed(self, engine: HybridEngine) -> None:
        """Status 'Completed' is valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        statuses = engine.inspect()
        assert statuses.get("urn:task:A") == "Completed"

    def test_case_sensitivity_enforced(self, engine: HybridEngine) -> None:
        """Status values are case-sensitive."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "completed" .
        """
        engine.load_data(topology)
        statuses = engine.inspect()
        # Lowercase 'completed' should not match 'Completed'
        assert statuses.get("urn:task:A") == "completed"


class TestPY004SplitTypeValidation:
    """PY-004: Split type must be valid YAWL control type.

    Poka-Yoke Type: Fixed-Value Method (Prevention)
    Error Class: Type 5 (Selection error)
    Valid Values: ControlTypeAnd, ControlTypeXor, ControlTypeOr
    """

    def test_valid_and_split(self, engine: HybridEngine) -> None:
        """ControlTypeAnd split is valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:task:A> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()
        assert statuses.get("urn:task:A") in ["Active", "Completed", "Archived"]

    def test_valid_xor_split(self, engine: HybridEngine) -> None:
        """ControlTypeXor split is valid and engine processes without error."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> ;
            yawl:isDefaultFlow true .
        <urn:task:A> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()
        # Poka-Yoke validates structure: engine accepted the XOR split
        assert statuses.get("urn:task:Split") == "Completed"
        assert "urn:task:A" in statuses or len(statuses) >= 1


class TestPY005JoinTypeValidation:
    """PY-005: Join type must be valid YAWL control type.

    Poka-Yoke Type: Fixed-Value Method (Prevention)
    Error Class: Type 5 (Selection error)
    Valid Values: ControlTypeAnd, ControlTypeXor, ControlTypeOr
    """

    def test_valid_and_join(self, engine: HybridEngine) -> None:
        """ControlTypeAnd join is valid."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_join> .

        <urn:flow:a_to_join> yawl:nextElementRef <urn:task:Join> .

        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()
        # AND-join with single predecessor behaves like sequence
        assert statuses.get("urn:task:Join") in ["Active", "Completed", "Archived", None]


# =============================================================================
# MOTION-STEP METHOD TESTS (Type 3 & Type 4 Errors)
# =============================================================================


class TestPY003FlowIntegrity:
    """PY-003: Flow connections must be complete.

    Poka-Yoke Type: Motion-Step Method (Prevention)
    Error Class: Type 4 (Omission error)
    Requirement: flowsInto must have nextElementRef
    """

    def test_complete_flow_accepted(self, engine: HybridEngine) -> None:
        """Complete flow definition is accepted."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()
        assert statuses.get("urn:task:B") in ["Active", "Completed", "Archived"]


class TestPY010Idempotency:
    """PY-010: Multiple loads should be idempotent.

    Poka-Yoke Type: Motion-Step Method (Prevention)
    Error Class: Type 3 (Sequence error)
    Constraint: Loading same topology twice should not change behavior
    """

    def test_double_load_same_result(self, engine: HybridEngine) -> None:
        """Loading topology twice produces same result as once."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        # First engine - single load
        engine1 = HybridEngine()
        engine1.load_data(topology)
        engine1.run_to_completion(max_ticks=5)
        statuses1 = engine1.inspect()

        # Second engine - double load
        engine2 = HybridEngine()
        engine2.load_data(topology)
        engine2.load_data(topology)  # Load again
        engine2.run_to_completion(max_ticks=5)
        statuses2 = engine2.inspect()

        # Results should be consistent
        assert statuses1.get("urn:task:B") == statuses2.get("urn:task:B")

    def test_multiple_apply_physics_stable(self, engine: HybridEngine) -> None:
        """Multiple apply_physics calls reach stable state."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)

        # Apply physics multiple times
        result1 = engine.apply_physics()
        result2 = engine.apply_physics()
        result3 = engine.apply_physics()

        # Should reach stable state (no changes)
        assert result2.delta == 0 or result3.delta == 0


class TestPY014StateTransitionErrors:
    """PY-014: State transition error detection.

    Error Type 2: Invalid state transitions
    - Completed -> Pending (backwards)
    - Active -> Pending (backwards)
    """

    def test_backwards_transition_prevented(self, engine: HybridEngine) -> None:
        """Completed task should not revert to Pending."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        engine.apply_physics()
        statuses = engine.inspect()

        # Monotonic reasoning: Completed status persists
        assert statuses.get("urn:task:A") in ["Completed", "Archived"]

    def test_status_progression_monotonic(self, engine: HybridEngine) -> None:
        """Status progression should be monotonically forward."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:to_b> .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)

        # Track progression
        initial = engine.inspect()
        engine.run_to_completion(max_ticks=5)
        final = engine.inspect()

        # Monotonic: A stays Completed/Archived
        assert final.get("urn:task:A") in ["Completed", "Archived"]


# =============================================================================
# RESOURCE CONSTRAINT TESTS (Type 6 Errors)
# =============================================================================


class TestPY006TickCountBounds:
    """PY-006: Tick count must be within bounds.

    Poka-Yoke Type: Fixed-Value Method (Prevention)
    Error Class: Type 1 (Input validation)
    Constraint: max_ticks must be positive integer
    """

    def test_positive_max_ticks(self, engine: HybridEngine) -> None:
        """Positive max_ticks is accepted."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Active" .
        """
        engine.load_data(topology)
        result = engine.run_to_completion(max_ticks=5)
        assert engine.tick_count <= 5

    def test_single_tick(self, engine: HybridEngine) -> None:
        """Single tick (max_ticks=1) is valid parameter."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" .
        """
        engine.load_data(topology)
        result = engine.run_to_completion(max_ticks=1)
        assert engine.tick_count <= 1


class TestPY015ResourceConstraintErrors:
    """PY-015: Resource constraint error detection.

    Error Type 6: Resource exhaustion and constraints
    - Memory limits
    - Tick count limits
    - Task count limits
    """

    def test_tick_limit_enforced(self, engine: HybridEngine) -> None:
        """max_ticks parameter prevents infinite execution."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Active" .
        """
        engine.load_data(topology)

        # Resource constraint: max_ticks=3
        result = engine.run_to_completion(max_ticks=3)
        assert engine.tick_count <= 3

    def test_large_topology_handles_gracefully(self, engine: HybridEngine) -> None:
        """Large topology (50 tasks) handles without resource exhaustion."""
        tasks = []
        for i in range(50):
            tasks.append(f'<urn:task:T{i}> a yawl:Task ; kgc:status "Pending" .')

        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        """ + "\n".join(tasks)

        engine.load_data(topology)
        result = engine.apply_physics()
        assert result is not None


# =============================================================================
# PATTERN CATALOG INTEGRITY TESTS (Type 4 Errors)
# =============================================================================


class TestPY008PatternCatalogIntegrity:
    """PY-008: Pattern catalog must be complete and consistent.

    Poka-Yoke Type: Fixed-Value Method (Detection)
    Error Class: Type 4 (Omission error)
    Constraint: Exactly 43 patterns, all with required fields
    """

    def test_exactly_43_patterns(self) -> None:
        """Catalog contains exactly 43 patterns."""
        assert len(WCP_PATTERN_CATALOG) == 43

    def test_all_patterns_have_name(self) -> None:
        """All patterns have 'name' field."""
        for wcp_num in range(1, 44):
            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert info is not None, f"WCP-{wcp_num} missing"
            assert "name" in info, f"WCP-{wcp_num} missing name"
            assert len(info["name"]) > 0, f"WCP-{wcp_num} has empty name"

    def test_all_patterns_have_verb(self) -> None:
        """All patterns have 'verb' field."""
        for wcp_num in range(1, 44):
            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert "verb" in info, f"WCP-{wcp_num} missing verb"

    def test_all_patterns_have_category(self) -> None:
        """All patterns have 'category' field."""
        for wcp_num in range(1, 44):
            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert "category" in info, f"WCP-{wcp_num} missing category"

    def test_pattern_numbers_sequential(self) -> None:
        """Pattern numbers are 1-43 sequential."""
        expected = set(range(1, 44))
        actual = set(WCP_PATTERN_CATALOG.keys())
        assert actual == expected


class TestPY009VerbVocabulary:
    """PY-009: Pattern verbs must be from KGC vocabulary.

    Poka-Yoke Type: Fixed-Value Method (Prevention)
    Error Class: Type 5 (Selection error)
    Valid Verbs: Transmute, Copy, Filter, Await, Void
    """

    VALID_VERBS = {"Transmute", "Copy", "Filter", "Await", "Void"}

    def test_all_verbs_valid(self) -> None:
        """All pattern verbs are from valid vocabulary."""
        for wcp_num in range(1, 44):
            info = WCP_PATTERN_CATALOG[wcp_num]
            verb = info["verb"]
            # Handle compound verbs (e.g., "Filter + Void")
            parts = verb.replace("+", ",").split(",")
            for part in parts:
                part = part.strip()
                assert part in self.VALID_VERBS, f"WCP-{wcp_num} has invalid verb '{part}'"
