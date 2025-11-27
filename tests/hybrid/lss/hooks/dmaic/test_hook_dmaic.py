"""Tests for Knowledge Hooks DMAIC Phases.

This module tests the DMAIC phase definitions and dataclasses for
Knowledge Hook quality improvement.
"""

from __future__ import annotations

import pytest

from tests.hybrid.lss.hooks.dmaic.phases import (
    HookAnalyzePhase,
    HookControlPhase,
    HookDefinePhase,
    HookDMAICCycle,
    HookDMAICPhase,
    HookImprovePhase,
    HookMeasurePhase,
)


class TestHookDMAICPhase:
    """Tests for HookDMAICPhase enum."""

    def test_all_phases_defined(self) -> None:
        """Test that all 5 DMAIC phases are defined.

        Verifies:
        - All 5 phases exist
        - Phase values match expected strings
        - Enum is complete
        """
        # Arrange
        expected_phases = ["define", "measure", "analyze", "improve", "control"]

        # Act
        actual_phases = [p.value for p in HookDMAICPhase]

        # Assert
        assert actual_phases == expected_phases
        assert len(HookDMAICPhase) == 5

    def test_phase_string_conversion(self) -> None:
        """Test that phases can be created from strings.

        Verifies:
        - String to enum conversion works
        - Case-sensitive matching
        """
        # Act & Assert
        assert HookDMAICPhase("define") == HookDMAICPhase.DEFINE
        assert HookDMAICPhase("measure") == HookDMAICPhase.MEASURE
        assert HookDMAICPhase("analyze") == HookDMAICPhase.ANALYZE
        assert HookDMAICPhase("improve") == HookDMAICPhase.IMPROVE
        assert HookDMAICPhase("control") == HookDMAICPhase.CONTROL


class TestHookDefinePhase:
    """Tests for HookDefinePhase dataclass."""

    def test_create_valid_define_phase(self) -> None:
        """Test creating a valid define phase.

        Verifies:
        - All required fields populated
        - Frozen dataclass behavior
        """
        # Arrange & Act
        define = HookDefinePhase(
            problem_statement="Hooks failing validation",
            hook_scope=["validate-person", "validate-org"],
            success_criteria={"success_rate": 0.95, "p99_latency_ms": 50.0},
            stakeholders=["data-team", "api-team"],
        )

        # Assert
        assert define.problem_statement == "Hooks failing validation"
        assert len(define.hook_scope) == 2
        assert define.success_criteria["success_rate"] == 0.95
        assert len(define.stakeholders) == 2

    def test_empty_problem_statement_raises(self) -> None:
        """Test that empty problem statement raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="problem_statement cannot be empty"):
            HookDefinePhase(
                problem_statement="", hook_scope=["hook1"], success_criteria={"metric": 1.0}, stakeholders=["team"]
            )

    def test_empty_hook_scope_raises(self) -> None:
        """Test that empty hook scope raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="hook_scope must contain at least one hook ID"):
            HookDefinePhase(
                problem_statement="Problem", hook_scope=[], success_criteria={"metric": 1.0}, stakeholders=["team"]
            )

    def test_empty_success_criteria_raises(self) -> None:
        """Test that empty success criteria raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="success_criteria must contain at least one metric"):
            HookDefinePhase(
                problem_statement="Problem", hook_scope=["hook1"], success_criteria={}, stakeholders=["team"]
            )


class TestHookMeasurePhase:
    """Tests for HookMeasurePhase dataclass."""

    def test_create_valid_measure_phase(self) -> None:
        """Test creating a valid measure phase."""
        # Arrange & Act
        measure = HookMeasurePhase(
            baseline_metrics={"success_rate": 0.70, "avg_latency_ms": 45.2, "p99_latency_ms": 120.0},
            measurement_system="HookReceipt analysis from production",
            data_collection_plan="Collect receipts every tick, aggregate hourly",
        )

        # Assert
        assert measure.baseline_metrics["success_rate"] == 0.70
        assert "HookReceipt" in measure.measurement_system
        assert "hourly" in measure.data_collection_plan

    def test_empty_baseline_metrics_raises(self) -> None:
        """Test that empty baseline metrics raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="baseline_metrics must contain at least one metric"):
            HookMeasurePhase(baseline_metrics={}, measurement_system="System", data_collection_plan="Plan")

    def test_empty_measurement_system_raises(self) -> None:
        """Test that empty measurement system raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="measurement_system cannot be empty"):
            HookMeasurePhase(baseline_metrics={"m": 1.0}, measurement_system="", data_collection_plan="Plan")

    def test_empty_data_collection_plan_raises(self) -> None:
        """Test that empty data collection plan raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="data_collection_plan cannot be empty"):
            HookMeasurePhase(baseline_metrics={"m": 1.0}, measurement_system="System", data_collection_plan="")


class TestHookAnalyzePhase:
    """Tests for HookAnalyzePhase dataclass."""

    def test_create_valid_analyze_phase(self) -> None:
        """Test creating a valid analyze phase."""
        # Arrange & Act
        analyze = HookAnalyzePhase(
            root_causes=["Missing SPARQL escaping", "Timeout too short", "Race condition"],
            pareto_analysis={"Missing escaping": 45, "Timeout": 30, "Race condition": 15, "Other": 10},
            fishbone_categories={
                "People": ["Unclear SPARQL docs"],
                "Process": ["No validation on hook registration"],
                "Technology": ["SPARQL parser limitations"],
                "Environment": ["Heavy production load"],
            },
        )

        # Assert
        assert len(analyze.root_causes) == 3
        assert analyze.pareto_analysis["Missing escaping"] == 45
        assert "People" in analyze.fishbone_categories
        assert len(analyze.fishbone_categories["Technology"]) == 1

    def test_top_cause_property(self) -> None:
        """Test top_cause property returns highest frequency cause."""
        # Arrange
        analyze = HookAnalyzePhase(
            root_causes=["A", "B", "C"],
            pareto_analysis={"A": 100, "B": 50, "C": 25},
            fishbone_categories={"Tech": ["A"]},
        )

        # Act & Assert
        assert analyze.top_cause == "A"

    def test_empty_root_causes_raises(self) -> None:
        """Test that empty root causes raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="root_causes must contain at least one cause"):
            HookAnalyzePhase(root_causes=[], pareto_analysis={"c": 1}, fishbone_categories={"cat": ["x"]})

    def test_empty_pareto_analysis_raises(self) -> None:
        """Test that empty pareto analysis raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="pareto_analysis must contain at least one entry"):
            HookAnalyzePhase(root_causes=["cause"], pareto_analysis={}, fishbone_categories={"cat": ["x"]})

    def test_empty_fishbone_categories_raises(self) -> None:
        """Test that empty fishbone categories raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="fishbone_categories must contain at least one category"):
            HookAnalyzePhase(root_causes=["cause"], pareto_analysis={"c": 1}, fishbone_categories={})


class TestHookImprovePhase:
    """Tests for HookImprovePhase dataclass."""

    def test_create_valid_improve_phase(self) -> None:
        """Test creating a valid improve phase."""
        # Arrange & Act
        improve = HookImprovePhase(
            solutions=[
                "Add SPARQL query validation on registration",
                "Increase timeout to 5s",
                "Add query result caching",
            ],
            pilot_results={"success_rate": 0.92, "avg_latency_ms": 38.5, "p99_latency_ms": 95.0},
            implementation_plan="Phase 1: Deploy validation. Phase 2: Increase timeout. Phase 3: Add caching.",
        )

        # Assert
        assert len(improve.solutions) == 3
        assert improve.pilot_results["success_rate"] == 0.92
        assert "Phase 1" in improve.implementation_plan

    def test_meets_target_success(self) -> None:
        """Test meets_target returns True when target is met."""
        # Arrange
        improve = HookImprovePhase(
            solutions=["Fix bug"], pilot_results={"success_rate": 0.95}, implementation_plan="Deploy to prod"
        )

        # Act & Assert
        assert improve.meets_target(0.90) is True
        assert improve.meets_target(0.95) is True

    def test_meets_target_failure(self) -> None:
        """Test meets_target returns False when target not met."""
        # Arrange
        improve = HookImprovePhase(
            solutions=["Fix bug"], pilot_results={"success_rate": 0.92}, implementation_plan="Deploy to prod"
        )

        # Act & Assert
        assert improve.meets_target(0.95) is False
        assert improve.meets_target(0.99) is False

    def test_empty_solutions_raises(self) -> None:
        """Test that empty solutions raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="solutions must contain at least one solution"):
            HookImprovePhase(solutions=[], pilot_results={"m": 1.0}, implementation_plan="Plan")

    def test_empty_pilot_results_raises(self) -> None:
        """Test that empty pilot results raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="pilot_results must contain at least one metric"):
            HookImprovePhase(solutions=["sol"], pilot_results={}, implementation_plan="Plan")

    def test_empty_implementation_plan_raises(self) -> None:
        """Test that empty implementation plan raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="implementation_plan cannot be empty"):
            HookImprovePhase(solutions=["sol"], pilot_results={"m": 1.0}, implementation_plan="")


class TestHookControlPhase:
    """Tests for HookControlPhase dataclass."""

    def test_create_valid_control_phase(self) -> None:
        """Test creating a valid control phase."""
        # Arrange & Act
        control = HookControlPhase(
            control_plan="Monitor hook receipts hourly, alert on SPC violations",
            spc_metrics={"success_rate": (0.90, 1.0), "avg_latency_ms": (0.0, 50.0), "p99_latency_ms": (0.0, 100.0)},
            response_plan="Auto-disable hook if success_rate < LCL for 3 consecutive hours",
        )

        # Assert
        assert "hourly" in control.control_plan
        assert control.spc_metrics["success_rate"] == (0.90, 1.0)
        assert "Auto-disable" in control.response_plan

    def test_is_within_limits_success(self) -> None:
        """Test is_within_limits returns True for values within bounds."""
        # Arrange
        control = HookControlPhase(
            control_plan="Monitor", spc_metrics={"success_rate": (0.90, 1.0)}, response_plan="Alert"
        )

        # Act & Assert
        assert control.is_within_limits("success_rate", 0.95) is True
        assert control.is_within_limits("success_rate", 0.90) is True
        assert control.is_within_limits("success_rate", 1.0) is True

    def test_is_within_limits_failure(self) -> None:
        """Test is_within_limits returns False for values outside bounds."""
        # Arrange
        control = HookControlPhase(
            control_plan="Monitor", spc_metrics={"success_rate": (0.90, 1.0)}, response_plan="Alert"
        )

        # Act & Assert
        assert control.is_within_limits("success_rate", 0.85) is False
        assert control.is_within_limits("success_rate", 1.05) is False

    def test_is_within_limits_unknown_metric(self) -> None:
        """Test is_within_limits returns False for unknown metric."""
        # Arrange
        control = HookControlPhase(
            control_plan="Monitor", spc_metrics={"success_rate": (0.90, 1.0)}, response_plan="Alert"
        )

        # Act & Assert
        assert control.is_within_limits("unknown_metric", 0.5) is False

    def test_get_violated_metrics_none(self) -> None:
        """Test get_violated_metrics returns empty list when all within limits."""
        # Arrange
        control = HookControlPhase(
            control_plan="Monitor",
            spc_metrics={"success_rate": (0.90, 1.0), "latency_ms": (0.0, 50.0)},
            response_plan="Alert",
        )

        # Act
        violated = control.get_violated_metrics({"success_rate": 0.95, "latency_ms": 45.0})

        # Assert
        assert violated == []

    def test_get_violated_metrics_some(self) -> None:
        """Test get_violated_metrics returns violated metrics."""
        # Arrange
        control = HookControlPhase(
            control_plan="Monitor",
            spc_metrics={"success_rate": (0.90, 1.0), "latency_ms": (0.0, 50.0)},
            response_plan="Alert",
        )

        # Act
        violated = control.get_violated_metrics({"success_rate": 0.85, "latency_ms": 45.0})

        # Assert
        assert violated == ["success_rate"]

    def test_get_violated_metrics_multiple(self) -> None:
        """Test get_violated_metrics returns all violated metrics."""
        # Arrange
        control = HookControlPhase(
            control_plan="Monitor",
            spc_metrics={"success_rate": (0.90, 1.0), "latency_ms": (0.0, 50.0)},
            response_plan="Alert",
        )

        # Act
        violated = control.get_violated_metrics({"success_rate": 0.85, "latency_ms": 55.0})

        # Assert
        assert len(violated) == 2
        assert "success_rate" in violated
        assert "latency_ms" in violated

    def test_invalid_control_limits_raises(self) -> None:
        """Test that LCL > UCL raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="LCL .* must be <= UCL"):
            HookControlPhase(control_plan="Monitor", spc_metrics={"success_rate": (1.0, 0.5)}, response_plan="Alert")

    def test_empty_control_plan_raises(self) -> None:
        """Test that empty control plan raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="control_plan cannot be empty"):
            HookControlPhase(control_plan="", spc_metrics={"m": (0.0, 1.0)}, response_plan="Alert")

    def test_empty_spc_metrics_raises(self) -> None:
        """Test that empty SPC metrics raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="spc_metrics must contain at least one metric"):
            HookControlPhase(control_plan="Monitor", spc_metrics={}, response_plan="Alert")

    def test_empty_response_plan_raises(self) -> None:
        """Test that empty response plan raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="response_plan cannot be empty"):
            HookControlPhase(control_plan="Monitor", spc_metrics={"m": (0.0, 1.0)}, response_plan="")


class TestHookDMAICCycle:
    """Tests for complete HookDMAICCycle."""

    def test_create_valid_cycle(self) -> None:
        """Test creating a valid complete DMAIC cycle."""
        # Arrange
        define = HookDefinePhase(
            problem_statement="Low validation success rate",
            hook_scope=["validate-person"],
            success_criteria={"success_rate": 0.95},
            stakeholders=["team"],
        )
        measure = HookMeasurePhase(
            baseline_metrics={"success_rate": 0.70}, measurement_system="Receipts", data_collection_plan="Hourly"
        )
        analyze = HookAnalyzePhase(
            root_causes=["Bug"], pareto_analysis={"Bug": 100}, fishbone_categories={"Tech": ["Bug"]}
        )
        improve = HookImprovePhase(
            solutions=["Fix bug"], pilot_results={"success_rate": 0.95}, implementation_plan="Deploy"
        )
        control = HookControlPhase(
            control_plan="Monitor", spc_metrics={"success_rate": (0.90, 1.0)}, response_plan="Alert"
        )

        # Act
        cycle = HookDMAICCycle(
            cycle_id="dmaic-2024-01",
            define=define,
            measure=measure,
            analyze=analyze,
            improve=improve,
            control=control,
            metadata={"owner": "data-team", "start_date": "2024-01-01"},
        )

        # Assert
        assert cycle.cycle_id == "dmaic-2024-01"
        assert cycle.define.problem_statement == "Low validation success rate"
        assert cycle.measure.baseline_metrics["success_rate"] == 0.70
        assert cycle.analyze.root_causes == ["Bug"]
        assert cycle.improve.pilot_results["success_rate"] == 0.95
        assert cycle.control.spc_metrics["success_rate"] == (0.90, 1.0)
        assert cycle.metadata["owner"] == "data-team"

    def test_is_complete_true(self) -> None:
        """Test is_complete returns True when all phases present."""
        # Arrange
        cycle = HookDMAICCycle(
            cycle_id="test",
            define=HookDefinePhase("Problem", ["hook1"], {"metric": 1.0}, ["team"]),
            measure=HookMeasurePhase({"m": 1.0}, "sys", "plan"),
            analyze=HookAnalyzePhase(["cause"], {"c": 1}, {"cat": ["x"]}),
            improve=HookImprovePhase(["sol"], {"m": 1.0}, "plan"),
            control=HookControlPhase("plan", {"m": (0.0, 1.0)}, "response"),
        )

        # Act & Assert
        assert cycle.is_complete() is True

    def test_improvement_achieved_calculation(self) -> None:
        """Test improvement_achieved calculates percentage correctly."""
        # Arrange
        cycle = HookDMAICCycle(
            cycle_id="test",
            define=HookDefinePhase("Problem", ["hook1"], {"metric": 1.0}, ["team"]),
            measure=HookMeasurePhase({"success_rate": 0.70}, "sys", "plan"),
            analyze=HookAnalyzePhase(["cause"], {"c": 1}, {"cat": ["x"]}),
            improve=HookImprovePhase(["sol"], {"success_rate": 0.95}, "plan"),
            control=HookControlPhase("plan", {"m": (0.0, 1.0)}, "response"),
        )

        # Act
        improvement = cycle.improvement_achieved()

        # Assert - 0.70 to 0.95 is (0.25 / 0.70) * 100 = 35.71%
        assert abs(improvement - 35.71) < 0.01

    def test_improvement_achieved_zero_baseline(self) -> None:
        """Test improvement_achieved returns 0 for zero baseline."""
        # Arrange
        cycle = HookDMAICCycle(
            cycle_id="test",
            define=HookDefinePhase("Problem", ["hook1"], {"metric": 1.0}, ["team"]),
            measure=HookMeasurePhase({"success_rate": 0.0}, "sys", "plan"),
            analyze=HookAnalyzePhase(["cause"], {"c": 1}, {"cat": ["x"]}),
            improve=HookImprovePhase(["sol"], {"success_rate": 0.95}, "plan"),
            control=HookControlPhase("plan", {"m": (0.0, 1.0)}, "response"),
        )

        # Act
        improvement = cycle.improvement_achieved()

        # Assert
        assert improvement == 0.0
