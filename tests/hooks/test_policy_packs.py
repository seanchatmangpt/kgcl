"""Chicago School TDD Tests for Policy Pack Management.

Tests PolicyPackManifest, PolicyPack, and PolicyPackManager without mocks.
Real file I/O and validation.
"""

import json
from datetime import UTC, datetime

import pytest

from kgcl.unrdf_engine.hook_registry import PersistentHookRegistry, PolicyPack, PolicyPackManager, PolicyPackManifest
from kgcl.unrdf_engine.hooks import HookContext, HookPhase, KnowledgeHook


class TestPolicyPackManifest:
    """Test PolicyPackManifest validation and serialization."""

    def test_manifest_validation_success(self):
        """Valid manifest passes validation."""
        manifest = PolicyPackManifest(
            name="test-pack", version="1.0.0", description="Test policy pack", hooks=["hook1", "hook2"]
        )

        assert manifest.validate() is True

    def test_manifest_validation_fails_missing_name(self):
        """Manifest validation fails with empty name."""
        manifest = PolicyPackManifest(name="", version="1.0.0", description="Test", hooks=["hook1"])

        assert manifest.validate() is False

    def test_manifest_validation_fails_missing_version(self):
        """Manifest validation fails with empty version."""
        manifest = PolicyPackManifest(name="test", version="", description="Test", hooks=["hook1"])

        assert manifest.validate() is False

    def test_manifest_validation_fails_invalid_semver(self):
        """Manifest validation fails with invalid semantic version."""
        manifest = PolicyPackManifest(name="test", version="1.0", description="Test", hooks=["hook1"])

        assert manifest.validate() is False

    def test_manifest_validation_fails_no_hooks(self):
        """Manifest validation fails with no hooks."""
        manifest = PolicyPackManifest(name="test", version="1.0.0", description="Test", hooks=[])

        assert manifest.validate() is False

    def test_manifest_serialization_roundtrip(self):
        """Manifest serializes and deserializes correctly."""
        original = PolicyPackManifest(
            name="test-pack",
            version="1.2.3",
            description="Test policy pack",
            hooks=["hook1", "hook2"],
            dependencies={"dep1": "1.0.0"},
            slos={"latency": 100.0},
            author="Test Author",
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = PolicyPackManifest.from_dict(data)

        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.description == original.description
        assert restored.hooks == original.hooks
        assert restored.dependencies == original.dependencies
        assert restored.slos == original.slos
        assert restored.author == original.author


class TestPolicyPack:
    """Test PolicyPack SLO validation."""

    def test_get_slo_target_exists(self):
        """Get SLO target returns value when defined."""
        manifest = PolicyPackManifest(
            name="test", version="1.0.0", description="Test", hooks=["h1"], slos={"latency": 100.0}
        )
        pack = PolicyPack(manifest=manifest, hooks={})

        assert pack.get_slo_target("latency") == 100.0

    def test_get_slo_target_missing(self):
        """Get SLO target returns None when not defined."""
        manifest = PolicyPackManifest(name="test", version="1.0.0", description="Test", hooks=["h1"])
        pack = PolicyPack(manifest=manifest, hooks={})

        assert pack.get_slo_target("latency") is None

    def test_validate_slos_all_compliant(self):
        """Validate SLOs returns True for compliant metrics."""
        manifest = PolicyPackManifest(
            name="test", version="1.0.0", description="Test", hooks=["h1"], slos={"latency": 100.0, "error_rate": 0.01}
        )
        pack = PolicyPack(manifest=manifest, hooks={})

        result = pack.validate_slos({"latency": 50.0, "error_rate": 0.005})

        assert result["latency"] is True
        assert result["error_rate"] is True

    def test_validate_slos_non_compliant(self):
        """Validate SLOs returns False for non-compliant metrics."""
        manifest = PolicyPackManifest(
            name="test", version="1.0.0", description="Test", hooks=["h1"], slos={"latency": 100.0}
        )
        pack = PolicyPack(manifest=manifest, hooks={})

        result = pack.validate_slos({"latency": 150.0})

        assert result["latency"] is False

    def test_validate_slos_undefined_metrics_pass(self):
        """Validate SLOs treats undefined metrics as compliant."""
        manifest = PolicyPackManifest(
            name="test", version="1.0.0", description="Test", hooks=["h1"], slos={"latency": 100.0}
        )
        pack = PolicyPack(manifest=manifest, hooks={})

        result = pack.validate_slos({"throughput": 1000.0})

        assert result["throughput"] is True


class TestPolicyPackManager:
    """Test PolicyPackManager lifecycle and validation."""

    @pytest.fixture
    def hook_registry(self):
        """Create hook registry with test hooks."""
        registry = PersistentHookRegistry()

        # Create concrete hook implementations
        class TestHook1(KnowledgeHook):
            """Test hook 1."""

            def execute(self, context: HookContext) -> dict:
                """Execute hook."""
                return {"result": "executed"}

        class TestHook2(KnowledgeHook):
            """Test hook 2."""

            def execute(self, context: HookContext) -> dict:
                """Execute hook."""
                return {"result": "executed"}

        # Register test hooks
        hook1 = TestHook1(name="test-hook-1", phases=[HookPhase.PRE_QUERY], priority=50, trigger=None)
        hook2 = TestHook2(name="test-hook-2", phases=[HookPhase.POST_QUERY], priority=60, trigger=None)

        registry.register(hook1)
        registry.register(hook2)

        return registry

    @pytest.fixture
    def pack_dir(self, tmp_path):
        """Create temporary pack directory with manifest."""
        pack_path = tmp_path / "test-pack"
        pack_path.mkdir()

        manifest = {
            "name": "test-pack",
            "version": "1.0.0",
            "description": "Test policy pack",
            "hooks": ["test-hook-1", "test-hook-2"],
            "dependencies": {},
            "slos": {"latency": 100.0},
            "author": "Test Author",
            "created": datetime.now(UTC).isoformat(),
        }

        with open(pack_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        return pack_path

    def test_load_pack_success(self, tmp_path, hook_registry, pack_dir):
        """Load pack successfully with valid manifest and hooks."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)

        pack = manager.load_pack(pack_dir)

        assert pack.manifest.name == "test-pack"
        assert pack.manifest.version == "1.0.0"
        assert len(pack.hooks) == 2
        assert "test-hook-1" in pack.hooks
        assert "test-hook-2" in pack.hooks
        assert pack.is_active is True

    def test_load_pack_fails_missing_manifest(self, tmp_path, hook_registry):
        """Load pack fails when manifest file missing."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)
        invalid_pack = tmp_path / "invalid-pack"
        invalid_pack.mkdir()

        with pytest.raises(ValueError, match="Manifest not found"):
            manager.load_pack(invalid_pack)

    def test_load_pack_fails_missing_hook(self, tmp_path, hook_registry):
        """Load pack fails when referenced hook not in registry."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)

        pack_path = tmp_path / "bad-pack"
        pack_path.mkdir()

        manifest = {
            "name": "bad-pack",
            "version": "1.0.0",
            "description": "Pack with missing hook",
            "hooks": ["missing-hook"],
        }

        with open(pack_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        with pytest.raises(ValueError, match="Hook not found"):
            manager.load_pack(pack_path)

    def test_activate_pack(self, tmp_path, hook_registry, pack_dir):
        """Activate loaded pack."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)
        pack = manager.load_pack(pack_dir)

        # Deactivate first
        pack.is_active = False
        manager.active_packs.pop("test-pack", None)

        # Then activate
        result = manager.activate_pack("test-pack")

        assert result is True
        assert "test-pack" in manager.active_packs
        assert manager.active_packs["test-pack"].is_active is True

    def test_deactivate_pack(self, tmp_path, hook_registry, pack_dir):
        """Deactivate loaded pack."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)
        manager.load_pack(pack_dir)

        result = manager.deactivate_pack("test-pack")

        assert result is True
        assert "test-pack" not in manager.active_packs
        assert manager.all_packs["test-pack"].is_active is False

    def test_get_active_hooks(self, tmp_path, hook_registry, pack_dir):
        """Get all hooks from active packs."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)
        manager.load_pack(pack_dir)

        hooks = manager.get_active_hooks()

        assert len(hooks) == 2
        hook_names = {h.name for h in hooks}
        assert "test-hook-1" in hook_names
        assert "test-hook-2" in hook_names

    def test_validate_dependencies_success(self, tmp_path, hook_registry):
        """Validate dependencies when all satisfied."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)

        # Create dependency pack
        dep_pack_path = tmp_path / "dep-pack"
        dep_pack_path.mkdir()
        dep_manifest = {
            "name": "dep-pack",
            "version": "1.0.0",
            "description": "Dependency pack",
            "hooks": ["test-hook-1"],
        }
        with open(dep_pack_path / "manifest.json", "w") as f:
            json.dump(dep_manifest, f)

        # Create dependent pack
        main_pack_path = tmp_path / "main-pack"
        main_pack_path.mkdir()
        main_manifest = {
            "name": "main-pack",
            "version": "1.0.0",
            "description": "Main pack",
            "hooks": ["test-hook-2"],
            "dependencies": {"dep-pack": "1.0.0"},
        }
        with open(main_pack_path / "manifest.json", "w") as f:
            json.dump(main_manifest, f)

        # Load both packs
        manager.load_pack(dep_pack_path)
        manager.load_pack(main_pack_path)

        result = manager.validate_dependencies()

        assert result["dep-pack"] is True
        assert result["main-pack"] is True

    def test_validate_dependencies_fails_missing_dependency(self, tmp_path, hook_registry):
        """Validate dependencies fails when dependency missing."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)

        # Create pack with missing dependency
        pack_path = tmp_path / "pack"
        pack_path.mkdir()
        manifest = {
            "name": "pack",
            "version": "1.0.0",
            "description": "Pack with missing dep",
            "hooks": ["test-hook-1"],
            "dependencies": {"missing-pack": "1.0.0"},
        }
        with open(pack_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        manager.load_pack(pack_path)

        result = manager.validate_dependencies()

        assert result["pack"] is False

    def test_validate_dependencies_fails_version_mismatch(self, tmp_path, hook_registry):
        """Validate dependencies fails when version incompatible."""
        manager = PolicyPackManager(base_path=tmp_path, hook_registry=hook_registry)

        # Create dependency pack v1.0
        dep_pack_path = tmp_path / "dep-pack"
        dep_pack_path.mkdir()
        dep_manifest = {"name": "dep-pack", "version": "1.0.0", "description": "Dependency", "hooks": ["test-hook-1"]}
        with open(dep_pack_path / "manifest.json", "w") as f:
            json.dump(dep_manifest, f)

        # Create pack requiring v2.0
        main_pack_path = tmp_path / "main-pack"
        main_pack_path.mkdir()
        main_manifest = {
            "name": "main-pack",
            "version": "1.0.0",
            "description": "Main",
            "hooks": ["test-hook-2"],
            "dependencies": {"dep-pack": "2.0.0"},  # Incompatible
        }
        with open(main_pack_path / "manifest.json", "w") as f:
            json.dump(main_manifest, f)

        manager.load_pack(dep_pack_path)
        manager.load_pack(main_pack_path)

        result = manager.validate_dependencies()

        assert result["main-pack"] is False
