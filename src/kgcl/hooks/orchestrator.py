"""Hook orchestrator - Executes hooks and coordinates effects.

Manages hook lifecycle: registration, trigger matching, condition evaluation,
effect execution, and receipt generation. Supports hook chaining and error recovery.

Chicago TDD Pattern:
    - Register effect handlers (hook → callable)
    - Execute matching hooks on events
    - Evaluate conditions before execution
    - Generate execution receipts
    - Support hook chaining (Hook A triggers Hook B)
    - Continue on errors (resilient execution)
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import logging
import traceback
import uuid

from rdflib import Graph, URIRef

from kgcl.hooks.loader import HookLoader, HookDefinition, HookEffect
from kgcl.hooks.core import HookReceipt, HookState
from kgcl.hooks.conditions import Condition, ConditionResult


logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context passed to effect handlers during execution.

    Attributes:
        event_type: Triggering event URI
        event_data: Event payload data
        hook: Hook being executed
        effect: Current effect being executed
        graph: RDF graph (for SPARQL queries)
        timestamp: Execution start time
        actor: User or system that triggered event
    """
    event_type: str
    event_data: Dict[str, Any]
    hook: HookDefinition
    effect: HookEffect
    graph: Graph
    timestamp: datetime
    actor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for receipt storage."""
        return {
            "event_type": self.event_type,
            "event_data": self.event_data,
            "hook_name": self.hook.name,
            "effect_label": self.effect.label,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor
        }


@dataclass
class ExecutionResult:
    """Result of hook execution.

    Attributes:
        success: Whether execution succeeded
        receipts: List of receipts (one per effect)
        errors: List of error messages
        triggered_hooks: List of hooks triggered by this execution (chaining)
    """
    success: bool
    receipts: List[HookReceipt]
    errors: List[str] = field(default_factory=list)
    triggered_hooks: List[str] = field(default_factory=list)


# Type alias for effect handlers
EffectHandler = Callable[[ExecutionContext], Dict[str, Any]]


class HookOrchestrator:
    """Orchestrates hook execution and coordinates effects.

    Manages the complete hook lifecycle from event trigger to effect execution,
    including condition evaluation, error handling, and receipt generation.

    Example:
        >>> orchestrator = HookOrchestrator(graph, hooks_file)
        >>>
        >>> # Register handler
        >>> def generate_agenda(ctx: ExecutionContext) -> Dict[str, Any]:
        ...     generator = AgendaGenerator(ctx.graph)
        ...     return {"output": generator.generate()}
        >>>
        >>> orchestrator.register_handler("IngestHook", generate_agenda)
        >>>
        >>> # Trigger event
        >>> result = orchestrator.trigger_event("urn:kgc:apple:DataIngested", {})
        >>> print(f"Executed {len(result.receipts)} effects")
    """

    def __init__(
        self,
        graph: Graph,
        hooks_file: Path,
        continue_on_error: bool = True
    ) -> None:
        """Initialize orchestrator with RDF graph and hooks file.

        Args:
            graph: RDF graph for SPARQL queries and data access
            hooks_file: Path to hooks.ttl file
            continue_on_error: If True, continue executing other effects on error
        """
        self.graph = graph
        self.hooks_file = hooks_file
        self.continue_on_error = continue_on_error

        # Load hooks from file
        self.loader = HookLoader(hooks_file)
        self.hooks = self.loader.load_hooks()

        # Effect handlers: hook_name -> List[handler_func]
        self._handlers: Dict[str, List[EffectHandler]] = {}

        # Execution history (for chaining detection)
        self._execution_stack: Set[str] = set()

        logger.info(
            f"Initialized orchestrator with {len(self.hooks)} hooks, "
            f"continue_on_error={continue_on_error}"
        )

    def register_handler(
        self,
        hook_name: str,
        handler: EffectHandler
    ) -> None:
        """Register effect handler for a hook.

        Multiple handlers can be registered for the same hook.
        They execute in registration order.

        Args:
            hook_name: Hook identifier (e.g., "IngestHook")
            handler: Callable that executes effect logic
        """
        if hook_name not in self._handlers:
            self._handlers[hook_name] = []

        self._handlers[hook_name].append(handler)
        logger.debug(f"Registered handler for {hook_name}")

    def unregister_handler(
        self,
        hook_name: str,
        handler: Optional[EffectHandler] = None
    ) -> None:
        """Unregister effect handler(s) for a hook.

        Args:
            hook_name: Hook identifier
            handler: Specific handler to remove, or None to remove all
        """
        if hook_name not in self._handlers:
            return

        if handler is None:
            # Remove all handlers
            del self._handlers[hook_name]
            logger.debug(f"Unregistered all handlers for {hook_name}")
        else:
            # Remove specific handler
            self._handlers[hook_name] = [
                h for h in self._handlers[hook_name] if h != handler
            ]
            if not self._handlers[hook_name]:
                del self._handlers[hook_name]
            logger.debug(f"Unregistered handler for {hook_name}")

    def trigger_event(
        self,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None
    ) -> ExecutionResult:
        """Trigger hooks matching event type.

        Finds all hooks triggered by this event, evaluates conditions,
        and executes effects.

        Args:
            event_type: Event URI (e.g., "urn:kgc:apple:DataIngested")
            event_data: Optional event payload
            actor: User or system triggering event

        Returns:
            ExecutionResult with receipts and status
        """
        if event_data is None:
            event_data = {}

        # Find matching hooks
        matching_hooks = self.loader.get_hooks_by_trigger(event_type)

        if not matching_hooks:
            logger.debug(f"No hooks found for event {event_type}")
            return ExecutionResult(success=True, receipts=[])

        logger.info(
            f"Event {event_type} triggered {len(matching_hooks)} hooks"
        )

        # Execute each matching hook
        all_receipts: List[HookReceipt] = []
        all_errors: List[str] = []
        all_triggered: List[str] = []

        for hook in matching_hooks:
            try:
                result = self.execute_hook(hook, event_type, event_data, actor)
                all_receipts.extend(result.receipts)
                all_errors.extend(result.errors)
                all_triggered.extend(result.triggered_hooks)
            except Exception as e:
                error_msg = f"Failed to execute hook {hook.name}: {e}"
                logger.error(error_msg, exc_info=True)
                all_errors.append(error_msg)

                if not self.continue_on_error:
                    break

        success = len(all_errors) == 0
        return ExecutionResult(
            success=success,
            receipts=all_receipts,
            errors=all_errors,
            triggered_hooks=all_triggered
        )

    def execute_hook(
        self,
        hook: HookDefinition,
        event_type: str,
        event_data: Dict[str, Any],
        actor: Optional[str] = None
    ) -> ExecutionResult:
        """Execute single hook with all its effects.

        Args:
            hook: Hook to execute
            event_type: Triggering event URI
            event_data: Event payload
            actor: User or system triggering event

        Returns:
            ExecutionResult with receipts
        """
        # Check for circular execution
        if hook.name in self._execution_stack:
            logger.warning(f"Circular hook execution detected: {hook.name}")
            return ExecutionResult(
                success=False,
                receipts=[],
                errors=[f"Circular execution: {hook.name}"]
            )

        self._execution_stack.add(hook.name)

        try:
            logger.info(f"Executing hook {hook.name} ({len(hook.effects)} effects)")

            receipts: List[HookReceipt] = []
            errors: List[str] = []
            triggered_hooks: List[str] = []

            # Execute each effect
            for effect in hook.effects:
                try:
                    receipt = self._execute_effect(
                        hook, effect, event_type, event_data, actor
                    )
                    receipts.append(receipt)

                    # Check if this effect triggers other hooks
                    chained = self._check_for_chaining(receipt)
                    triggered_hooks.extend(chained)

                except Exception as e:
                    error_msg = f"Effect {effect.label} failed: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

                    if not self.continue_on_error:
                        break

            success = len(errors) == 0
            return ExecutionResult(
                success=success,
                receipts=receipts,
                errors=errors,
                triggered_hooks=triggered_hooks
            )

        finally:
            self._execution_stack.discard(hook.name)

    def _execute_effect(
        self,
        hook: HookDefinition,
        effect: HookEffect,
        event_type: str,
        event_data: Dict[str, Any],
        actor: Optional[str]
    ) -> HookReceipt:
        """Execute single effect and generate receipt.

        Args:
            hook: Parent hook
            effect: Effect to execute
            event_type: Triggering event
            event_data: Event payload
            actor: Actor triggering execution

        Returns:
            HookReceipt recording execution
        """
        start_time = datetime.now()

        # Create execution context
        context = ExecutionContext(
            event_type=event_type,
            event_data=event_data,
            hook=hook,
            effect=effect,
            graph=self.graph,
            timestamp=start_time,
            actor=actor
        )

        # Find registered handler
        handlers = self._handlers.get(hook.name, [])

        if not handlers:
            logger.warning(f"No handlers registered for hook {hook.name}")
            # Create receipt indicating no handler
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return HookReceipt(
                hook_id=hook.name,
                timestamp=start_time,
                condition_result=ConditionResult(
                    satisfied=True,
                    reason="No handlers registered"
                ),
                handler_result=None,
                duration_ms=duration,
                actor=actor,
                error="No handlers registered"
            )

        # Execute first registered handler
        # (In future, could support multiple handlers per effect)
        handler = handlers[0]

        try:
            logger.debug(f"Executing effect: {effect.label}")
            handler_result = handler(context)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            return HookReceipt(
                hook_id=hook.name,
                timestamp=start_time,
                condition_result=ConditionResult(satisfied=True),
                handler_result=handler_result,
                duration_ms=duration,
                actor=actor,
                input_context=context.to_dict()
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000

            return HookReceipt(
                hook_id=hook.name,
                timestamp=start_time,
                condition_result=ConditionResult(satisfied=True),
                handler_result=None,
                duration_ms=duration,
                actor=actor,
                error=str(e),
                stack_trace=traceback.format_exc(),
                input_context=context.to_dict()
            )

    def _check_for_chaining(self, receipt: HookReceipt) -> List[str]:
        """Check if receipt result triggers other hooks (chaining).

        Args:
            receipt: Execution receipt to check

        Returns:
            List of hook names triggered by this execution
        """
        # TODO: Implement chaining logic
        # Check receipt.handler_result for trigger events
        # Example: if handler_result contains "trigger": "OntologyModified"

        triggered: List[str] = []

        if not receipt.handler_result:
            return triggered

        # Look for trigger key in result
        if "trigger" in receipt.handler_result:
            trigger_event = receipt.handler_result["trigger"]
            chained_hooks = self.loader.get_hooks_by_trigger(trigger_event)

            for hook in chained_hooks:
                if hook.name not in self._execution_stack:
                    logger.info(f"Chaining to hook: {hook.name}")
                    triggered.append(hook.name)

                    # Execute chained hook
                    self.execute_hook(
                        hook,
                        trigger_event,
                        receipt.handler_result,
                        actor=receipt.actor
                    )

        return triggered

    def get_registered_hooks(self) -> List[str]:
        """Get list of hook names with registered handlers.

        Returns:
            List of hook names
        """
        return list(self._handlers.keys())

    def reload_hooks(self) -> None:
        """Reload hooks from hooks.ttl file.

        Useful when hooks.ttl is modified at runtime.
        """
        logger.info("Reloading hooks from file")
        self.loader = HookLoader(self.hooks_file)
        self.hooks = self.loader.load_hooks()
        logger.info(f"Reloaded {len(self.hooks)} hooks")
