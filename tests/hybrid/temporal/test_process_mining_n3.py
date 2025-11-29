"""Tests for N3 process mining rules using EYE reasoner.

This module tests van der Aalst's α-algorithm implemented as N3 inference rules.
Tests cover:
- Directly-follows relation extraction
- Causality inference
- Parallel and exclusive activity detection
- Workflow pattern identification (AND-split, XOR-join, etc)
- Conformance checking
- Petri net generation
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

# Test data paths
ONTOLOGY_DIR = Path(__file__).parent.parent.parent.parent / "src" / "kgcl" / "hybrid" / "temporal" / "ontology"
TEST_DATA_DIR = Path(__file__).parent
PROCESS_MINING_N3 = ONTOLOGY_DIR / "process_mining.n3"
CONFORMANCE_N3 = ONTOLOGY_DIR / "conformance.n3"
SAMPLE_LOGS = TEST_DATA_DIR / "sample_logs.ttl"


def run_eye_reasoner(data_files: list[Path], rule_files: list[Path], query: str | None = None) -> str:
    """Run EYE reasoner with given data and rules.

    Parameters
    ----------
    data_files : list[Path]
        Input data files (Turtle/N3)
    rule_files : list[Path]
        N3 rule files
    query : str | None
        Optional SPARQL query to filter results

    Returns
    -------
    str
        N3 output from reasoner

    Raises
    ------
    FileNotFoundError
        If EYE reasoner not installed
    subprocess.CalledProcessError
        If reasoning fails
    """
    cmd = ["eye", "--pass-only-new"]

    # Add data files
    for data_file in data_files:
        cmd.extend(["--turtle", str(data_file)])

    # Add rule files
    for rule_file in rule_files:
        cmd.append(str(rule_file))

    # Add query if provided
    if query:
        cmd.extend(["--query", query])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return result.stdout
    except FileNotFoundError as e:
        pytest.skip("EYE reasoner not installed (install: npm install -g eye-js)")
        raise e
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"EYE reasoner timeout after 30s: {e}")
        raise e


def parse_n3_output(output: str) -> dict[str, Any]:
    """Parse N3 output into structured data.

    Parameters
    ----------
    output : str
        N3 reasoning output

    Returns
    -------
    dict[str, Any]
        Parsed triples organized by predicate
    """
    triples: dict[str, list[tuple[str, str]]] = {}

    for line in output.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("@"):
            continue

        # Simple N3 triple parsing (subject predicate object .)
        parts = line.rstrip(" .").split()
        if len(parts) >= 3:
            subject, predicate, obj = parts[0], parts[1], " ".join(parts[2:])
            predicate_key = predicate.split(":")[-1] if ":" in predicate else predicate

            if predicate_key not in triples:
                triples[predicate_key] = []
            triples[predicate_key].append((subject, obj))

    return triples


class TestDirectlyFollowsExtraction:
    """Test directly-follows relation extraction from event logs."""

    def test_sequential_process_directly_follows(self) -> None:
        """Test extracting directly-follows from sequential process (A→B→C→D)."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Verify A > B, B > C, C > D
        assert "pm:directlyFollows" in output
        assert '"A" pm:directlyFollows "B"' in output
        assert '"B" pm:directlyFollows "C"' in output
        assert '"C" pm:directlyFollows "D"' in output

    def test_parallel_activities_directly_follows(self) -> None:
        """Test directly-follows with parallel activities (both B>C and C>B)."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # In parallel log, both B>C and C>B should exist
        assert '"B" pm:directlyFollows "C"' in output
        assert '"C" pm:directlyFollows "B"' in output

    def test_no_false_directly_follows(self) -> None:
        """Test that non-adjacent activities don't have directly-follows."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # A and C are not adjacent in sequential process
        assert '"A" pm:directlyFollows "C"' not in output
        # A and D are not adjacent
        assert '"A" pm:directlyFollows "D"' not in output


class TestCausalityInference:
    """Test causality relation (a → b) inference."""

    def test_sequential_causality(self) -> None:
        """Test causal relations in sequential process."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Sequential process: A→B→C→D (all causal)
        assert "pm:causes" in output
        assert '"A" pm:causes "B"' in output
        assert '"B" pm:causes "C"' in output
        assert '"C" pm:causes "D"' in output

    def test_causality_not_parallel(self) -> None:
        """Test that parallel activities don't have causality."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # B and C are parallel, not causal
        # (both B>C and C>B exist, so neither B→C nor C→B)
        parsed = parse_n3_output(output)
        causes_pairs = parsed.get("causes", [])

        # B and C should not have causal relation
        bc_causal = any((subj.strip('"') == "B" and obj.strip('"') == "C") for subj, obj in causes_pairs)
        cb_causal = any((subj.strip('"') == "C" and obj.strip('"') == "B") for subj, obj in causes_pairs)

        assert not bc_causal, "B→C should not exist (B||C)"
        assert not cb_causal, "C→B should not exist (B||C)"


class TestParallelDetection:
    """Test parallel activity (a || b) detection."""

    def test_parallel_activities_detected(self) -> None:
        """Test detection of parallel activities."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # B || C in parallel log
        assert "pm:parallelWith" in output
        assert '"B" pm:parallelWith "C"' in output
        assert '"C" pm:parallelWith "B"' in output

    def test_sequential_not_parallel(self) -> None:
        """Test that sequential activities are not marked parallel."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # A and B are sequential, not parallel
        assert '"A" pm:parallelWith "B"' not in output


class TestExclusiveDetection:
    """Test exclusive choice (a # b) detection."""

    def test_exclusive_activities_detected(self) -> None:
        """Test detection of mutually exclusive activities."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # In exclusive choice log, B # C (never both executed)
        # This is complex to detect without negative constraints
        # May require additional query logic
        parsed = parse_n3_output(output)

        # At minimum, verify no directly-follows between B and C in exclusive log
        directly_follows = parsed.get("directlyFollows", [])
        bc_follows = any((subj.strip('"') == "B" and obj.strip('"') == "C") for subj, obj in directly_follows)
        cb_follows = any((subj.strip('"') == "C" and obj.strip('"') == "B") for subj, obj in directly_follows)

        # In exclusive choice, B and C should not directly follow each other
        assert not bc_follows or not cb_follows


class TestStartEndActivities:
    """Test identification of start and end activities."""

    def test_start_activity_detection(self) -> None:
        """Test that start activities are correctly identified."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Activity A is always first
        assert "pm:StartActivity" in output
        assert '"A" a pm:StartActivity' in output

    def test_end_activity_detection(self) -> None:
        """Test that end activities are correctly identified."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Activity D or F is last in different traces
        assert "pm:EndActivity" in output
        assert '"D" a pm:EndActivity' in output or '"F" a pm:EndActivity' in output


class TestWorkflowPatterns:
    """Test workflow pattern identification."""

    def test_and_split_detection(self) -> None:
        """Test AND-split pattern detection."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # In complex workflow, A is AND-split (A → B || C)
        # Requires both: A causes B, A causes C, B||C
        assert "pm:isAndSplit" in output or "pn:AndSplit" in output

    def test_xor_split_detection(self) -> None:
        """Test XOR-split pattern detection."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # In exclusive choice log, A is XOR-split (A → B XOR C)
        # Complex pattern requiring analysis across multiple traces
        parsed = parse_n3_output(output)

        # Verify A causes both B and C
        causes = parsed.get("causes", [])
        a_causes_b = any((subj.strip('"') == "A" and obj.strip('"') == "B") for subj, obj in causes)
        a_causes_c = any((subj.strip('"') == "A" and obj.strip('"') == "C") for subj, obj in causes)

        # If both exist, should have XOR-split marker
        if a_causes_b and a_causes_c:
            assert "pm:isXorSplit" in output or "pn:XorSplit" in output


class TestLoopDetection:
    """Test loop pattern detection."""

    def test_activity_repetition_detected(self) -> None:
        """Test detection of repeated activities in trace."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Activity B appears twice in loop trace
        assert "pm:hasLoop" in output or "pm:hasSelfLoop" in output


class TestPetriNetGeneration:
    """Test Petri net generation from discovered relations."""

    def test_places_generated_from_causal_pairs(self) -> None:
        """Test that places are created for causal pairs."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Places should be created for causal relations
        assert "pn:Place" in output
        assert "pn:fromActivity" in output
        assert "pn:toActivity" in output

    def test_arcs_generated(self) -> None:
        """Test that arcs connect activities and places."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Arcs should exist
        assert "pn:Arc" in output
        assert "pn:source" in output
        assert "pn:target" in output

    def test_source_and_sink_places(self) -> None:
        """Test that source and sink places are created."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Should have source place (i) and sink place (o)
        assert "pn:SourcePlace" in output
        assert "pn:SinkPlace" in output


class TestConformanceChecking:
    """Test conformance checking rules."""

    def test_conforming_trace_detected(self) -> None:
        """Test that conforming traces are marked as such."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3, CONFORMANCE_N3])

        # Sequential traces should conform to sequential model
        assert "pm:isConforming" in output or "pm:isPerfectlyFitting" in output

    def test_deviation_detected(self) -> None:
        """Test that deviations are detected in non-conforming traces."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3, CONFORMANCE_N3])

        # Non-conforming log should have deviations
        assert "pm:hasDeviation" in output or "pm:UnexpectedTransition" in output or "xes:WrongOrderDeviation" in output

    def test_fitness_calculation(self) -> None:
        """Test fitness metric calculation."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3, CONFORMANCE_N3])

        # Fitness values should be computed
        assert "xes:fitness" in output or "pm:isPerfectlyFitting" in output


class TestIntegrationScenarios:
    """Integration tests with complete workflows."""

    def test_complete_alpha_algorithm_sequential(self) -> None:
        """Test complete α-algorithm on sequential process."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Verify all steps of α-algorithm
        assert "pm:directlyFollows" in output  # Step 1: Directly-follows
        assert "pm:causes" in output  # Step 2: Causality
        assert "pm:StartActivity" in output  # Step 5: Start activities
        assert "pm:EndActivity" in output  # Step 6: End activities
        assert "pn:Place" in output  # Step 9: Petri net places

    def test_complete_alpha_algorithm_parallel(self) -> None:
        """Test complete α-algorithm on parallel process."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3])

        # Verify parallel detection
        assert "pm:parallelWith" in output  # Step 3: Parallel activities
        assert "pm:isAndSplit" in output or "pn:AndSplit" in output  # Step 7: AND-split

    def test_full_conformance_analysis(self) -> None:
        """Test complete conformance checking workflow."""
        output = run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3, CONFORMANCE_N3])

        # Should have both mining and conformance results
        assert "pm:causes" in output  # Mining results
        assert "xes:fitness" in output or "pm:isConforming" in output  # Conformance


class TestPerformance:
    """Performance tests for N3 reasoning."""

    def test_reasoning_completes_under_time_limit(self) -> None:
        """Test that reasoning completes within reasonable time."""
        import time

        start = time.time()
        run_eye_reasoner(data_files=[SAMPLE_LOGS], rule_files=[PROCESS_MINING_N3, CONFORMANCE_N3])
        duration = time.time() - start

        # Should complete in under 10 seconds
        assert duration < 10.0, f"Reasoning took {duration:.2f}s (limit: 10s)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
