"""Workflow state management for StandardWorkLoop.

Tracks execution state across the 5 workflow steps:
1. Discover - Fetch data from Apple ingest
2. Align - Check ontology drift, update if needed
3. Regenerate - Run ALL generators
4. Review - Validate artifacts against SHACL
5. Remove - Detect waste, identify cleanup
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class WorkflowStep(Enum):
    """Workflow execution steps in order."""

    DISCOVER = "discover"
    ALIGN = "align"
    REGENERATE = "regenerate"
    REVIEW = "review"
    REMOVE = "remove"

    @classmethod
    def all_steps(cls) -> list["WorkflowStep"]:
        """Return all steps in execution order."""
        return [cls.DISCOVER, cls.ALIGN, cls.REGENERATE, cls.REVIEW, cls.REMOVE]

    @classmethod
    def next_step(cls, current: "WorkflowStep") -> "WorkflowStep | None":
        """Get next step after current, or None if complete."""
        steps = cls.all_steps()
        try:
            idx = steps.index(current)
            return steps[idx + 1] if idx + 1 < len(steps) else None
        except (ValueError, IndexError):
            return None


@dataclass
class StepResult:
    """Result from executing a workflow step."""

    step: WorkflowStep
    success: bool
    started_at: datetime
    completed_at: datetime
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Calculate step execution duration."""
        delta = self.completed_at - self.started_at
        return delta.total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "step": self.step.value,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepResult":
        """Create from JSON dict."""
        return cls(
            step=WorkflowStep(data["step"]),
            success=data["success"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]),
            data=data.get("data", {}),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )


@dataclass
class WorkflowState:
    """Tracks state of workflow execution.

    Maintains:
    - Current step being executed
    - Results from completed steps
    - Timing information
    - Errors and warnings
    - Data passed between steps
    """

    workflow_id: str
    started_at: datetime
    current_step: WorkflowStep | None = None
    completed_steps: list[StepResult] = field(default_factory=list)
    is_complete: bool = False
    failed: bool = False

    def start_step(self, step: WorkflowStep) -> None:
        """Mark step as started."""
        self.current_step = step

    def complete_step(
        self,
        step: WorkflowStep,
        success: bool,
        started_at: datetime,
        data: dict[str, Any] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        """Record step completion."""
        result = StepResult(
            step=step,
            success=success,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            data=data or {},
            errors=errors or [],
            warnings=warnings or [],
        )
        self.completed_steps.append(result)

        # Update workflow state
        if not success:
            self.failed = True
            self.is_complete = True
            self.current_step = None
        else:
            next_step = WorkflowStep.next_step(step)
            if next_step is None:
                self.is_complete = True
                self.current_step = None
            else:
                self.current_step = next_step

    def get_step_result(self, step: WorkflowStep) -> StepResult | None:
        """Get result for a specific step."""
        for result in self.completed_steps:
            if result.step == step:
                return result
        return None

    def get_step_data(self, step: WorkflowStep, key: str) -> Any:
        """Get data from a specific step's result."""
        result = self.get_step_result(step)
        if result:
            return result.data.get(key)
        return None

    @property
    def total_duration_seconds(self) -> float:
        """Total workflow execution time."""
        if not self.completed_steps:
            return 0.0

        now = datetime.now(UTC)
        delta = now - self.started_at
        return delta.total_seconds()

    @property
    def all_errors(self) -> list[str]:
        """Collect all errors from all steps."""
        errors = []
        for result in self.completed_steps:
            errors.extend(result.errors)
        return errors

    @property
    def all_warnings(self) -> list[str]:
        """Collect all warnings from all steps."""
        warnings = []
        for result in self.completed_steps:
            warnings.extend(result.warnings)
        return warnings

    def validate(self) -> list[str]:
        """Validate state consistency.

        Returns
        -------
            List of validation errors (empty if valid)
        """
        errors = []

        # Check step order
        expected_order = WorkflowStep.all_steps()
        completed_order = [r.step for r in self.completed_steps]

        for i, step in enumerate(completed_order):
            if i < len(expected_order) and step != expected_order[i]:
                errors.append(
                    f"Step order violation: {step.value} at position {i}, "
                    f"expected {expected_order[i].value}"
                )

        # Check current step is valid
        if self.current_step and self.is_complete:
            errors.append("Workflow marked complete but has current_step")

        # Check failed state consistency
        if self.failed and not any(not r.success for r in self.completed_steps):
            errors.append("Workflow marked failed but no failed steps")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "workflow_id": self.workflow_id,
            "started_at": self.started_at.isoformat(),
            "current_step": self.current_step.value if self.current_step else None,
            "completed_steps": [r.to_dict() for r in self.completed_steps],
            "is_complete": self.is_complete,
            "failed": self.failed,
            "total_duration_seconds": self.total_duration_seconds,
            "errors": self.all_errors,
            "warnings": self.all_warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowState":
        """Create from JSON dict."""
        current_step_value = data.get("current_step")
        return cls(
            workflow_id=data["workflow_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            current_step=WorkflowStep(current_step_value) if current_step_value else None,
            completed_steps=[StepResult.from_dict(r) for r in data.get("completed_steps", [])],
            is_complete=data.get("is_complete", False),
            failed=data.get("failed", False),
        )

    def save(self, path: Path) -> None:
        """Persist state to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "WorkflowState":
        """Load state from JSON file."""
        with path.open("r") as f:
            data = json.load(f)
        return cls.from_dict(data)
