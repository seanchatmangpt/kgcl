"""StandardWorkLoop orchestrator for KGC workflow.

Executes the 5-step workflow:
1. Discover - Fetch data from Apple ingest
2. Align - Check ontology drift, update if needed
3. Regenerate - Run ALL generators (agenda, quality, conflict, stale, diagrams)
4. Review - Validate artifacts against SHACL
5. Remove - Detect waste, identify cleanup opportunities

Each step triggers appropriate hooks and tracks execution state.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .state import WorkflowState, WorkflowStep


class IngestClient(Protocol):
    """Protocol for data ingestion client."""

    def fetch_all(self) -> dict[str, Any]:
        """Fetch all data from Apple ingest."""
        ...


class OntologyManager(Protocol):
    """Protocol for ontology drift detection."""

    def check_drift(self) -> dict[str, Any]:
        """Check for ontology drift and update if needed."""
        ...


class GeneratorRunner(Protocol):
    """Protocol for running all generators."""

    def run_all(self, ingested_data: dict[str, Any]) -> dict[str, Any]:
        """Run all generators (agenda, quality, conflict, stale, diagrams)."""
        ...


class ValidatorRunner(Protocol):
    """Protocol for validation."""

    def validate_all(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        """Validate all artifacts against SHACL."""
        ...


class WasteDetector(Protocol):
    """Protocol for waste detection."""

    def find_waste(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Detect waste and identify cleanup opportunities."""
        ...


class HookRegistry(Protocol):
    """Protocol for hook triggering."""

    def trigger(self, event: str, context: dict[str, Any]) -> None:
        """Trigger hooks for given event."""
        ...


class StandardWorkLoop:
    """Orchestrates the 5-step KGC workflow.

    Coordinates between:
    - Apple ingest (data fetching)
    - Ontology manager (drift detection)
    - Generators (artifact creation)
    - Validators (SHACL validation)
    - Waste detector (cleanup identification)
    - Hook system (event triggering)

    Tracks state and timing throughout execution.
    Provides error recovery with clear messages.
    """

    def __init__(
        self,
        ingest_client: IngestClient,
        ontology_manager: OntologyManager,
        generator_runner: GeneratorRunner,
        validator_runner: ValidatorRunner,
        waste_detector: WasteDetector,
        hook_registry: HookRegistry,
        state_dir: Path | None = None,
    ):
        """Initialize orchestrator with dependencies.

        Args:
            ingest_client: Client for fetching Apple data
            ontology_manager: Manager for ontology drift
            generator_runner: Runner for all generators
            validator_runner: Runner for SHACL validation
            waste_detector: Detector for waste identification
            hook_registry: Registry for triggering hooks
            state_dir: Directory for state persistence (default: .kgcl/workflows)
        """
        self.ingest = ingest_client
        self.ontology = ontology_manager
        self.generators = generator_runner
        self.validators = validator_runner
        self.waste = waste_detector
        self.hooks = hook_registry
        self.state_dir = state_dir or Path.cwd() / ".kgcl" / "workflows"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, workflow_id: str | None = None) -> WorkflowState:
        """Execute complete 5-step workflow.

        Args:
            workflow_id: Optional workflow identifier (generates UUID if None)

        Returns
        -------
            WorkflowState with execution results

        Raises
        ------
            Exception: If critical step fails (captured in state)
        """
        workflow_id = workflow_id or str(uuid.uuid4())
        state = WorkflowState(workflow_id=workflow_id, started_at=datetime.now(UTC), current_step=WorkflowStep.DISCOVER)

        # Execute each step in sequence
        try:
            self._execute_discover(state)
            if not state.failed:
                self._execute_align(state)
            if not state.failed:
                self._execute_regenerate(state)
            if not state.failed:
                self._execute_review(state)
            if not state.failed:
                self._execute_remove(state)

        except Exception as e:
            # Capture unexpected errors
            if state.current_step:
                state.complete_step(
                    step=state.current_step,
                    success=False,
                    started_at=datetime.now(UTC),
                    errors=[f"Unexpected error: {e!s}"],
                )

        # Persist final state
        self._save_state(state)
        return state

    def _execute_discover(self, state: WorkflowState) -> None:
        """Step 1: Discover - Fetch data from Apple ingest."""
        step = WorkflowStep.DISCOVER
        started_at = datetime.now(UTC)
        state.start_step(step)

        try:
            # Fetch all data from Apple ingest
            ingested_data = self.ingest.fetch_all()

            # Trigger IngestHook (will trigger AgendaGenerator)
            self.hooks.trigger(
                "ingest_complete",
                {"workflow_id": state.workflow_id, "data": ingested_data, "timestamp": datetime.now(UTC).isoformat()},
            )

            # Success
            state.complete_step(
                step=step,
                success=True,
                started_at=started_at,
                data={"ingested": ingested_data, "record_count": ingested_data.get("count", 0)},
            )

        except Exception as e:
            state.complete_step(step=step, success=False, started_at=started_at, errors=[f"Ingest failed: {e!s}"])

    def _execute_align(self, state: WorkflowState) -> None:
        """Step 2: Align - Check ontology drift, update if needed."""
        step = WorkflowStep.ALIGN
        started_at = datetime.now(UTC)
        state.start_step(step)

        try:
            # Check for ontology drift
            drift_result = self.ontology.check_drift()

            has_drift = drift_result.get("has_drift", False)
            changes = drift_result.get("changes", [])

            # Trigger OntologyChangeHook if drift detected
            if has_drift:
                self.hooks.trigger(
                    "ontology_changed",
                    {"workflow_id": state.workflow_id, "changes": changes, "timestamp": datetime.now(UTC).isoformat()},
                )

            # Success
            state.complete_step(
                step=step,
                success=True,
                started_at=started_at,
                data={
                    "has_drift": has_drift,
                    "changes": changes,
                    "ontology_version": drift_result.get("version", "unknown"),
                },
                warnings=["Ontology drift detected"] if has_drift else [],
            )

        except Exception as e:
            state.complete_step(
                step=step, success=False, started_at=started_at, errors=[f"Ontology alignment failed: {e!s}"]
            )

    def _execute_regenerate(self, state: WorkflowState) -> None:
        """Step 3: Regenerate - Run ALL generators."""
        step = WorkflowStep.REGENERATE
        started_at = datetime.now(UTC)
        state.start_step(step)

        try:
            # Get ingested data from Discover step
            ingested_data = state.get_step_data(WorkflowStep.DISCOVER, "ingested")
            if not ingested_data:
                raise ValueError("No ingested data available from Discover step")

            # Run all generators (agenda, quality, conflict, stale, diagrams)
            artifacts = self.generators.run_all(ingested_data)

            generator_names = artifacts.get("generators", [])
            artifact_count = artifacts.get("artifact_count", 0)

            # No hook trigger - this step IS the result of hooks
            # (IngestHook triggered AgendaGenerator in Discover)
            # (OntologyChangeHook triggered regeneration in Align)

            # Success
            state.complete_step(
                step=step,
                success=True,
                started_at=started_at,
                data={"artifacts": artifacts, "generators": generator_names, "artifact_count": artifact_count},
            )

        except Exception as e:
            state.complete_step(step=step, success=False, started_at=started_at, errors=[f"Regeneration failed: {e!s}"])

    def _execute_review(self, state: WorkflowState) -> None:
        """Step 4: Review - Validate artifacts against SHACL."""
        step = WorkflowStep.REVIEW
        started_at = datetime.now(UTC)
        state.start_step(step)

        try:
            # Get artifacts from Regenerate step
            artifacts = state.get_step_data(WorkflowStep.REGENERATE, "artifacts")
            if not artifacts:
                raise ValueError("No artifacts available from Regenerate step")

            # Validate all artifacts
            validation_result = self.validators.validate_all(artifacts)

            violations = validation_result.get("violations", [])
            has_violations = len(violations) > 0

            # Trigger ValidationFailureHook if violations found
            if has_violations:
                self.hooks.trigger(
                    "validation_failed",
                    {
                        "workflow_id": state.workflow_id,
                        "violations": violations,
                        "artifact_count": validation_result.get("artifact_count", 0),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

            # Success (violations are warnings, not failures)
            state.complete_step(
                step=step,
                success=True,
                started_at=started_at,
                data={
                    "violations": violations,
                    "violation_count": len(violations),
                    "validated_count": validation_result.get("artifact_count", 0),
                },
                warnings=[f"Found {len(violations)} validation violations"] if has_violations else [],
            )

        except Exception as e:
            state.complete_step(step=step, success=False, started_at=started_at, errors=[f"Validation failed: {e!s}"])

    def _execute_remove(self, state: WorkflowState) -> None:
        """Step 5: Remove - Detect waste, identify cleanup opportunities."""
        step = WorkflowStep.REMOVE
        started_at = datetime.now(UTC)
        state.start_step(step)

        try:
            # Collect data from all previous steps
            workflow_data = {
                "ingested": state.get_step_data(WorkflowStep.DISCOVER, "ingested"),
                "ontology_changes": state.get_step_data(WorkflowStep.ALIGN, "changes"),
                "artifacts": state.get_step_data(WorkflowStep.REGENERATE, "artifacts"),
                "violations": state.get_step_data(WorkflowStep.REVIEW, "violations"),
            }

            # Detect waste
            waste_result = self.waste.find_waste(workflow_data)

            waste_items = waste_result.get("waste_items", [])
            cleanup_opportunities = waste_result.get("cleanup_opportunities", [])

            # No hook trigger - this is a cleanup action, not event

            # Success
            state.complete_step(
                step=step,
                success=True,
                started_at=started_at,
                data={
                    "waste_items": waste_items,
                    "cleanup_opportunities": cleanup_opportunities,
                    "waste_count": len(waste_items),
                },
                warnings=[f"Found {len(waste_items)} waste items"] if waste_items else [],
            )

        except Exception as e:
            state.complete_step(
                step=step, success=False, started_at=started_at, errors=[f"Waste detection failed: {e!s}"]
            )

    def _save_state(self, state: WorkflowState) -> None:
        """Persist workflow state to disk."""
        state_file = self.state_dir / f"{state.workflow_id}.json"
        state.save(state_file)

    def load_state(self, workflow_id: str) -> WorkflowState | None:
        """Load workflow state from disk.

        Args:
            workflow_id: Workflow identifier

        Returns
        -------
            WorkflowState if found, None otherwise
        """
        state_file = self.state_dir / f"{workflow_id}.json"
        if not state_file.exists():
            return None
        return WorkflowState.load(state_file)

    def list_workflows(self) -> list[str]:
        """List all workflow IDs with saved state.

        Returns
        -------
            List of workflow IDs
        """
        return [f.stem for f in self.state_dir.glob("*.json")]

    def resume(self, workflow_id: str) -> WorkflowState:
        """Resume a failed or interrupted workflow.

        Args:
            workflow_id: Workflow identifier to resume

        Returns
        -------
            WorkflowState with execution results

        Raises
        ------
            ValueError: If workflow not found or already complete
        """
        state = self.load_state(workflow_id)
        if not state:
            raise ValueError(f"Workflow {workflow_id} not found")

        if state.is_complete:
            raise ValueError(f"Workflow {workflow_id} already complete")

        # Execute from current step
        if state.current_step == WorkflowStep.DISCOVER:
            self._execute_discover(state)
        if state.current_step == WorkflowStep.ALIGN and not state.failed:
            self._execute_align(state)
        if state.current_step == WorkflowStep.REGENERATE and not state.failed:
            self._execute_regenerate(state)
        if state.current_step == WorkflowStep.REVIEW and not state.failed:
            self._execute_review(state)
        if state.current_step == WorkflowStep.REMOVE and not state.failed:
            self._execute_remove(state)

        self._save_state(state)
        return state
