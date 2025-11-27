"""DMAIC Phase Definitions for Knowledge Hooks.

This module defines the DMAIC phases enum and phase dataclasses for tracking
Knowledge Hook quality improvement across all 5 phases of the DMAIC methodology.

The DMAIC methodology applied to Knowledge Hooks enables:
- DEFINE: Identify hook problems and define scope
- MEASURE: Establish baseline hook performance metrics
- ANALYZE: Identify root causes of hook failures
- IMPROVE: Implement and test hook solutions
- CONTROL: Monitor and maintain hook quality
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HookDMAICPhase(str, Enum):
    """DMAIC methodology phases for Knowledge Hooks quality improvement.

    Examples
    --------
    >>> HookDMAICPhase.DEFINE
    <HookDMAICPhase.DEFINE: 'define'>
    >>> [p.value for p in HookDMAICPhase]
    ['define', 'measure', 'analyze', 'improve', 'control']
    >>> len(HookDMAICPhase)
    5
    >>> HookDMAICPhase("measure")
    <HookDMAICPhase.MEASURE: 'measure'>
    """

    DEFINE = "define"
    MEASURE = "measure"
    ANALYZE = "analyze"
    IMPROVE = "improve"
    CONTROL = "control"


@dataclass(frozen=True)
class HookDefinePhase:
    """Define phase for Knowledge Hooks DMAIC.

    Captures the problem statement, hook scope, success criteria, and stakeholders
    for a Knowledge Hook quality improvement initiative.

    Attributes
    ----------
    problem_statement : str
        Clear description of the hook problem or improvement opportunity
    hook_scope : list[str]
        List of hook IDs in scope for this DMAIC initiative
    success_criteria : dict[str, float]
        Metric name to target value mapping (e.g., {"success_rate": 0.95})
    stakeholders : list[str]
        People or teams affected by this hook improvement

    Examples
    --------
    >>> define = HookDefinePhase(
    ...     problem_statement="Validation hooks failing 30% of the time",
    ...     hook_scope=["validate-person", "validate-org"],
    ...     success_criteria={"success_rate": 0.95, "p99_latency_ms": 50.0},
    ...     stakeholders=["data-quality-team", "api-users"],
    ... )
    >>> define.problem_statement
    'Validation hooks failing 30% of the time'
    >>> len(define.hook_scope)
    2
    >>> define.success_criteria["success_rate"]
    0.95
    """

    problem_statement: str
    hook_scope: list[str]
    success_criteria: dict[str, float]
    stakeholders: list[str]

    def __post_init__(self) -> None:
        """Validate define phase data."""
        if not self.problem_statement.strip():
            msg = "problem_statement cannot be empty"
            raise ValueError(msg)
        if not self.hook_scope:
            msg = "hook_scope must contain at least one hook ID"
            raise ValueError(msg)
        if not self.success_criteria:
            msg = "success_criteria must contain at least one metric"
            raise ValueError(msg)


@dataclass(frozen=True)
class HookMeasurePhase:
    """Measure phase for Knowledge Hooks DMAIC.

    Establishes baseline metrics, measurement system, and data collection plan
    for Knowledge Hook performance.

    Attributes
    ----------
    baseline_metrics : dict[str, float]
        Current performance metrics (e.g., {"success_rate": 0.70, "avg_latency_ms": 45.2})
    measurement_system : str
        Description of how metrics are collected (e.g., "HookReceipt analysis")
    data_collection_plan : str
        Plan for ongoing metric collection

    Examples
    --------
    >>> measure = HookMeasurePhase(
    ...     baseline_metrics={"success_rate": 0.70, "avg_latency_ms": 45.2, "p99_latency_ms": 120.0},
    ...     measurement_system="HookReceipt analysis from production",
    ...     data_collection_plan="Collect receipts every tick, aggregate hourly",
    ... )
    >>> measure.baseline_metrics["success_rate"]
    0.7
    >>> "HookReceipt" in measure.measurement_system
    True
    """

    baseline_metrics: dict[str, float]
    measurement_system: str
    data_collection_plan: str

    def __post_init__(self) -> None:
        """Validate measure phase data."""
        if not self.baseline_metrics:
            msg = "baseline_metrics must contain at least one metric"
            raise ValueError(msg)
        if not self.measurement_system.strip():
            msg = "measurement_system cannot be empty"
            raise ValueError(msg)
        if not self.data_collection_plan.strip():
            msg = "data_collection_plan cannot be empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class HookAnalyzePhase:
    """Analyze phase for Knowledge Hooks DMAIC.

    Identifies root causes of hook failures using Pareto analysis and
    fishbone diagrams to categorize issues.

    Attributes
    ----------
    root_causes : list[str]
        Identified root causes of hook failures
    pareto_analysis : dict[str, int]
        Cause to frequency mapping showing most common issues
    fishbone_categories : dict[str, list[str]]
        Fishbone diagram categories with causes (e.g., {"People": [...], "Process": [...]})

    Examples
    --------
    >>> analyze = HookAnalyzePhase(
    ...     root_causes=["Missing SPARQL escaping", "Timeout too short", "Race condition"],
    ...     pareto_analysis={"Missing escaping": 45, "Timeout": 30, "Race condition": 15, "Other": 10},
    ...     fishbone_categories={
    ...         "People": ["Unclear SPARQL docs"],
    ...         "Process": ["No validation on hook registration"],
    ...         "Technology": ["SPARQL parser limitations"],
    ...         "Environment": ["Heavy production load"],
    ...     },
    ... )
    >>> len(analyze.root_causes)
    3
    >>> analyze.pareto_analysis["Missing escaping"]
    45
    >>> "People" in analyze.fishbone_categories
    True
    """

    root_causes: list[str]
    pareto_analysis: dict[str, int]
    fishbone_categories: dict[str, list[str]]

    def __post_init__(self) -> None:
        """Validate analyze phase data."""
        if not self.root_causes:
            msg = "root_causes must contain at least one cause"
            raise ValueError(msg)
        if not self.pareto_analysis:
            msg = "pareto_analysis must contain at least one entry"
            raise ValueError(msg)
        if not self.fishbone_categories:
            msg = "fishbone_categories must contain at least one category"
            raise ValueError(msg)

    @property
    def top_cause(self) -> str:
        """Get the most frequent root cause from Pareto analysis.

        Returns
        -------
        str
            Cause with highest frequency

        Examples
        --------
        >>> analyze = HookAnalyzePhase(
        ...     root_causes=["A", "B"], pareto_analysis={"A": 100, "B": 50}, fishbone_categories={"People": ["A"]}
        ... )
        >>> analyze.top_cause
        'A'
        """
        return max(self.pareto_analysis.items(), key=lambda x: x[1])[0]


@dataclass(frozen=True)
class HookImprovePhase:
    """Improve phase for Knowledge Hooks DMAIC.

    Documents solutions, pilot test results, and implementation plans
    for hook improvements.

    Attributes
    ----------
    solutions : list[str]
        Proposed solutions to address root causes
    pilot_results : dict[str, float]
        Metrics from pilot testing (e.g., {"success_rate": 0.92})
    implementation_plan : str
        Plan for rolling out improvements to production

    Examples
    --------
    >>> improve = HookImprovePhase(
    ...     solutions=[
    ...         "Add SPARQL query validation on registration",
    ...         "Increase timeout to 5s",
    ...         "Add query result caching",
    ...     ],
    ...     pilot_results={"success_rate": 0.92, "avg_latency_ms": 38.5, "p99_latency_ms": 95.0},
    ...     implementation_plan="Phase 1: Deploy validation. Phase 2: Increase timeout. Phase 3: Add caching.",
    ... )
    >>> len(improve.solutions)
    3
    >>> improve.pilot_results["success_rate"]
    0.92
    >>> improve.meets_target(0.90)
    True
    """

    solutions: list[str]
    pilot_results: dict[str, float]
    implementation_plan: str

    def __post_init__(self) -> None:
        """Validate improve phase data."""
        if not self.solutions:
            msg = "solutions must contain at least one solution"
            raise ValueError(msg)
        if not self.pilot_results:
            msg = "pilot_results must contain at least one metric"
            raise ValueError(msg)
        if not self.implementation_plan.strip():
            msg = "implementation_plan cannot be empty"
            raise ValueError(msg)

    def meets_target(self, target_success_rate: float) -> bool:
        """Check if pilot results meet target success rate.

        Parameters
        ----------
        target_success_rate : float
            Target success rate (0.0 to 1.0)

        Returns
        -------
        bool
            True if pilot success rate meets or exceeds target

        Examples
        --------
        >>> improve = HookImprovePhase(
        ...     solutions=["Fix bug"], pilot_results={"success_rate": 0.95}, implementation_plan="Deploy to prod"
        ... )
        >>> improve.meets_target(0.90)
        True
        >>> improve.meets_target(0.99)
        False
        """
        return self.pilot_results.get("success_rate", 0.0) >= target_success_rate


@dataclass(frozen=True)
class HookControlPhase:
    """Control phase for Knowledge Hooks DMAIC.

    Establishes ongoing control plan, Statistical Process Control (SPC) metrics,
    and response plans for maintaining hook quality.

    Attributes
    ----------
    control_plan : str
        Description of ongoing monitoring and maintenance
    spc_metrics : dict[str, tuple[float, float]]
        Metric to (LCL, UCL) control limits mapping
    response_plan : str
        Plan for responding to out-of-control conditions

    Examples
    --------
    >>> control = HookControlPhase(
    ...     control_plan="Monitor hook receipts hourly, alert on SPC violations",
    ...     spc_metrics={"success_rate": (0.90, 1.0), "avg_latency_ms": (0.0, 50.0), "p99_latency_ms": (0.0, 100.0)},
    ...     response_plan="Auto-disable hook if success_rate < LCL for 3 consecutive hours",
    ... )
    >>> control.spc_metrics["success_rate"]
    (0.9, 1.0)
    >>> control.is_within_limits("success_rate", 0.95)
    True
    >>> control.is_within_limits("success_rate", 0.85)
    False
    """

    control_plan: str
    spc_metrics: dict[str, tuple[float, float]]
    response_plan: str

    def __post_init__(self) -> None:
        """Validate control phase data."""
        if not self.control_plan.strip():
            msg = "control_plan cannot be empty"
            raise ValueError(msg)
        if not self.spc_metrics:
            msg = "spc_metrics must contain at least one metric"
            raise ValueError(msg)
        if not self.response_plan.strip():
            msg = "response_plan cannot be empty"
            raise ValueError(msg)

        # Validate control limits
        for metric, (lcl, ucl) in self.spc_metrics.items():
            if lcl > ucl:
                msg = f"LCL ({lcl}) must be <= UCL ({ucl}) for metric {metric}"
                raise ValueError(msg)

    def is_within_limits(self, metric: str, value: float) -> bool:
        """Check if a metric value is within SPC control limits.

        Parameters
        ----------
        metric : str
            Metric name
        value : float
            Observed metric value

        Returns
        -------
        bool
            True if value is within [LCL, UCL]

        Examples
        --------
        >>> control = HookControlPhase(
        ...     control_plan="Monitor", spc_metrics={"success_rate": (0.90, 1.0)}, response_plan="Alert"
        ... )
        >>> control.is_within_limits("success_rate", 0.95)
        True
        >>> control.is_within_limits("success_rate", 0.85)
        False
        >>> control.is_within_limits("success_rate", 1.05)
        False
        """
        if metric not in self.spc_metrics:
            return False
        lcl, ucl = self.spc_metrics[metric]
        return lcl <= value <= ucl

    def get_violated_metrics(self, current_metrics: dict[str, float]) -> list[str]:
        """Get list of metrics violating SPC control limits.

        Parameters
        ----------
        current_metrics : dict[str, float]
            Current metric values

        Returns
        -------
        list[str]
            Metrics that are out of control

        Examples
        --------
        >>> control = HookControlPhase(
        ...     control_plan="Monitor",
        ...     spc_metrics={"success_rate": (0.90, 1.0), "latency_ms": (0.0, 50.0)},
        ...     response_plan="Alert",
        ... )
        >>> control.get_violated_metrics({"success_rate": 0.85, "latency_ms": 45.0})
        ['success_rate']
        >>> control.get_violated_metrics({"success_rate": 0.95, "latency_ms": 45.0})
        []
        """
        violated = []
        for metric, value in current_metrics.items():
            if not self.is_within_limits(metric, value):
                violated.append(metric)
        return violated


@dataclass(frozen=True)
class HookDMAICCycle:
    """Complete DMAIC cycle for Knowledge Hook quality improvement.

    Attributes
    ----------
    cycle_id : str
        Unique identifier for this DMAIC cycle
    define : HookDefinePhase
        Define phase data
    measure : HookMeasurePhase
        Measure phase data
    analyze : HookAnalyzePhase
        Analyze phase data
    improve : HookImprovePhase
        Improve phase data
    control : HookControlPhase
        Control phase data
    metadata : dict[str, str]
        Additional cycle metadata

    Examples
    --------
    >>> cycle = HookDMAICCycle(
    ...     cycle_id="dmaic-2024-01",
    ...     define=HookDefinePhase(
    ...         problem_statement="Low validation success rate",
    ...         hook_scope=["validate-person"],
    ...         success_criteria={"success_rate": 0.95},
    ...         stakeholders=["team"],
    ...     ),
    ...     measure=HookMeasurePhase(
    ...         baseline_metrics={"success_rate": 0.70}, measurement_system="Receipts", data_collection_plan="Hourly"
    ...     ),
    ...     analyze=HookAnalyzePhase(
    ...         root_causes=["Bug"], pareto_analysis={"Bug": 100}, fishbone_categories={"Tech": ["Bug"]}
    ...     ),
    ...     improve=HookImprovePhase(
    ...         solutions=["Fix bug"], pilot_results={"success_rate": 0.95}, implementation_plan="Deploy"
    ...     ),
    ...     control=HookControlPhase(
    ...         control_plan="Monitor", spc_metrics={"success_rate": (0.90, 1.0)}, response_plan="Alert"
    ...     ),
    ... )
    >>> cycle.cycle_id
    'dmaic-2024-01'
    >>> cycle.is_complete()
    True
    """

    cycle_id: str
    define: HookDefinePhase
    measure: HookMeasurePhase
    analyze: HookAnalyzePhase
    improve: HookImprovePhase
    control: HookControlPhase
    metadata: dict[str, str] = field(default_factory=dict)

    def is_complete(self) -> bool:
        """Check if all DMAIC phases are complete.

        Returns
        -------
        bool
            True if all phases have data

        Examples
        --------
        >>> cycle = HookDMAICCycle(
        ...     cycle_id="test",
        ...     define=HookDefinePhase("Problem", ["hook1"], {"metric": 1.0}, ["team"]),
        ...     measure=HookMeasurePhase({"m": 1.0}, "sys", "plan"),
        ...     analyze=HookAnalyzePhase(["cause"], {"c": 1}, {"cat": ["x"]}),
        ...     improve=HookImprovePhase(["sol"], {"m": 1.0}, "plan"),
        ...     control=HookControlPhase("plan", {"m": (0.0, 1.0)}, "response"),
        ... )
        >>> cycle.is_complete()
        True
        """
        return all(
            [
                self.define is not None,
                self.measure is not None,
                self.analyze is not None,
                self.improve is not None,
                self.control is not None,
            ]
        )

    def improvement_achieved(self) -> float:
        """Calculate improvement from baseline to pilot results.

        Returns
        -------
        float
            Percentage improvement in success_rate

        Examples
        --------
        >>> cycle = HookDMAICCycle(
        ...     cycle_id="test",
        ...     define=HookDefinePhase("Problem", ["hook1"], {"metric": 1.0}, ["team"]),
        ...     measure=HookMeasurePhase({"success_rate": 0.70}, "sys", "plan"),
        ...     analyze=HookAnalyzePhase(["cause"], {"c": 1}, {"cat": ["x"]}),
        ...     improve=HookImprovePhase(["sol"], {"success_rate": 0.95}, "plan"),
        ...     control=HookControlPhase("plan", {"m": (0.0, 1.0)}, "response"),
        ... )
        >>> abs(cycle.improvement_achieved() - 35.71) < 0.01
        True
        """
        baseline = self.measure.baseline_metrics.get("success_rate", 0.0)
        pilot = self.improve.pilot_results.get("success_rate", 0.0)
        if baseline == 0.0:
            return 0.0
        return ((pilot - baseline) / baseline) * 100.0
