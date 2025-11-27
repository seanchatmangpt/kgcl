"""FMEA Tests: Input and Topology Failures.

This module tests failure modes related to invalid or malformed input:
- FM-001: Empty Topology
- FM-002: Malformed RDF

References
----------
AIAG FMEA Handbook (4th Edition), Section 4.1 (Input Validation Failures)
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

from .ratings import Detection, Occurrence, Severity, calculate_rpn


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for FMEA testing.

    Returns
    -------
    HybridEngine
        Initialized engine instance
    """
    return HybridEngine()


class TestFM001EmptyTopology:
    """FM-001: Empty or missing topology data.

    Failure Mode
    ------------
    System receives empty or null topology input.

    Effect
    ------
    No tasks to process, potential null pointer errors.

    FMEA Ratings
    ------------
    - Severity: 5 (Moderate - system should handle gracefully)
    - Occurrence: 3 (Low - validation usually catches this)
    - Detection: 1 (Certain - easy to detect empty input)
    - RPN: 15 (Low risk)

    Mitigation
    ----------
    Graceful handling of empty input with zero-delta result.
    """

    rpn = calculate_rpn(Severity.MODERATE, Occurrence.LOW, Detection.CERTAIN)

    def test_empty_string_topology(self, engine: HybridEngine) -> None:
        """System handles empty topology string gracefully.

        An empty string should produce zero state changes (delta=0).
        """
        engine.load_data("")
        result = engine.apply_physics()
        assert result.delta == 0, "Empty topology should produce no changes"

    def test_whitespace_only_topology(self, engine: HybridEngine) -> None:
        """System handles whitespace-only topology.

        Whitespace (spaces, tabs, newlines) should be treated as empty.
        """
        engine.load_data("   \n\t\n   ")
        result = engine.apply_physics()
        assert result.delta == 0

    def test_comments_only_topology(self, engine: HybridEngine) -> None:
        """System handles comments-only topology.

        RDF comments without actual triples should produce no changes.
        """
        topology = """
        # This is a comment
        # No actual triples
        """
        engine.load_data(topology)
        result = engine.apply_physics()
        assert result.delta == 0


class TestFM002MalformedRDF:
    """FM-002: Malformed or invalid RDF syntax.

    Failure Mode
    ------------
    Invalid Turtle/N3 syntax in topology input.

    Effect
    ------
    Parser errors, potential crash or incomplete loading.

    FMEA Ratings
    ------------
    - Severity: 7 (High - blocks all processing)
    - Occurrence: 5 (Moderate - common user error)
    - Detection: 1 (Certain - parser reports errors immediately)
    - RPN: 35 (Medium risk)

    Mitigation
    ----------
    Parser error handling with clear error messages.
    """

    rpn = calculate_rpn(Severity.HIGH, Occurrence.MODERATE, Detection.CERTAIN)

    def test_missing_prefix_declaration(self, engine: HybridEngine) -> None:
        """Detect missing prefix declarations.

        Using undefined prefixes should raise an exception.
        """
        topology = """
        <urn:task:A> a yawl:Task .
        """
        with pytest.raises(Exception):
            engine.load_data(topology)

    def test_unclosed_uri(self, engine: HybridEngine) -> None:
        """Detect unclosed URI brackets.

        Malformed URIs should trigger parser errors.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        <urn:task:A a kgc:Task .
        """
        with pytest.raises(Exception):
            engine.load_data(topology)

    def test_invalid_predicate(self, engine: HybridEngine) -> None:
        """Detect invalid predicate syntax.

        Predicates must be URIs, not literals.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        <urn:task:A> "invalid predicate" <urn:task:B> .
        """
        with pytest.raises(Exception):
            engine.load_data(topology)
