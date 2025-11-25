"""Hook registry - Central hook discovery and lifecycle management.

Provides unified interface for querying hooks by trigger, effect, or name.
Manages hook activation/deactivation and validation.

Chicago TDD Pattern:
    - Central hook discovery
    - Query by trigger type
    - Query by effect type
    - Lifecycle management (activate/deactivate)
    - Validation before registration
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from rdflib import Graph

from kgcl.hooks.loader import HookDefinition, HookLoader

logger = logging.getLogger(__name__)


class HookStatus(Enum):
    """Hook lifecycle status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class RegisteredHook:
    """Hook with registration metadata.

    Attributes
    ----------
        definition: Parsed hook definition
        status: Current lifecycle status
        activation_count: Number of times hook has been activated
        last_execution: Timestamp of last execution
        error_message: Most recent error (if status=ERROR)
    """

    definition: HookDefinition
    status: HookStatus = HookStatus.ACTIVE
    activation_count: int = 0
    last_execution: str | None = None
    error_message: str | None = None


class HookRegistry:
    """Central registry for hook discovery and lifecycle management.

    Provides a unified interface for:
    - Loading hooks from RDF
    - Querying hooks by trigger or effect
    - Managing hook activation state
    - Validating hook definitions

    Example:
        >>> registry = HookRegistry(graph, hooks_file)
        >>>
        >>> # Query hooks
        >>> ingest_hooks = registry.get_hooks_by_trigger("apple:DataIngested")
        >>> print(f"Found {len(ingest_hooks)} ingest hooks")
        >>>
        >>> # Manage lifecycle
        >>> registry.deactivate_hook("ValidationFailureHook")
        >>> active = registry.get_active_hooks()
    """

    def __init__(self, graph: Graph, hooks_file: Path) -> None:
        """Initialize registry with RDF graph and hooks file.

        Args:
            graph: RDF graph for validation queries
            hooks_file: Path to hooks.ttl file
        """
        self.graph = graph
        self.hooks_file = hooks_file

        # Load hooks
        self.loader = HookLoader(hooks_file)

        # Registry: hook_name -> RegisteredHook
        self._registry: dict[str, RegisteredHook] = {}

        # Index by trigger event
        self._trigger_index: dict[str, set[str]] = {}

        # Index by effect generator
        self._effect_index: dict[str, set[str]] = {}

        # Load and index hooks
        self._load_and_index()

        logger.info(f"Registry initialized with {len(self._registry)} hooks")

    def _load_and_index(self) -> None:
        """Load hooks and build indexes."""
        hooks = self.loader.load_hooks()

        for hook in hooks:
            # Register hook
            registered = RegisteredHook(definition=hook)
            self._registry[hook.name] = registered

            # Index by trigger
            if hook.trigger_event:
                trigger_key = str(hook.trigger_event)
                if trigger_key not in self._trigger_index:
                    self._trigger_index[trigger_key] = set()
                self._trigger_index[trigger_key].add(hook.name)

            # Index by effect generator
            for effect in hook.effects:
                if effect.generator:
                    if effect.generator not in self._effect_index:
                        self._effect_index[effect.generator] = set()
                    self._effect_index[effect.generator].add(hook.name)

        logger.debug(
            f"Built indexes: {len(self._trigger_index)} triggers, "
            f"{len(self._effect_index)} generators"
        )

    def register_hook(self, hook: HookDefinition) -> None:
        """Register a new hook dynamically.

        Args:
            hook: Hook definition to register

        Raises
        ------
            ValueError: If hook with same name already exists
        """
        if hook.name in self._registry:
            raise ValueError(f"Hook {hook.name} already registered")

        # Validate hook
        self._validate_hook(hook)

        # Register
        registered = RegisteredHook(definition=hook)
        self._registry[hook.name] = registered

        # Update indexes
        if hook.trigger_event:
            trigger_key = str(hook.trigger_event)
            if trigger_key not in self._trigger_index:
                self._trigger_index[trigger_key] = set()
            self._trigger_index[trigger_key].add(hook.name)

        for effect in hook.effects:
            if effect.generator:
                if effect.generator not in self._effect_index:
                    self._effect_index[effect.generator] = set()
                self._effect_index[effect.generator].add(hook.name)

        logger.info(f"Registered hook: {hook.name}")

    def unregister_hook(self, hook_name: str) -> None:
        """Unregister a hook.

        Args:
            hook_name: Name of hook to remove
        """
        if hook_name not in self._registry:
            logger.warning(f"Hook {hook_name} not found in registry")
            return

        hook = self._registry[hook_name].definition

        # Remove from indexes
        if hook.trigger_event:
            trigger_key = str(hook.trigger_event)
            if trigger_key in self._trigger_index:
                self._trigger_index[trigger_key].discard(hook_name)

        for effect in hook.effects:
            if effect.generator and effect.generator in self._effect_index:
                self._effect_index[effect.generator].discard(hook_name)

        # Remove from registry
        del self._registry[hook_name]

        logger.info(f"Unregistered hook: {hook_name}")

    def get_hook(self, hook_name: str) -> RegisteredHook | None:
        """Get registered hook by name.

        Args:
            hook_name: Hook name

        Returns
        -------
            RegisteredHook or None
        """
        return self._registry.get(hook_name)

    def get_hooks_by_trigger(self, trigger_event: str) -> list[RegisteredHook]:
        """Get all hooks triggered by specific event.

        Args:
            trigger_event: Event URI (e.g., "urn:kgc:apple:DataIngested")

        Returns
        -------
            List of matching active hooks
        """
        # Normalize trigger event (handle with/without urn: prefix)
        if not trigger_event.startswith("urn:"):
            # Try both with and without namespace
            candidates = [f"urn:kgc:apple:{trigger_event}", trigger_event]
        else:
            candidates = [trigger_event]

        hooks: list[RegisteredHook] = []

        for candidate in candidates:
            hook_names = self._trigger_index.get(candidate, set())
            for name in hook_names:
                hook = self._registry[name]
                if hook.status == HookStatus.ACTIVE:
                    hooks.append(hook)

        return hooks

    def get_hooks_by_generator(self, generator_name: str) -> list[RegisteredHook]:
        """Get all hooks using specific generator.

        Args:
            generator_name: Generator class name (e.g., "AgendaGenerator")

        Returns
        -------
            List of matching hooks
        """
        hook_names = self._effect_index.get(generator_name, set())
        return [self._registry[name] for name in hook_names]

    def get_active_hooks(self) -> list[RegisteredHook]:
        """Get all active hooks.

        Returns
        -------
            List of hooks with status=ACTIVE
        """
        return [h for h in self._registry.values() if h.status == HookStatus.ACTIVE]

    def get_timed_hooks(self) -> list[RegisteredHook]:
        """Get all hooks with cron schedules.

        Returns
        -------
            List of active timed hooks
        """
        return [
            h
            for h in self._registry.values()
            if h.definition.cron_schedule and h.status == HookStatus.ACTIVE
        ]

    def activate_hook(self, hook_name: str) -> None:
        """Activate a hook.

        Args:
            hook_name: Hook to activate
        """
        if hook_name not in self._registry:
            logger.warning(f"Hook {hook_name} not found")
            return

        hook = self._registry[hook_name]
        hook.status = HookStatus.ACTIVE
        hook.activation_count += 1

        logger.info(f"Activated hook: {hook_name}")

    def deactivate_hook(self, hook_name: str) -> None:
        """Deactivate a hook.

        Args:
            hook_name: Hook to deactivate
        """
        if hook_name not in self._registry:
            logger.warning(f"Hook {hook_name} not found")
            return

        hook = self._registry[hook_name]
        hook.status = HookStatus.INACTIVE

        logger.info(f"Deactivated hook: {hook_name}")

    def mark_hook_error(self, hook_name: str, error: str) -> None:
        """Mark hook as errored.

        Args:
            hook_name: Hook that failed
            error: Error message
        """
        if hook_name not in self._registry:
            return

        hook = self._registry[hook_name]
        hook.status = HookStatus.ERROR
        hook.error_message = error

        logger.error(f"Hook {hook_name} marked as error: {error}")

    def clear_hook_error(self, hook_name: str) -> None:
        """Clear error status and reactivate hook.

        Args:
            hook_name: Hook to clear error for
        """
        if hook_name not in self._registry:
            return

        hook = self._registry[hook_name]
        if hook.status == HookStatus.ERROR:
            hook.status = HookStatus.ACTIVE
            hook.error_message = None
            logger.info(f"Cleared error for hook: {hook_name}")

    def _validate_hook(self, hook: HookDefinition) -> None:
        """Validate hook definition.

        Args:
            hook: Hook to validate

        Raises
        ------
            ValueError: If hook is invalid
        """
        # Check has trigger
        if not hook.trigger_event and not hook.cron_schedule:
            raise ValueError(f"Hook {hook.name} has no trigger")

        # Check has effects
        if not hook.effects:
            raise ValueError(f"Hook {hook.name} has no effects")

        # Validate each effect
        for effect in hook.effects:
            if not effect.command:
                raise ValueError(f"Effect {effect.label} in hook {hook.name} has no command")

    def reload(self) -> None:
        """Reload hooks from file and rebuild indexes."""
        logger.info("Reloading hooks from file")

        # Clear indexes
        self._registry.clear()
        self._trigger_index.clear()
        self._effect_index.clear()

        # Reload loader
        self.loader = HookLoader(self.hooks_file)

        # Load and index
        self._load_and_index()

        logger.info(f"Reloaded {len(self._registry)} hooks")

    def get_statistics(self) -> dict[str, int]:
        """Get registry statistics.

        Returns
        -------
            Dictionary with counts
        """
        return {
            "total_hooks": len(self._registry),
            "active_hooks": len(
                [h for h in self._registry.values() if h.status == HookStatus.ACTIVE]
            ),
            "inactive_hooks": len(
                [h for h in self._registry.values() if h.status == HookStatus.INACTIVE]
            ),
            "error_hooks": len(
                [h for h in self._registry.values() if h.status == HookStatus.ERROR]
            ),
            "timed_hooks": len(self.get_timed_hooks()),
            "trigger_types": len(self._trigger_index),
            "generator_types": len(self._effect_index),
        }
