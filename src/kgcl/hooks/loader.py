"""Hook loader - Parses hooks.ttl and instantiates Hook objects.

Loads hook definitions from RDF, extracting triggers, effects, and metadata
to create executable Hook instances for the orchestrator.

Chicago TDD Pattern:
    - Parse RDF hook definitions
    - Extract trigger events and cron schedules
    - Map effects to generator commands
    - Handle missing/invalid hooks gracefully
    - Return validated Hook domain objects
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS

from kgcl.hooks.value_objects import HookName

logger = logging.getLogger(__name__)

# Define namespaces
KGC = Namespace("urn:kgc:")
APPLE = Namespace("urn:kgc:apple:")


@dataclass
class HookEffect:
    """Single effect (command) that a hook triggers.

    Attributes
    ----------
        label: Human-readable name
        description: Explanation of what this effect does
        command: CLI command to execute (e.g., "kgct generate-agenda")
        target: Output file path or destination
        generator: Name of ProjectionGenerator class to invoke
    """

    label: str
    description: str
    command: str
    target: str
    generator: str | None = None  # Mapped from command


@dataclass
class HookDefinition:
    """Parsed hook definition from hooks.ttl.

    Represents a complete hook with its trigger conditions and effects.

    Attributes
    ----------
        uri: RDF URI of the hook
        name: Hook identifier (e.g., "IngestHook")
        label: Human-readable label
        description: Purpose and behavior
        trigger_event: Event URI that triggers this hook (e.g., apple:DataIngested)
        trigger_label: Human-readable event name
        cron_schedule: Optional cron expression for timed hooks
        effects: List of commands/generators to execute
        waste_removed: Description of manual work eliminated
    """

    uri: URIRef
    name: HookName
    label: str
    description: str
    trigger_event: URIRef | None
    trigger_label: str | None
    cron_schedule: str | None
    effects: list[HookEffect]
    waste_removed: str = ""

    def __post_init__(self) -> None:
        """Validate hook definition after initialization."""
        if not self.trigger_event and not self.cron_schedule:
            raise ValueError(f"Hook {self.name} must have either trigger_event or cron_schedule")
        if not self.effects:
            raise ValueError(f"Hook {self.name} must have at least one effect")


class HookLoader:
    """Loads and parses hook definitions from RDF graph.

    Reads hooks.ttl, extracts hook metadata, triggers, and effects,
    then instantiates Hook domain objects for execution.

    Example:
        >>> loader = HookLoader(Path(".kgc/hooks.ttl"))
        >>> hooks = loader.load_hooks()
        >>> for hook in hooks:
        ...     print(f"{hook.name}: {len(hook.effects)} effects")
    """

    # Mapping from CLI commands to generator classes
    COMMAND_TO_GENERATOR = {
        "kgct generate-agenda": "AgendaGenerator",
        "kgct generate-cli": "CLIGenerator",
        "kgct generate-quality-report": "QualityReportGenerator",
        "kgct detect-conflicts": "ConflictReportGenerator",
        "kgct find-legacy": "StaleItemsGenerator",
        "kgct find-unused-lists": "StaleItemsGenerator",
        "kgct generate-daily-briefing": "AgendaGenerator",
        "kgct generate-priority-matrix": "AgendaGenerator",
        "kgct generate-weekly-summary": "AgendaGenerator",
        "kgct generate-lens": "LensGenerator",
        "kgct generate-diagrams": "DiagramGenerator",
        "kgct generate-docs": "DocumentationGenerator",
    }

    def __init__(self, hooks_file: Path) -> None:
        """Initialize loader with path to hooks.ttl file.

        Args:
            hooks_file: Path to RDF file containing hook definitions

        Raises
        ------
            FileNotFoundError: If hooks file doesn't exist
        """
        if not hooks_file.exists():
            raise FileNotFoundError(f"Hooks file not found: {hooks_file}")

        self.hooks_file = hooks_file
        self.graph = Graph()
        self.graph.parse(str(hooks_file), format="turtle")

        logger.info(f"Loaded hooks graph from {hooks_file} ({len(self.graph)} triples)")

    def load_hooks(self) -> list[HookDefinition]:
        """Load all hook definitions from RDF graph.

        Returns
        -------
            List of parsed HookDefinition objects

        Raises
        ------
            ValueError: If hook definitions are malformed
        """
        hooks: list[HookDefinition] = []

        # Query for all hooks (anything with rdf:type kgc:Hook)
        hook_query = """
        PREFIX kgc: <urn:kgc:>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?hook ?label ?comment
        WHERE {
            ?hook a kgc:Hook .
            ?hook rdfs:label ?label .
            ?hook rdfs:comment ?comment .
        }
        """

        results = self.graph.query(hook_query)

        for row in results:
            hook_uri = row.hook
            try:
                hook = self._parse_hook(hook_uri, str(row.label), str(row.comment))
                hooks.append(hook)
                logger.info(f"Loaded hook: {hook.name} ({len(hook.effects)} effects)")
            except Exception as e:
                logger.error(f"Failed to parse hook {hook_uri}: {e}", exc_info=True)
                # Continue loading other hooks

        if not hooks:
            logger.warning("No hooks found in RDF graph")

        return hooks

    def _parse_hook(self, hook_uri: URIRef, label: str, comment: str) -> HookDefinition:
        """Parse single hook from RDF graph.

        Args:
            hook_uri: URI of the hook node
            label: Human-readable label
            comment: Description

        Returns
        -------
            Parsed HookDefinition

        Raises
        ------
            ValueError: If hook is malformed
        """
        # Extract hook name from URI (e.g., apple:IngestHook -> IngestHook)
        name = str(hook_uri).split(":")[-1]
        hook_name = HookName.new(name)

        # Get trigger event
        trigger_event = self._get_trigger_event(hook_uri)
        trigger_label = self._get_trigger_label(trigger_event) if trigger_event else None

        # Get cron schedule (if any)
        cron_schedule = self._get_cron_schedule(hook_uri)

        # Get effects
        effects = self._parse_effects(hook_uri)

        # Get waste removed
        waste_removed = self._get_waste_removed(hook_uri)

        return HookDefinition(
            uri=hook_uri,
            name=hook_name,
            label=label,
            description=comment,
            trigger_event=trigger_event,
            trigger_label=trigger_label,
            cron_schedule=cron_schedule,
            effects=effects,
            waste_removed=waste_removed,
        )

    def _get_trigger_event(self, hook_uri: URIRef) -> URIRef | None:
        """Extract trigger event URI from hook.

        Args:
            hook_uri: Hook URI

        Returns
        -------
            Event URI or None
        """
        # Direct triggeredBy predicate
        for obj in self.graph.objects(hook_uri, KGC.triggeredBy):
            # Check if it's a direct event URI or a blank node with cronSchedule
            if not isinstance(obj, URIRef):
                # Blank node - check for cron schedule
                continue
            return obj

        return None

    def _get_trigger_label(self, event_uri: URIRef) -> str | None:
        """Get human-readable label for trigger event.

        Args:
            event_uri: Event URI

        Returns
        -------
            Event label or None
        """
        for label in self.graph.objects(event_uri, RDFS.label):
            return str(label)
        return None

    def _get_cron_schedule(self, hook_uri: URIRef) -> str | None:
        """Extract cron schedule from hook (for timed hooks).

        Args:
            hook_uri: Hook URI

        Returns
        -------
            Cron expression string or None
        """
        # Check for triggeredBy blank node with cronSchedule
        for trigger_node in self.graph.objects(hook_uri, KGC.triggeredBy):
            for cron in self.graph.objects(trigger_node, KGC.cronSchedule):
                return str(cron)

        return None

    def _parse_effects(self, hook_uri: URIRef) -> list[HookEffect]:
        """Parse all effects from hook.

        Args:
            hook_uri: Hook URI

        Returns
        -------
            List of HookEffect objects
        """
        effects: list[HookEffect] = []

        for effect_node in self.graph.objects(hook_uri, KGC.effect):
            try:
                effect = self._parse_single_effect(effect_node)
                effects.append(effect)
            except Exception as e:
                logger.error(f"Failed to parse effect for {hook_uri}: {e}")

        return effects

    def _parse_single_effect(self, effect_node) -> HookEffect:
        """Parse single effect from RDF.

        Args:
            effect_node: RDF blank node or URI representing effect

        Returns
        -------
            HookEffect object

        Raises
        ------
            ValueError: If effect is malformed
        """
        label = None
        description = None
        command = None
        target = None

        for pred, obj in self.graph.predicate_objects(effect_node):
            if pred == RDFS.label:
                label = str(obj)
            elif pred == RDFS.comment:
                description = str(obj)
            elif pred == KGC.command:
                command = str(obj)
            elif pred == KGC.target:
                target = str(obj)

        if not all([label, description, command, target]):
            raise ValueError(f"Effect missing required fields: label={label}, command={command}")

        # Map command to generator
        generator = self._map_command_to_generator(command)

        return HookEffect(label=label, description=description, command=command, target=target, generator=generator)

    def _map_command_to_generator(self, command: str) -> str | None:
        """Map CLI command to generator class name.

        Args:
            command: CLI command string

        Returns
        -------
            Generator class name or None
        """
        # Extract base command (ignore flags)
        base_command = " ".join(command.split()[:2])  # "kgct generate-agenda"

        return self.COMMAND_TO_GENERATOR.get(base_command)

    def _get_waste_removed(self, hook_uri: URIRef) -> str:
        """Extract waste removed description.

        Args:
            hook_uri: Hook URI

        Returns
        -------
            Waste removed description or empty string
        """
        for waste in self.graph.objects(hook_uri, KGC.wasteRemoved):
            return str(waste)
        return ""

    def get_hook_by_name(self, name: str | HookName) -> HookDefinition | None:
        """Find hook by name.

        Args:
            name: Hook name (e.g., "IngestHook")

        Returns
        -------
            HookDefinition or None if not found
        """
        target = HookName.ensure(name)
        hooks = self.load_hooks()
        for hook in hooks:
            if hook.name == target:
                return hook
        return None

    def get_hooks_by_trigger(self, event_uri: str) -> list[HookDefinition]:
        """Find all hooks triggered by specific event.

        Args:
            event_uri: Event URI string (e.g., "urn:kgc:apple:DataIngested")

        Returns
        -------
            List of matching hooks
        """
        hooks = self.load_hooks()
        event = URIRef(event_uri)
        return [h for h in hooks if h.trigger_event == event]

    def get_timed_hooks(self) -> list[HookDefinition]:
        """Get all hooks with cron schedules.

        Returns
        -------
            List of hooks with cron_schedule defined
        """
        hooks = self.load_hooks()
        return [h for h in hooks if h.cron_schedule]
