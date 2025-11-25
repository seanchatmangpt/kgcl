"""Workflow metrics for StandardWorkLoop analysis.

Calculates:
- Lead time (discover → review)
- Rework rate (step re-executions)
- Drift detection (artifact vs source freshness)
- Hands-on time (manual interventions)
- Bottlenecks (slowest steps)
- Trends (metrics over time)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .state import WorkflowState, WorkflowStep


@dataclass
class StepMetrics:
    """Metrics for a single workflow step."""

    step: WorkflowStep
    execution_count: int = 0
    total_duration_seconds: float = 0.0
    failure_count: int = 0
    average_duration_seconds: float = 0.0

    def update(self, duration: float, failed: bool) -> None:
        """Update metrics with new execution."""
        self.execution_count += 1
        self.total_duration_seconds += duration
        if failed:
            self.failure_count += 1

        # Recalculate average
        self.average_duration_seconds = self.total_duration_seconds / self.execution_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "step": self.step.value,
            "execution_count": self.execution_count,
            "total_duration_seconds": self.total_duration_seconds,
            "failure_count": self.failure_count,
            "average_duration_seconds": self.average_duration_seconds,
            "failure_rate": (
                self.failure_count / self.execution_count if self.execution_count > 0 else 0.0
            ),
        }


@dataclass
class WorkflowMetrics:
    """Metrics for StandardWorkLoop execution.

    Tracks:
    - Lead time: Time from discover to review
    - Rework rate: How often steps are re-executed
    - Drift: Artifact freshness vs source data
    - Hands-on time: Manual intervention duration
    - Bottlenecks: Slowest steps
    - Trends: Metrics over time
    """

    step_metrics: dict[WorkflowStep, StepMetrics] = field(default_factory=dict)
    total_workflows: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    total_lead_time_seconds: float = 0.0
    manual_interventions: int = 0
    manual_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        """Initialize step metrics for all steps."""
        if not self.step_metrics:
            self.step_metrics = {step: StepMetrics(step=step) for step in WorkflowStep.all_steps()}

    def record_workflow(self, state: WorkflowState) -> None:
        """Record metrics from completed workflow.

        Args:
            state: Completed workflow state
        """
        self.total_workflows += 1

        if state.failed:
            self.failed_workflows += 1
        else:
            self.successful_workflows += 1

        # Record step metrics
        for result in state.completed_steps:
            step_metric = self.step_metrics[result.step]
            step_metric.update(duration=result.duration_seconds, failed=not result.success)

        # Calculate lead time (Discover → Review)
        discover_result = state.get_step_result(WorkflowStep.DISCOVER)
        review_result = state.get_step_result(WorkflowStep.REVIEW)

        if discover_result and review_result:
            lead_time = (review_result.completed_at - discover_result.started_at).total_seconds()
            self.total_lead_time_seconds += lead_time

    def record_manual_intervention(self, duration_seconds: float) -> None:
        """Record manual intervention.

        Args:
            duration_seconds: Time spent on manual intervention
        """
        self.manual_interventions += 1
        self.manual_time_seconds += duration_seconds

    @property
    def success_rate(self) -> float:
        """Calculate workflow success rate."""
        if self.total_workflows == 0:
            return 0.0
        return self.successful_workflows / self.total_workflows

    @property
    def average_lead_time_seconds(self) -> float:
        """Calculate average lead time."""
        if self.successful_workflows == 0:
            return 0.0
        return self.total_lead_time_seconds / self.successful_workflows

    @property
    def rework_rate(self) -> float:
        """Calculate rework rate (step failures requiring re-execution).

        Returns
        -------
            Ratio of failed step executions to total executions
        """
        total_executions = sum(m.execution_count for m in self.step_metrics.values())
        total_failures = sum(m.failure_count for m in self.step_metrics.values())

        if total_executions == 0:
            return 0.0
        return total_failures / total_executions

    @property
    def bottleneck_step(self) -> WorkflowStep | None:
        """Identify bottleneck step (slowest average duration).

        Returns
        -------
            WorkflowStep that takes longest on average
        """
        slowest = max(
            self.step_metrics.values(), key=lambda m: m.average_duration_seconds, default=None
        )
        return slowest.step if slowest else None

    @property
    def hands_on_ratio(self) -> float:
        """Calculate ratio of manual intervention time to total workflow time.

        Returns
        -------
            Ratio of manual time to total lead time
        """
        if self.total_lead_time_seconds == 0:
            return 0.0
        return self.manual_time_seconds / self.total_lead_time_seconds

    def get_step_metrics(self, step: WorkflowStep) -> StepMetrics:
        """Get metrics for specific step.

        Args:
            step: Workflow step

        Returns
        -------
            StepMetrics for the step
        """
        return self.step_metrics[step]

    def get_top_failures(self, limit: int = 3) -> list[tuple[WorkflowStep, float]]:
        """Get steps with highest failure rates.

        Args:
            limit: Maximum number of steps to return

        Returns
        -------
            List of (step, failure_rate) tuples, highest first
        """
        failure_rates = [
            (
                step,
                (
                    metrics.failure_count / metrics.execution_count
                    if metrics.execution_count > 0
                    else 0.0
                ),
            )
            for step, metrics in self.step_metrics.items()
        ]

        return sorted(failure_rates, key=lambda x: x[1], reverse=True)[:limit]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "total_workflows": self.total_workflows,
            "successful_workflows": self.successful_workflows,
            "failed_workflows": self.failed_workflows,
            "success_rate": self.success_rate,
            "average_lead_time_seconds": self.average_lead_time_seconds,
            "rework_rate": self.rework_rate,
            "bottleneck_step": self.bottleneck_step.value if self.bottleneck_step else None,
            "manual_interventions": self.manual_interventions,
            "manual_time_seconds": self.manual_time_seconds,
            "hands_on_ratio": self.hands_on_ratio,
            "step_metrics": {
                step.value: metrics.to_dict() for step, metrics in self.step_metrics.items()
            },
            "top_failures": [
                {"step": step.value, "failure_rate": rate} for step, rate in self.get_top_failures()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowMetrics":
        """Create from JSON dict."""
        step_metrics = {
            WorkflowStep(step_name): StepMetrics(
                step=WorkflowStep(step_name),
                execution_count=step_data["execution_count"],
                total_duration_seconds=step_data["total_duration_seconds"],
                failure_count=step_data["failure_count"],
                average_duration_seconds=step_data["average_duration_seconds"],
            )
            for step_name, step_data in data.get("step_metrics", {}).items()
        }

        return cls(
            step_metrics=step_metrics,
            total_workflows=data["total_workflows"],
            successful_workflows=data["successful_workflows"],
            failed_workflows=data["failed_workflows"],
            total_lead_time_seconds=data["total_lead_time_seconds"],
            manual_interventions=data["manual_interventions"],
            manual_time_seconds=data["manual_time_seconds"],
        )

    def save(self, path: Path) -> None:
        """Persist metrics to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "WorkflowMetrics":
        """Load metrics from JSON file."""
        with path.open("r") as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class TrendPoint:
    """Single point in metrics trend over time."""

    timestamp: datetime
    metric_name: str
    value: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrendPoint":
        """Create from JSON dict."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metric_name=data["metric_name"],
            value=data["value"],
        )


class MetricsTrendAnalyzer:
    """Analyzes metrics trends over time."""

    def __init__(self, metrics_dir: Path | None = None):
        """Initialize trend analyzer.

        Args:
            metrics_dir: Directory for trend data (default: .kgcl/metrics)
        """
        self.metrics_dir = metrics_dir or Path.cwd() / ".kgcl" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.trends: list[TrendPoint] = []
        self._load_trends()

    def record_snapshot(self, metrics: WorkflowMetrics) -> None:
        """Record current metrics as trend snapshot.

        Args:
            metrics: Current workflow metrics
        """
        timestamp = datetime.utcnow()

        # Record key metrics
        self.trends.extend(
            [
                TrendPoint(timestamp, "success_rate", metrics.success_rate),
                TrendPoint(timestamp, "average_lead_time", metrics.average_lead_time_seconds),
                TrendPoint(timestamp, "rework_rate", metrics.rework_rate),
                TrendPoint(timestamp, "hands_on_ratio", metrics.hands_on_ratio),
            ]
        )

        self._save_trends()

    def get_trend(self, metric_name: str, days: int = 30) -> list[tuple[datetime, float]]:
        """Get trend for specific metric.

        Args:
            metric_name: Name of metric to analyze
            days: Number of days to include

        Returns
        -------
            List of (timestamp, value) tuples
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [
            (p.timestamp, p.value)
            for p in self.trends
            if p.metric_name == metric_name and p.timestamp >= cutoff
        ]

    def detect_degradation(self, metric_name: str, threshold: float = 0.2) -> bool:
        """Detect if metric is degrading over time.

        Args:
            metric_name: Metric to check
            threshold: Degradation threshold (0.2 = 20% worse)

        Returns
        -------
            True if metric degraded by more than threshold
        """
        trend = self.get_trend(metric_name, days=7)  # Last week
        if len(trend) < 2:
            return False

        # Compare most recent to week average
        recent = trend[-1][1]
        week_avg = sum(v for _, v in trend) / len(trend)

        # Different metrics degrade differently
        if metric_name in ["success_rate"]:
            # Lower is worse
            degradation = (week_avg - recent) / week_avg if week_avg > 0 else 0
        else:
            # Higher is worse (lead time, rework, hands-on)
            degradation = (recent - week_avg) / week_avg if week_avg > 0 else 0

        return degradation > threshold

    def _save_trends(self) -> None:
        """Persist trends to disk."""
        trends_file = self.metrics_dir / "trends.json"
        data = [p.to_dict() for p in self.trends]
        with trends_file.open("w") as f:
            json.dump(data, f, indent=2)

    def _load_trends(self) -> None:
        """Load trends from disk."""
        trends_file = self.metrics_dir / "trends.json"
        if not trends_file.exists():
            return

        with trends_file.open("r") as f:
            data = json.load(f)

        self.trends = [TrendPoint.from_dict(p) for p in data]
