"""KGC Integration - Wire generators to hooks and start workflow.

This module ties together all components:
- Hook orchestrator (loads hooks.ttl, executes on events)
- Generator handlers (produce artifacts)
- Workflow orchestrator (5-step loop)
- Hook scheduler (cron-based execution)

End-to-end data flow:
  Data Ingest → Validation → Hook Triggers → Generators → Artifacts
     ↑                                                         ↓
     └─────────────────────────────────────────────────────────
                    (feedback loop)

Chicago TDD Pattern:
    - Real objects (no mocking)
    - Protocol-based design
    - Clear responsibility separation
    - Easy to test
"""

from datetime import datetime
from pathlib import Path
from typing import Any
import logging

from rdflib import Graph

from kgcl.hooks.orchestrator import HookOrchestrator
from kgcl.hooks.handlers import register_all_handlers
from kgcl.hooks.scheduler import HookScheduler
from kgcl.workflow.orchestrator import StandardWorkLoop
from kgcl.workflow.scheduler import WorkflowScheduler, ScheduleConfig


logger = logging.getLogger(__name__)


class KGCIntegration:
    """Complete KGC system integration.

    Manages:
    - Hook loading and orchestration
    - Generator registration
    - Workflow orchestration
    - Scheduling (hooks and workflows)

    Usage:
        >>> integration = KGCIntegration(
        ...     graph=rdf_graph,
        ...     hooks_file=Path(".kgc/hooks.ttl"),
        ...     ingest_client=apple_ingest,
        ...     # ... other dependencies
        ... )
        >>>
        >>> # Start everything
        >>> integration.start()
        >>>
        >>> # Execute one iteration manually
        >>> state = integration.run_workflow_once()
    """

    def __init__(
        self,
        graph: Graph,
        hooks_file: Path,
        ingest_client,
        ontology_manager,
        generator_runner,
        validator_runner,
        waste_detector,
        state_dir: Path | None = None,
    ):
        """Initialize KGC integration with all dependencies.

        Args:
            graph: RDF graph for all components
            hooks_file: Path to hooks.ttl
            ingest_client: Apple data ingest client
            ontology_manager: Ontology drift detection
            generator_runner: Artifact generators
            validator_runner: SHACL validation
            waste_detector: Waste/cleanup detection
            state_dir: Directory for persisting state (default: .kgc/state)
        """
        self.graph = graph
        self.hooks_file = hooks_file

        logger.info("🔧 Initializing KGC Integration...")

        # 1️⃣ Initialize hook orchestrator
        try:
            self.hook_orchestrator = HookOrchestrator(
                graph=graph,
                hooks_file=hooks_file,
                continue_on_error=True
            )
            logger.info(f"✅ Hook Orchestrator initialized with {len(self.hook_orchestrator.hooks)} hooks")
        except Exception as e:
            logger.error(f"❌ Failed to initialize hook orchestrator: {e}")
            raise

        # 2️⃣ Register all generator handlers
        try:
            register_all_handlers(self.hook_orchestrator)
            logger.info("✅ Generator handlers registered")
        except Exception as e:
            logger.error(f"❌ Failed to register handlers: {e}")
            raise

        # 3️⃣ Initialize hook scheduler
        try:
            self.hook_scheduler = HookScheduler(self.hook_orchestrator)
            logger.info("✅ Hook Scheduler initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize hook scheduler: {e}")
            raise

        # 4️⃣ Initialize workflow orchestrator
        try:
            self.workflow = StandardWorkLoop(
                ingest_client=ingest_client,
                ontology_manager=ontology_manager,
                generator_runner=generator_runner,
                validator_runner=validator_runner,
                waste_detector=waste_detector,
                hook_registry=self,  # Pass self as hook registry
                state_dir=state_dir,
            )
            logger.info("✅ Workflow Orchestrator initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize workflow: {e}")
            raise

        # 5️⃣ Initialize workflow scheduler
        try:
            self.workflow_scheduler = WorkflowScheduler(self.workflow)
            logger.info("✅ Workflow Scheduler initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize workflow scheduler: {e}")
            raise

        logger.info("✅ KGC Integration initialized successfully!")

    def trigger_hook_event(self, event_uri: str, event_data: dict[str, Any] | None = None) -> None:
        """Trigger a hook event (implements HookRegistry protocol).

        This method is called by the workflow orchestrator when hooks should fire.

        Args:
            event_uri: Event URI (e.g., "urn:kgc:apple:DataIngested")
            event_data: Optional event payload data
        """
        if event_data is None:
            event_data = {}

        logger.debug(f"Triggering hook event: {event_uri}")

        try:
            result = self.hook_orchestrator.trigger_event(event_uri, event_data)
            logger.info(f"✅ Hook event executed: {len(result.receipts)} effects")
        except Exception as e:
            logger.error(f"❌ Hook event failed: {e}")

    def run_workflow_once(self) -> Any:
        """Execute one complete workflow iteration.

        Runs the 5-step Standard Work Loop once:
        1. Discover (fetch Apple data)
        2. Align (check ontology drift)
        3. Regenerate (run all generators)
        4. Review (validate artifacts)
        5. Remove (identify waste)

        Returns:
            WorkflowState with execution results
        """
        logger.info("🔄 Starting workflow iteration...")
        try:
            state = self.workflow.execute()
            logger.info(f"✅ Workflow completed: {state.status}")
            return state
        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}")
            raise

    def start_background_schedulers(
        self,
        hook_schedule: dict[str, str] | None = None,
        workflow_schedule: ScheduleConfig | None = None,
    ) -> None:
        """Start background schedulers for hooks and workflows.

        Args:
            hook_schedule: Hook cron schedules (hook_name -> cron_expr)
                          If None, uses schedules from hooks.ttl
            workflow_schedule: Workflow schedule config
                              If None, defaults to daily at 6am
        """
        logger.info("▶️  Starting background schedulers...")

        # Start hook scheduler (loads schedules from hooks.ttl)
        try:
            self.hook_scheduler.start()
            logger.info("✅ Hook Scheduler started")
        except Exception as e:
            logger.error(f"❌ Failed to start hook scheduler: {e}")

        # Start workflow scheduler
        try:
            if workflow_schedule is None:
                # Default: daily at 6am
                workflow_schedule = ScheduleConfig(
                    frequency="daily",
                    hour=6,
                    minute=0,
                )

            self.workflow_scheduler.start(workflow_schedule)
            logger.info(f"✅ Workflow Scheduler started: {workflow_schedule}")
        except Exception as e:
            logger.error(f"❌ Failed to start workflow scheduler: {e}")

        logger.info("✅ All background schedulers started!")

    def stop_background_schedulers(self) -> None:
        """Stop background schedulers."""
        logger.info("⏹️  Stopping background schedulers...")

        try:
            self.hook_scheduler.stop()
            logger.info("✅ Hook Scheduler stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping hook scheduler: {e}")

        try:
            self.workflow_scheduler.stop()
            logger.info("✅ Workflow Scheduler stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping workflow scheduler: {e}")

        logger.info("✅ All background schedulers stopped")

    def get_status(self) -> dict[str, Any]:
        """Get current system status.

        Returns:
            Dictionary with status of hooks, workflow, schedulers
        """
        return {
            "integration": "ready",
            "hooks_loaded": len(self.hook_orchestrator.hooks),
            "handlers_registered": len(self.hook_orchestrator._handlers),
            "hook_scheduler_running": self.hook_scheduler.running,
            "workflow_scheduler_running": self.workflow_scheduler.running,
            "timestamp": datetime.now().isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"KGCIntegration("
            f"hooks={len(self.hook_orchestrator.hooks)}, "
            f"handlers={len(self.hook_orchestrator._handlers)}"
            f")"
        )


__all__ = [
    "KGCIntegration",
]
