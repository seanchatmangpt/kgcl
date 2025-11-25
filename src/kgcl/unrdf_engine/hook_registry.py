"""Persistent hook registry with JSON and RDF storage.

Provides hook persistence, version control, hot reloading, and export capabilities.
Includes PolicyPackManager for UNRDF policy pack management.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opentelemetry import trace
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS

from kgcl.unrdf_engine.hooks import HookPhase, KnowledgeHook

tracer = trace.get_tracer(__name__)

UNRDF = Namespace("http://unrdf.org/ontology/")
HOOK = Namespace("http://unrdf.org/ontology/hook/")


def _parse_semver(version: str) -> tuple[int, int, int]:
    """Parse semantic version string.

    Parameters
    ----------
    version : str
        Version string (e.g., "1.2.3")

    Returns
    -------
    tuple[int, int, int]
        Major, minor, patch version numbers

    Raises
    ------
    ValueError
        If version format is invalid

    """
    parts = version.split(".")
    if len(parts) != 3:
        msg = f"Invalid semantic version: {version}"
        raise ValueError(msg)

    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as e:
        msg = f"Invalid semantic version: {version}"
        raise ValueError(msg) from e


@dataclass
class PolicyPackManifest:
    """Manifest for a policy pack.

    Ported from UNRDF policy-pack.mjs.

    Parameters
    ----------
    name : str
        Policy pack name
    version : str
        Semantic version (e.g., "1.0.0")
    description : str
        Human-readable description
    hooks : list[str]
        Hook IDs/names included in pack
    dependencies : dict[str, str]
        Pack dependencies (name -> version)
    slos : dict[str, float]
        Service Level Objectives (metric -> target value)
    author : str
        Pack author
    created : datetime
        Creation timestamp

    """

    name: str
    version: str
    description: str
    hooks: list[str]
    dependencies: dict[str, str] = field(default_factory=dict)
    slos: dict[str, float] = field(default_factory=dict)
    author: str = ""
    created: datetime = field(default_factory=lambda: datetime.now(UTC))

    def validate(self) -> bool:
        """Verify manifest is valid.

        Returns
        -------
        bool
            True if manifest passes validation

        Examples
        --------
        >>> manifest = PolicyPackManifest(
        ...     name="my-pack", version="1.0.0", description="Test pack", hooks=["hook1"]
        ... )
        >>> manifest.validate()
        True

        """
        if not self.name or not self.version or not self.description:
            return False

        # Validate semantic versioning
        try:
            _parse_semver(self.version)
        except ValueError:
            return False

        return len(self.hooks) > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict.

        Returns
        -------
        dict[str, Any]
            Manifest as dictionary

        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "hooks": self.hooks,
            "dependencies": self.dependencies,
            "slos": self.slos,
            "author": self.author,
            "created": self.created.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyPackManifest:
        """Deserialize from dict.

        Parameters
        ----------
        data : dict[str, Any]
            Manifest data

        Returns
        -------
        PolicyPackManifest
            Deserialized manifest

        """
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            hooks=data["hooks"],
            dependencies=data.get("dependencies", {}),
            slos=data.get("slos", {}),
            author=data.get("author", ""),
            created=datetime.fromisoformat(data.get("created", datetime.now(UTC).isoformat())),
        )


@dataclass
class PolicyPack:
    """Loaded policy pack with hooks and metadata.

    Parameters
    ----------
    manifest : PolicyPackManifest
        Pack manifest
    hooks : dict[str, KnowledgeHook]
        Hook name -> Hook object mapping
    is_active : bool
        Whether pack is active
    loaded_at : datetime
        Load timestamp

    """

    manifest: PolicyPackManifest
    hooks: dict[str, KnowledgeHook]
    is_active: bool = True
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get_slo_target(self, metric: str) -> float | None:
        """Get SLO target for metric.

        Parameters
        ----------
        metric : str
            Metric name

        Returns
        -------
        float | None
            SLO target value or None if not defined

        """
        return self.manifest.slos.get(metric)

    def validate_slos(self, metrics: dict[str, float]) -> dict[str, bool]:
        """Validate metrics against SLOs.

        Parameters
        ----------
        metrics : dict[str, float]
            Metric name -> value mapping

        Returns
        -------
        dict[str, bool]
            Metric -> compliant (bool) mapping

        Examples
        --------
        >>> pack = PolicyPack(
        ...     manifest=PolicyPackManifest(
        ...         name="test",
        ...         version="1.0.0",
        ...         description="Test",
        ...         hooks=["h1"],
        ...         slos={"latency": 100.0},
        ...     ),
        ...     hooks={},
        ... )
        >>> pack.validate_slos({"latency": 50.0, "throughput": 1000.0})
        {'latency': True, 'throughput': True}

        """
        result = {}
        for metric, value in metrics.items():
            target = self.get_slo_target(metric)
            if target is None:
                result[metric] = True
            else:
                result[metric] = value <= target
        return result


class PolicyPackManager:
    """Manage policy packs and their activation.

    Ported from UNRDF policy-pack.mjs.

    Features:
    - Load policy packs from disk (manifest + hooks)
    - Activate/deactivate packs without deletion
    - SLO monitoring
    - Dependency validation

    Examples
    --------
    >>> manager = PolicyPackManager(base_path=Path("/packs"), hook_registry=registry)
    >>> pack = manager.load_pack(Path("/packs/my-pack"))
    >>> manager.activate_pack("my-pack")

    """

    def __init__(self, base_path: Path, hook_registry: PersistentHookRegistry) -> None:
        """Initialize manager.

        Parameters
        ----------
        base_path : Path
            Base directory for policy packs
        hook_registry : PersistentHookRegistry
            Hook registry to load hooks from

        """
        self.base_path = Path(base_path)
        self.hook_registry = hook_registry
        self.active_packs: dict[str, PolicyPack] = {}
        self.all_packs: dict[str, PolicyPack] = {}

    def load_pack(self, pack_path: Path) -> PolicyPack:
        """Load and activate a policy pack.

        Parameters
        ----------
        pack_path : Path
            Path to pack directory

        Returns
        -------
        PolicyPack
            Loaded PolicyPack

        Raises
        ------
        ValueError
            If manifest invalid or hooks not found

        """
        manifest_file = pack_path / "manifest.json"
        if not manifest_file.exists():
            msg = f"Manifest not found at {manifest_file}"
            raise ValueError(msg)

        with open(manifest_file) as f:
            manifest_data = json.load(f)

        manifest = PolicyPackManifest.from_dict(manifest_data)
        if not manifest.validate():
            msg = f"Invalid manifest: {manifest_file}"
            raise ValueError(msg)

        # Load hooks
        hooks = {}
        for hook_id in manifest.hooks:
            hook = self.hook_registry.get(hook_id)
            if hook is None:
                msg = f"Hook not found: {hook_id}"
                raise ValueError(msg)
            hooks[hook_id] = hook

        pack = PolicyPack(manifest=manifest, hooks=hooks)
        self.all_packs[manifest.name] = pack

        if pack.is_active:
            self.active_packs[manifest.name] = pack

        return pack

    def activate_pack(self, pack_name: str) -> bool:
        """Activate a loaded pack.

        Parameters
        ----------
        pack_name : str
            Name of pack to activate

        Returns
        -------
        bool
            True if activated successfully

        """
        if pack_name not in self.all_packs:
            return False

        pack = self.all_packs[pack_name]
        pack.is_active = True
        self.active_packs[pack_name] = pack
        return True

    def deactivate_pack(self, pack_name: str) -> bool:
        """Deactivate a pack (without deletion).

        Parameters
        ----------
        pack_name : str
            Name of pack to deactivate

        Returns
        -------
        bool
            True if deactivated successfully

        """
        if pack_name not in self.all_packs:
            return False

        pack = self.all_packs[pack_name]
        pack.is_active = False
        self.active_packs.pop(pack_name, None)
        return True

    def get_active_hooks(self) -> list[KnowledgeHook]:
        """Get all hooks from active packs.

        Returns
        -------
        list[KnowledgeHook]
            All hooks from active packs

        """
        hooks: list[KnowledgeHook] = []
        for pack in self.active_packs.values():
            hooks.extend(pack.hooks.values())
        return hooks

    def validate_dependencies(self) -> dict[str, bool]:
        """Validate all pack dependencies.

        Returns
        -------
        dict[str, bool]
            Pack name -> valid (bool) mapping

        """
        result = {}
        for pack_name, pack in self.all_packs.items():
            valid = True
            for dep_name, dep_version in pack.manifest.dependencies.items():
                # Check if dependency is loaded
                if dep_name not in self.all_packs:
                    valid = False
                    break
                # Check version compatibility
                dep_pack = self.all_packs[dep_name]
                if not self._versions_compatible(dep_version, dep_pack.manifest.version):
                    valid = False
                    break
            result[pack_name] = valid
        return result

    @staticmethod
    def _versions_compatible(required: str, actual: str) -> bool:
        """Check if versions are compatible.

        Uses simple major.minor matching for compatibility.

        Parameters
        ----------
        required : str
            Required version
        actual : str
            Actual version

        Returns
        -------
        bool
            True if versions are compatible

        """
        try:
            req_major, req_minor, _ = _parse_semver(required)
            act_major, act_minor, _ = _parse_semver(actual)
            # Compatible if major.minor match
            return req_major == act_major and req_minor == act_minor
        except ValueError:
            return False


@dataclass
class HookMetadata:
    """Metadata for registered hooks.

    Parameters
    ----------
    hook_id : str
        Unique hook identifier
    version : int
        Hook version number
    created_at : datetime
        Hook creation timestamp
    updated_at : datetime
        Last update timestamp
    enabled : bool
        Whether hook is enabled
    description : str
        Hook description

    """

    hook_id: str
    version: int
    created_at: datetime
    updated_at: datetime
    enabled: bool
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Metadata as dictionary

        """
        return {
            "hook_id": self.hook_id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "enabled": self.enabled,
            "description": self.description,
        }


class PersistentHookRegistry:
    """Registry for managing hooks with persistence.

    Provides:
    - JSON file-based storage
    - RDF export/import
    - Version control
    - Hot reload capability
    - Hook lifecycle management

    Examples
    --------
    >>> registry = PersistentHookRegistry(storage_path=Path("hooks.json"))
    >>> registry.register(my_hook, description="Validates user data")
    >>> registry.save()
    >>> # Later...
    >>> registry.load()

    """

    def __init__(
        self, storage_path: Path | None = None, auto_save: bool = False, auto_load: bool = True
    ) -> None:
        """Initialize persistent hook registry.

        Parameters
        ----------
        storage_path : Path, optional
            Path to JSON storage file
        auto_save : bool, default=False
            Automatically save after modifications
        auto_load : bool, default=True
            Load hooks on initialization if storage exists

        """
        self.storage_path = storage_path
        self.auto_save = auto_save
        self._hooks: dict[str, KnowledgeHook] = {}
        self._metadata: dict[str, HookMetadata] = {}
        self._hooks_by_phase: dict[HookPhase, list[KnowledgeHook]] = {
            phase: [] for phase in HookPhase
        }

        if auto_load and storage_path and storage_path.exists():
            self.load()

    @tracer.start_as_current_span("hook_registry.register")
    def register(self, hook: KnowledgeHook, description: str = "", version: int = 1) -> str:
        """Register a hook with metadata.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to register
        description : str, default=""
            Hook description
        version : int, default=1
            Hook version number

        Returns
        -------
        str
            Hook identifier

        """
        span = trace.get_current_span()
        span.set_attribute("hook.name", hook.name)
        span.set_attribute("hook.version", version)

        if hook.name in self._hooks:
            # Update existing hook
            self._hooks[hook.name] = hook
            metadata = self._metadata[hook.name]
            metadata.version = version
            metadata.updated_at = datetime.now(UTC)
            metadata.description = description or metadata.description
        else:
            # New hook
            self._hooks[hook.name] = hook
            now = datetime.now(UTC)
            self._metadata[hook.name] = HookMetadata(
                hook_id=hook.name,
                version=version,
                created_at=now,
                updated_at=now,
                enabled=hook.enabled,
                description=description,
            )

            # Index by phase
            for phase in hook.phases:
                self._hooks_by_phase[phase].append(hook)
                # Sort by priority (descending)
                self._hooks_by_phase[phase].sort(key=lambda h: h.priority, reverse=True)

        if self.auto_save:
            self.save()

        return hook.name

    @tracer.start_as_current_span("hook_registry.unregister")
    def unregister(self, hook_id: str) -> None:
        """Unregister a hook.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        """
        if hook_id not in self._hooks:
            msg = f"Hook {hook_id} not found"
            raise ValueError(msg)

        hook = self._hooks[hook_id]

        # Remove from phase indices
        for phase in hook.phases:
            if hook in self._hooks_by_phase[phase]:
                self._hooks_by_phase[phase].remove(hook)

        del self._hooks[hook_id]
        del self._metadata[hook_id]

        if self.auto_save:
            self.save()

    def get(self, hook_id: str) -> KnowledgeHook | None:
        """Get hook by ID.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        Returns
        -------
        KnowledgeHook | None
            Hook instance or None if not found

        """
        return self._hooks.get(hook_id)

    def get_metadata(self, hook_id: str) -> HookMetadata | None:
        """Get hook metadata.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        Returns
        -------
        HookMetadata | None
            Hook metadata or None if not found

        """
        return self._metadata.get(hook_id)

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

    def enable_hook(self, hook_id: str) -> None:
        """Enable a hook.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        """
        if hook_id not in self._hooks:
            msg = f"Hook {hook_id} not found"
            raise ValueError(msg)

        self._hooks[hook_id].enabled = True
        self._metadata[hook_id].enabled = True
        self._metadata[hook_id].updated_at = datetime.now(UTC)

        if self.auto_save:
            self.save()

    def disable_hook(self, hook_id: str) -> None:
        """Disable a hook.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        """
        if hook_id not in self._hooks:
            msg = f"Hook {hook_id} not found"
            raise ValueError(msg)

        self._hooks[hook_id].enabled = False
        self._metadata[hook_id].enabled = False
        self._metadata[hook_id].updated_at = datetime.now(UTC)

        if self.auto_save:
            self.save()

    @tracer.start_as_current_span("hook_registry.save")
    def save(self) -> None:
        """Save hooks to storage file in JSON format."""
        if not self.storage_path:
            msg = "No storage path configured"
            raise ValueError(msg)

        span = trace.get_current_span()
        span.set_attribute("storage.path", str(self.storage_path))
        span.set_attribute("hooks.count", len(self._hooks))

        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize hooks and metadata
        data: dict[str, Any] = {"version": "1.0", "hooks": {}}

        for hook_id, hook in self._hooks.items():
            metadata = self._metadata[hook_id]
            hook_data: dict[str, Any] = data["hooks"]  # type: ignore[assignment]
            hook_data[hook_id] = {
                "metadata": metadata.to_dict(),
                "hook": {
                    "name": hook.name,
                    "phases": [p.value for p in hook.phases],
                    "priority": hook.priority,
                    "enabled": hook.enabled,
                    # Note: trigger conditions and execute logic cannot be serialized
                    # These must be re-registered on load
                },
            }

        with self.storage_path.open("w") as f:
            json.dump(data, f, indent=2)

    @tracer.start_as_current_span("hook_registry.load")
    def load(self) -> None:
        """Load hooks from storage file.

        Note: This loads metadata only. Hook implementations must be
        re-registered separately.
        """
        if not self.storage_path or not self.storage_path.exists():
            return

        span = trace.get_current_span()
        span.set_attribute("storage.path", str(self.storage_path))

        with self.storage_path.open() as f:
            data = json.load(f)

        # Load metadata (actual hooks must be re-registered)
        for hook_id, hook_data in data.get("hooks", {}).items():
            metadata_dict = hook_data.get("metadata", {})
            self._metadata[hook_id] = HookMetadata(
                hook_id=metadata_dict["hook_id"],
                version=metadata_dict["version"],
                created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                updated_at=datetime.fromisoformat(metadata_dict["updated_at"]),
                enabled=metadata_dict["enabled"],
                description=metadata_dict.get("description", ""),
            )

        span.set_attribute("hooks.loaded", len(self._metadata))

    @tracer.start_as_current_span("hook_registry.export_to_rdf")
    def export_to_rdf(self, output_path: Path | None = None) -> Graph:
        """Export hooks to RDF format.

        Parameters
        ----------
        output_path : Path, optional
            Path to save RDF file (Turtle format)

        Returns
        -------
        Graph
            RDF graph containing hook definitions

        """
        span = trace.get_current_span()
        graph = Graph()
        graph.bind("unrdf", UNRDF)
        graph.bind("hook", HOOK)

        for hook_id, hook in self._hooks.items():
            metadata = self._metadata[hook_id]
            hook_uri = HOOK[hook_id]

            # Add hook type
            graph.add((hook_uri, RDF.type, HOOK.KnowledgeHook))

            # Add basic properties
            graph.add((hook_uri, RDFS.label, Literal(hook.name)))
            graph.add((hook_uri, HOOK.priority, Literal(hook.priority)))
            graph.add((hook_uri, HOOK.enabled, Literal(hook.enabled)))

            # Add metadata
            graph.add((hook_uri, HOOK.version, Literal(metadata.version)))
            graph.add((hook_uri, HOOK.createdAt, Literal(metadata.created_at.isoformat())))
            graph.add((hook_uri, HOOK.updatedAt, Literal(metadata.updated_at.isoformat())))

            if metadata.description:
                graph.add((hook_uri, RDFS.comment, Literal(metadata.description)))

            # Add phases
            for phase in hook.phases:
                graph.add((hook_uri, HOOK.phase, Literal(phase.value)))

            # Add trigger condition if present
            if hook.trigger:
                trigger_uri = HOOK[f"{hook_id}_trigger"]
                graph.add((hook_uri, HOOK.trigger, trigger_uri))
                graph.add((trigger_uri, RDF.type, HOOK.TriggerCondition))
                graph.add((trigger_uri, HOOK.pattern, Literal(hook.trigger.pattern)))
                graph.add((trigger_uri, HOOK.checkDelta, Literal(hook.trigger.check_delta)))
                graph.add((trigger_uri, HOOK.minMatches, Literal(hook.trigger.min_matches)))

        span.set_attribute("rdf.triples", len(graph))

        if output_path:
            span.set_attribute("output.path", str(output_path))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            graph.serialize(destination=output_path, format="turtle")

        return graph

    @tracer.start_as_current_span("hook_registry.reload")
    def reload(self) -> None:
        """Hot reload hooks from storage file."""
        span = trace.get_current_span()

        # Clear existing hooks
        old_count = len(self._hooks)
        self._hooks.clear()
        self._metadata.clear()
        for phase in self._hooks_by_phase:
            self._hooks_by_phase[phase].clear()

        # Reload from storage
        self.load()

        span.set_attribute("hooks.old_count", old_count)
        span.set_attribute("hooks.new_count", len(self._hooks))

    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns
        -------
        dict[str, Any]
            Statistics about registered hooks

        """
        enabled_count = sum(1 for h in self._hooks.values() if h.enabled)
        phase_counts = {
            phase.value: len(hooks) for phase, hooks in self._hooks_by_phase.items() if hooks
        }

        return {
            "total_hooks": len(self._hooks),
            "enabled_hooks": enabled_count,
            "disabled_hooks": len(self._hooks) - enabled_count,
            "hooks_by_phase": phase_counts,
            "storage_path": str(self.storage_path) if self.storage_path else None,
        }
