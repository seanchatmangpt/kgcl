"""Hook effect handlers - Wire generators to hooks.

Maps hook effects to generator execution. Each handler:
1. Extracts event data from execution context
2. Instantiates appropriate generator
3. Calls generate() to produce artifacts
4. Returns result dictionary with artifact content

Chicago TDD Pattern:
    - Real generator objects (no mocking)
    - Direct function calls
    - Return artifact content as execution result
"""

import logging
from dataclasses import dataclass
from typing import Any

# Import generators
from kgcl.generators.agenda import AgendaGenerator
from kgcl.generators.conflict import ConflictReportGenerator
from kgcl.generators.quality import QualityReportGenerator
from kgcl.generators.stale import StaleItemsGenerator
from kgcl.hooks.orchestrator import ExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class HandlerResult:
    """Result of a handler execution.

    Attributes
    ----------
        artifact_type: Type of artifact generated (agenda, quality_report, etc)
        artifact_name: Generated file/artifact name
        artifact_content: Full rendered artifact content
        metadata: Additional metadata (item counts, time taken, etc)
    """

    artifact_type: str
    artifact_name: str
    artifact_content: str
    metadata: dict[str, Any]


class HookHandlers:
    """Central registry of hook effect handlers.

    Maps hook effects to generator functions. Each handler is a pure function
    that takes ExecutionContext and returns artifact content.
    """

    @staticmethod
    def generate_agenda(ctx: ExecutionContext) -> dict[str, Any]:
        """Handle IngestHook or DailyReviewHook - generate agenda.

        Args:
            ctx: Execution context with graph, event data, timestamp

        Returns
        -------
            Dictionary with artifact_type, artifact_name, artifact_content, metadata
        """
        try:
            logger.info(f"Generating agenda at {ctx.timestamp}")

            # Instantiate generator
            generator = AgendaGenerator(graph=ctx.graph, start_date=ctx.timestamp)

            # Generate artifact
            artifact_content = generator.generate()

            # Build result
            result = {
                "artifact_type": "agenda",
                "artifact_name": f"agenda_{ctx.timestamp.strftime('%Y%m%d_%H%M%S')}.md",
                "artifact_content": artifact_content,
                "metadata": {
                    "generator": "AgendaGenerator",
                    "triggered_by": ctx.event_type,
                    "generated_at": ctx.timestamp.isoformat(),
                    "lines": len(artifact_content.splitlines()),
                },
            }

            logger.info(f"✅ Agenda generated: {result['artifact_name']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to generate agenda: {e}")
            return {
                "artifact_type": "agenda",
                "artifact_name": None,
                "artifact_content": None,
                "metadata": {"error": str(e)},
            }

    @staticmethod
    def generate_quality_report(ctx: ExecutionContext) -> dict[str, Any]:
        """Handle ValidationFailureHook - generate quality report.

        Args:
            ctx: Execution context with validation results

        Returns
        -------
            Dictionary with quality report artifact
        """
        try:
            logger.info(f"Generating quality report at {ctx.timestamp}")

            # Extract validation graph if provided
            validation_graph = ctx.event_data.get("validation_graph", ctx.graph)

            # Instantiate generator
            generator = QualityReportGenerator(graph=ctx.graph, validation_graph=validation_graph)

            # Generate artifact
            artifact_content = generator.generate()

            # Build result
            result = {
                "artifact_type": "quality_report",
                "artifact_name": f"quality_report_{ctx.timestamp.strftime('%Y%m%d_%H%M%S')}.md",
                "artifact_content": artifact_content,
                "metadata": {
                    "generator": "QualityReportGenerator",
                    "triggered_by": ctx.event_type,
                    "generated_at": ctx.timestamp.isoformat(),
                    "lines": len(artifact_content.splitlines()),
                },
            }

            logger.info(f"✅ Quality report generated: {result['artifact_name']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to generate quality report: {e}")
            return {
                "artifact_type": "quality_report",
                "artifact_name": None,
                "artifact_content": None,
                "metadata": {"error": str(e)},
            }

    @staticmethod
    def generate_conflict_report(ctx: ExecutionContext) -> dict[str, Any]:
        """Handle ConflictDetectionHook - generate conflict report.

        Args:
            ctx: Execution context with calendar data

        Returns
        -------
            Dictionary with conflict report artifact
        """
        try:
            logger.info(f"Generating conflict report at {ctx.timestamp}")

            # Extract lookahead days if provided
            lookahead = ctx.event_data.get("lookahead_days", 7)

            # Instantiate generator
            generator = ConflictReportGenerator(graph=ctx.graph, lookahead_days=lookahead)

            # Generate artifact
            artifact_content = generator.generate()

            # Build result
            result = {
                "artifact_type": "conflict_report",
                "artifact_name": f"conflict_report_{ctx.timestamp.strftime('%Y%m%d_%H%M%S')}.md",
                "artifact_content": artifact_content,
                "metadata": {
                    "generator": "ConflictReportGenerator",
                    "triggered_by": ctx.event_type,
                    "lookahead_days": lookahead,
                    "generated_at": ctx.timestamp.isoformat(),
                    "lines": len(artifact_content.splitlines()),
                },
            }

            logger.info(f"✅ Conflict report generated: {result['artifact_name']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to generate conflict report: {e}")
            return {
                "artifact_type": "conflict_report",
                "artifact_name": None,
                "artifact_content": None,
                "metadata": {"error": str(e)},
            }

    @staticmethod
    def generate_stale_items_report(ctx: ExecutionContext) -> dict[str, Any]:
        """Handle StaleItemHook - generate stale items report.

        Args:
            ctx: Execution context with knowledge base data

        Returns
        -------
            Dictionary with stale items report artifact
        """
        try:
            logger.info(f"Generating stale items report at {ctx.timestamp}")

            # Extract threshold if provided
            threshold = ctx.event_data.get("stale_threshold_days", 30)

            # Instantiate generator
            generator = StaleItemsGenerator(graph=ctx.graph, stale_threshold=threshold)

            # Generate artifact
            artifact_content = generator.generate()

            # Build result
            result = {
                "artifact_type": "stale_items_report",
                "artifact_name": f"stale_items_{ctx.timestamp.strftime('%Y%m%d_%H%M%S')}.md",
                "artifact_content": artifact_content,
                "metadata": {
                    "generator": "StaleItemsGenerator",
                    "triggered_by": ctx.event_type,
                    "stale_threshold_days": threshold,
                    "generated_at": ctx.timestamp.isoformat(),
                    "lines": len(artifact_content.splitlines()),
                },
            }

            logger.info(f"✅ Stale items report generated: {result['artifact_name']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to generate stale items report: {e}")
            return {
                "artifact_type": "stale_items_report",
                "artifact_name": None,
                "artifact_content": None,
                "metadata": {"error": str(e)},
            }

    @staticmethod
    def generate_all_reports(ctx: ExecutionContext) -> dict[str, Any]:
        """Handle OntologyChangeHook - regenerate all reports.

        This handler runs all generators to ensure reports are current when
        the ontology changes (which affects data interpretation).

        Args:
            ctx: Execution context

        Returns
        -------
            Dictionary with all artifacts
        """
        try:
            logger.info(f"Regenerating all reports at {ctx.timestamp}")

            results = {
                "artifact_type": "all_reports",
                "artifacts": {},
                "metadata": {
                    "triggered_by": ctx.event_type,
                    "generated_at": ctx.timestamp.isoformat(),
                    "generators_run": [],
                },
            }

            # Run all generators
            generators = [
                ("agenda", HookHandlers.generate_agenda),
                ("quality_report", HookHandlers.generate_quality_report),
                ("conflict_report", HookHandlers.generate_conflict_report),
                ("stale_items", HookHandlers.generate_stale_items_report),
            ]

            for gen_name, handler in generators:
                try:
                    artifact = handler(ctx)
                    results["artifacts"][gen_name] = artifact
                    results["metadata"]["generators_run"].append(gen_name)
                except Exception as e:
                    logger.warning(f"Error running {gen_name}: {e}")
                    results["artifacts"][gen_name] = {"error": str(e), "artifact_type": gen_name}

            logger.info(f"✅ All reports regenerated: {len(results['metadata']['generators_run'])} generators")
            return results

        except Exception as e:
            logger.error(f"❌ Failed to regenerate all reports: {e}")
            return {"artifact_type": "all_reports", "artifacts": {}, "metadata": {"error": str(e)}}


def register_all_handlers(orchestrator) -> None:
    """Register all generator handlers with orchestrator.

    Maps:
        IngestHook → generate_agenda
        OntologyChangeHook → generate_all_reports
        ValidationFailureHook → generate_quality_report
        ConflictDetectionHook → generate_conflict_report
        StaleItemHook → generate_stale_items_report
        DailyReviewHook → generate_agenda
        WeeklyReviewHook → generate_agenda

    Args:
        orchestrator: HookOrchestrator instance to register handlers with
    """
    handlers = [
        ("IngestHook", HookHandlers.generate_agenda),
        ("OntologyChangeHook", HookHandlers.generate_all_reports),
        ("ValidationFailureHook", HookHandlers.generate_quality_report),
        ("ConflictDetectionHook", HookHandlers.generate_conflict_report),
        ("StaleItemHook", HookHandlers.generate_stale_items_report),
        ("DailyReviewHook", HookHandlers.generate_agenda),
        ("WeeklyReviewHook", HookHandlers.generate_agenda),
    ]

    for hook_name, handler in handlers:
        try:
            orchestrator.register_handler(hook_name, handler)
            logger.info(f"✅ Registered handler: {hook_name}")
        except Exception as e:
            logger.error(f"❌ Failed to register handler {hook_name}: {e}")


__all__ = ["HandlerResult", "HookHandlers", "register_all_handlers"]
