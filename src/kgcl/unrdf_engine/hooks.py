"""Knowledge hooks system for the UNRDF engine.

Provides lifecycle hooks for RDF ingestion and modification with trigger conditions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from opentelemetry import trace
from rdflib import Graph

tracer = trace.get_tracer(__name__)


class HookPhase(Enum):
    """Lifecycle phases for knowledge hooks."""

    PRE_INGESTION = "pre_ingestion"  # Before data enters the graph
    ON_CHANGE = "on_change"  # When graph changes are detected
    POST_COMMIT = "post_commit"  # After transaction commits
    PRE_VALIDATION = "pre_validation"  # Before SHACL validation
    POST_VALIDATION = "post_validation"  # After SHACL validation
    PRE_TRANSACTION = "pre_transaction"  # Before transaction begins
    POST_TRANSACTION = "post_transaction"  # After transaction committed
    ON_ERROR = "on_error"  # On ingestion/transaction error
    PRE_QUERY = "pre_query"  # Before SPARQL query execution
    POST_QUERY = "post_query"  # After SPARQL query execution


@dataclass
class Receipt:
    """Receipt of hook execution.

    Provides audit trail and proof of hook execution with results.

    Parameters
    ----------
    hook_id : str
        Hook identifier
    phase : HookPhase
        Execution phase
    timestamp : datetime
        Execution timestamp
    success : bool
        Whether hook executed successfully
    duration_ms : float
        Execution duration in milliseconds
    result : Any
        Hook execution result
    error : str | None
        Error message if failed
    metadata : dict[str, Any]
        Additional metadata

    """

    hook_id: str
    phase: HookPhase
    timestamp: datetime
    success: bool
    duration_ms: float
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Receipt as dictionary

        """
        return {
            "hook_id": self.hook_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class HookContext:
    """Context passed to hook execution.

    Parameters
    ----------
    phase : HookPhase
        Current lifecycle phase
    graph : Graph
        RDF graph being modified
    delta : Graph
        Changes being applied (new triples)
    transaction_id : str
        ID of current transaction
    metadata : dict[str, Any]
        Additional context metadata
    receipts : list[Receipt]
        Receipts from previous hook executions

    """

    phase: HookPhase
    graph: Graph
    delta: Graph
    transaction_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    receipts: list[Receipt] = field(default_factory=list)


@dataclass
class TriggerCondition:
    """Condition that triggers hook execution.

    Parameters
    ----------
    pattern : str
        SPARQL pattern to match (e.g., "?s rdf:type unrdf:FeatureTemplate")
    check_delta : bool
        If True, match against delta graph; if False, match against full graph
    min_matches : int
        Minimum number of matches required to trigger

    """

    pattern: str
    check_delta: bool = True
    min_matches: int = 1

    def matches(self, context: HookContext) -> bool:
        """Check if trigger condition is met.

        Parameters
        ----------
        context : HookContext
            Hook execution context

        Returns
        -------
        bool
            True if condition is met

        """
        target_graph = context.delta if self.check_delta else context.graph

        # Execute SPARQL query to count matches
        query = f"""
        SELECT (COUNT(?s) as ?count) WHERE {{
            {self.pattern}
        }}
        """

        results = list(target_graph.query(query))
        if not results:
            return False

        count = int(results[0][0])
        return count >= self.min_matches


class KnowledgeHook(ABC):
    """Base class for knowledge hooks.

    Hooks are callbacks triggered at specific lifecycle phases with optional
    trigger conditions.

    Examples
    --------
    >>> class FeatureTemplateHook(KnowledgeHook):
    ...     def __init__(self):
    ...         super().__init__(
    ...             name="feature_template_processor",
    ...             phases=[HookPhase.POST_COMMIT],
    ...             trigger=TriggerCondition(pattern="?s rdf:type unrdf:FeatureTemplate"),
    ...         )
    ...
    ...     def execute(self, context):
    ...         # Process feature templates
    ...         pass

    """

    def __init__(
        self,
        name: str,
        phases: list[HookPhase],
        trigger: TriggerCondition | None = None,
        priority: int = 0,
        enabled: bool = True,
    ) -> None:
        """Initialize hook.

        Parameters
        ----------
        name : str
            Unique hook identifier
        phases : list[HookPhase]
            Lifecycle phases when this hook runs
        trigger : TriggerCondition, optional
            Condition that must be met to execute
        priority : int, default=0
            Execution priority (higher runs first)
        enabled : bool, default=True
            Whether hook is currently enabled

        """
        self.name = name
        self.phases = phases
        self.trigger = trigger
        self.priority = priority
        self.enabled = enabled

    def should_execute(self, context: HookContext) -> bool:
        """Determine if hook should execute.

        Parameters
        ----------
        context : HookContext
            Hook execution context

        Returns
        -------
        bool
            True if hook should execute

        """
        if not self.enabled:
            return False

        if context.phase not in self.phases:
            return False

        if self.trigger and not self.trigger.matches(context):
            return False

        return True

    @abstractmethod
    def execute(self, context: HookContext) -> None:
        """Execute the hook logic.

        Parameters
        ----------
        context : HookContext
            Hook execution context

        """


class HookRegistry:
    """Registry for managing knowledge hooks.

    Provides hook registration, lookup, and management capabilities.
    """

    def __init__(self) -> None:
        """Initialize hook registry."""
        self._hooks: dict[str, KnowledgeHook] = {}
        self._hooks_by_phase: dict[HookPhase, list[KnowledgeHook]] = {
            phase: [] for phase in HookPhase
        }

    @tracer.start_as_current_span("hooks.register")
    def register(self, hook: KnowledgeHook) -> None:
        """Register a hook.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to register

        """
        span = trace.get_current_span()
        span.set_attribute("hook.name", hook.name)
        span.set_attribute("hook.phases", ",".join(p.value for p in hook.phases))

        if hook.name in self._hooks:
            msg = f"Hook {hook.name} already registered"
            raise ValueError(msg)

        self._hooks[hook.name] = hook

        # Index by phase
        for phase in hook.phases:
            self._hooks_by_phase[phase].append(hook)
            # Sort by priority (descending)
            self._hooks_by_phase[phase].sort(key=lambda h: h.priority, reverse=True)

    @tracer.start_as_current_span("hooks.unregister")
    def unregister(self, name: str) -> None:
        """Unregister a hook.

        Parameters
        ----------
        name : str
            Hook name to unregister

        """
        if name not in self._hooks:
            msg = f"Hook {name} not found"
            raise ValueError(msg)

        hook = self._hooks[name]

        # Remove from phase indices
        for phase in hook.phases:
            self._hooks_by_phase[phase].remove(hook)

        del self._hooks[name]

    def get(self, name: str) -> KnowledgeHook | None:
        """Get hook by name.

        Parameters
        ----------
        name : str
            Hook name

        Returns
        -------
        KnowledgeHook | None
            Hook instance or None if not found

        """
        return self._hooks.get(name)

    def get_for_phase(self, phase: HookPhase) -> list[KnowledgeHook]:
        """Get all hooks for a specific phase.

        Parameters
        ----------
        phase : HookPhase
            Lifecycle phase

        Returns
        -------
        list[KnowledgeHook]
            Hooks registered for the phase (sorted by priority)

        """
        return self._hooks_by_phase[phase].copy()

    def list_all(self) -> list[KnowledgeHook]:
        """List all registered hooks.

        Returns
        -------
        list[KnowledgeHook]
            All registered hooks

        """
        return list(self._hooks.values())


class HookExecutor:
    """Executor for running hooks at appropriate lifecycle phases.

    Handles hook execution, error handling, and instrumentation.
    """

    def __init__(self, registry: HookRegistry) -> None:
        """Initialize hook executor.

        Parameters
        ----------
        registry : HookRegistry
            Hook registry to use

        """
        self.registry = registry
        self._execution_history: list[dict[str, Any]] = []

    @tracer.start_as_current_span("hooks.execute_phase")
    def execute_phase(
        self, phase: HookPhase, context: HookContext, fail_fast: bool = False
    ) -> list[dict[str, Any]]:
        """Execute all hooks for a specific phase.

        Parameters
        ----------
        phase : HookPhase
            Lifecycle phase to execute
        context : HookContext
            Hook execution context
        fail_fast : bool, default=False
            If True, stop on first hook failure

        Returns
        -------
        list[dict[str, Any]]
            Execution results for each hook

        """
        span = trace.get_current_span()
        span.set_attribute("phase", phase.value)
        span.set_attribute("transaction.id", context.transaction_id)

        hooks = self.registry.get_for_phase(phase)
        results = []

        for hook in hooks:
            result = self._execute_hook(hook, context)
            results.append(result)

            if fail_fast and not result["success"]:
                span.set_attribute("failed_hook", hook.name)
                break

        span.set_attribute("hooks.executed", len(results))
        span.set_attribute("hooks.successful", sum(1 for r in results if r["success"]))

        self._execution_history.extend(results)
        return results

    @tracer.start_as_current_span("hooks.execute_hook")
    def _execute_hook(self, hook: KnowledgeHook, context: HookContext) -> dict[str, Any]:
        """Execute a single hook.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to execute
        context : HookContext
            Execution context

        Returns
        -------
        dict[str, Any]
            Execution result with status and details

        """
        import time

        span = trace.get_current_span()
        span.set_attribute("hook.name", hook.name)
        span.set_attribute("hook.priority", hook.priority)

        start_time = time.perf_counter()
        timestamp = datetime.now(UTC)

        result = {
            "hook": hook.name,
            "phase": context.phase.value,
            "transaction_id": context.transaction_id,
            "success": False,
            "executed": False,
            "error": None,
            "duration_ms": 0.0,
        }

        try:
            if not hook.should_execute(context):
                span.set_attribute("skipped", True)
                result["executed"] = False
                duration_ms = (time.perf_counter() - start_time) * 1000
                result["duration_ms"] = duration_ms

                # Create receipt for skipped hook
                receipt = Receipt(
                    hook_id=hook.name,
                    phase=context.phase,
                    timestamp=timestamp,
                    success=True,
                    duration_ms=duration_ms,
                    metadata={"skipped": True},
                )
                context.receipts.append(receipt)

                return result

            span.set_attribute("executed", True)
            hook.execute(context)

            duration_ms = (time.perf_counter() - start_time) * 1000
            result["success"] = True
            result["executed"] = True
            result["duration_ms"] = duration_ms

            # Create receipt for successful execution
            receipt = Receipt(
                hook_id=hook.name,
                phase=context.phase,
                timestamp=timestamp,
                success=True,
                duration_ms=duration_ms,
            )
            context.receipts.append(receipt)

            # Record performance metrics
            span.set_attribute("hook.duration_ms", duration_ms)
            span.set_attribute("hook.success", True)

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("error", str(e))
            span.set_attribute("hook.duration_ms", duration_ms)
            span.record_exception(e)
            result["error"] = str(e)
            result["duration_ms"] = duration_ms

            # Create receipt for failed execution
            receipt = Receipt(
                hook_id=hook.name,
                phase=context.phase,
                timestamp=timestamp,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            )
            context.receipts.append(receipt)

        return result

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get execution history.

        Returns
        -------
        list[dict[str, Any]]
            All hook execution results

        """
        return self._execution_history.copy()

    def clear_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()


# Predefined hook implementations


class ValidationFailureHook(KnowledgeHook):
    """Hook that triggers on SHACL validation failures.

    Rolls back transaction if validation fails.
    """

    def __init__(self, rollback_on_failure: bool = True) -> None:
        """Initialize validation failure hook.

        Parameters
        ----------
        rollback_on_failure : bool, default=True
            Whether to rollback transaction on validation failure

        """
        super().__init__(
            name="validation_failure_handler",
            phases=[HookPhase.POST_VALIDATION],
            priority=1000,  # High priority
        )
        self.rollback_on_failure = rollback_on_failure

    def execute(self, context: HookContext) -> None:
        """Execute hook - check for validation failures."""
        validation_report = context.metadata.get("validation_report")

        if validation_report and not validation_report.get("conforms", True):
            if self.rollback_on_failure:
                # Signal rollback through metadata
                context.metadata["should_rollback"] = True
                context.metadata["rollback_reason"] = "SHACL validation failed"


class FeatureTemplateHook(KnowledgeHook):
    """Hook that triggers when new FeatureTemplates are added.

    Materializes feature templates by applying them to matching entities.
    """

    def __init__(self, materializer: Callable[[HookContext], None] | None = None) -> None:
        """Initialize feature template hook.

        Parameters
        ----------
        materializer : Callable[[HookContext], None], optional
            Function to materialize features from templates

        """
        super().__init__(
            name="feature_template_materializer",
            phases=[HookPhase.POST_COMMIT],
            trigger=TriggerCondition(
                pattern="?s rdf:type <http://unrdf.org/ontology/FeatureTemplate>",
                check_delta=True,
                min_matches=1,
            ),
        )
        self.materializer = materializer

    def execute(self, context: HookContext) -> None:
        """Execute hook - materialize feature templates."""
        if self.materializer:
            self.materializer(context)
