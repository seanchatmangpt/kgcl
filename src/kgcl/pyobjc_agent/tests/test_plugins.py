"""
Unit tests for plugin system.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ..plugins.base import (
    BaseCapabilityPlugin,
    CapabilityDescriptor,
    CapabilityData,
    PluginStatus,
    EntitlementLevel
)
from ..plugins import PluginRegistry, get_registry


class MockPlugin(BaseCapabilityPlugin):
    """Mock plugin for testing."""

    @property
    def plugin_name(self) -> str:
        return "Mock Plugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def required_frameworks(self) -> list:
        return ["Foundation"]

    def discover_capabilities(self) -> list:
        return [
            CapabilityDescriptor(
                name="test_capability",
                description="Test capability",
                framework="Foundation",
                required_entitlement=EntitlementLevel.NONE
            )
        ]

    def check_entitlements(self) -> dict:
        return {"test": True}

    def collect_capability_data(self, capability_name: str, parameters=None):
        return CapabilityData(
            capability_name=capability_name,
            timestamp=datetime.utcnow(),
            data={"test": "data"}
        )


class TestBaseCapabilityPlugin(unittest.TestCase):
    """Test cases for BaseCapabilityPlugin."""

    def setUp(self):
        """Set up test fixtures."""
        self.plugin = MockPlugin(plugin_id="test_plugin")

    def test_initialization(self):
        """Test plugin initialization."""
        self.assertEqual(self.plugin.plugin_id, "test_plugin")
        self.assertEqual(self.plugin.status, PluginStatus.UNINITIALIZED)
        self.assertIsNone(self.plugin._error_message)

    @patch('builtins.__import__')
    def test_initialize_success(self, mock_import):
        """Test successful plugin initialization."""
        mock_import.return_value = MagicMock()

        result = self.plugin.initialize()

        self.assertTrue(result)
        self.assertEqual(self.plugin.status, PluginStatus.READY)
        self.assertIsNotNone(self.plugin._capabilities_cache)

    @patch('builtins.__import__')
    def test_initialize_framework_missing(self, mock_import):
        """Test initialization with missing framework."""
        mock_import.side_effect = ImportError("Framework not found")

        result = self.plugin.initialize()

        self.assertFalse(result)
        self.assertEqual(self.plugin.status, PluginStatus.ERROR)
        self.assertIsNotNone(self.plugin._error_message)

    @patch('builtins.__import__')
    def test_get_capabilities(self, mock_import):
        """Test getting capabilities."""
        mock_import.return_value = MagicMock()
        self.plugin.initialize()

        capabilities = self.plugin.get_capabilities()

        self.assertIsInstance(capabilities, list)
        self.assertEqual(len(capabilities), 1)
        self.assertEqual(capabilities[0].name, "test_capability")

    @patch('builtins.__import__')
    def test_get_capability_by_name(self, mock_import):
        """Test getting specific capability."""
        mock_import.return_value = MagicMock()
        self.plugin.initialize()

        capability = self.plugin.get_capability_by_name("test_capability")

        self.assertIsNotNone(capability)
        self.assertEqual(capability.name, "test_capability")

        # Non-existent capability
        capability = self.plugin.get_capability_by_name("nonexistent")
        self.assertIsNone(capability)

    @patch('builtins.__import__')
    def test_collect_capability_data(self, mock_import):
        """Test collecting capability data."""
        mock_import.return_value = MagicMock()
        self.plugin.initialize()

        data = self.plugin.collect_capability_data("test_capability")

        self.assertIsInstance(data, CapabilityData)
        self.assertEqual(data.capability_name, "test_capability")
        self.assertIsNotNone(data.data)

    @patch('builtins.__import__')
    def test_collect_all_capabilities(self, mock_import):
        """Test collecting all capabilities."""
        mock_import.return_value = MagicMock()
        self.plugin.initialize()

        results = self.plugin.collect_all_capabilities()

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], CapabilityData)

    def test_get_status(self):
        """Test getting plugin status."""
        status = self.plugin.get_status()

        self.assertIsInstance(status, dict)
        self.assertEqual(status["plugin_id"], "test_plugin")
        self.assertEqual(status["plugin_name"], "Mock Plugin")
        self.assertEqual(status["version"], "1.0.0")
        self.assertEqual(status["status"], PluginStatus.UNINITIALIZED.value)

    def test_shutdown(self):
        """Test plugin shutdown."""
        self.plugin.shutdown()
        self.assertEqual(self.plugin.status, PluginStatus.DISABLED)


class TestCapabilityDescriptor(unittest.TestCase):
    """Test cases for CapabilityDescriptor."""

    def test_creation(self):
        """Test descriptor creation."""
        descriptor = CapabilityDescriptor(
            name="test_cap",
            description="Test capability",
            framework="Foundation",
            required_entitlement=EntitlementLevel.BASIC,
            refresh_interval=30.0,
            is_continuous=True,
            tags={"test", "example"}
        )

        self.assertEqual(descriptor.name, "test_cap")
        self.assertEqual(descriptor.framework, "Foundation")
        self.assertEqual(descriptor.required_entitlement, EntitlementLevel.BASIC)
        self.assertEqual(descriptor.refresh_interval, 30.0)
        self.assertTrue(descriptor.is_continuous)
        self.assertIn("test", descriptor.tags)


class TestCapabilityData(unittest.TestCase):
    """Test cases for CapabilityData."""

    def test_creation(self):
        """Test data creation."""
        timestamp = datetime.utcnow()
        data = CapabilityData(
            capability_name="test",
            timestamp=timestamp,
            data={"key": "value"},
            metadata={"source": "test"},
            error=None
        )

        self.assertEqual(data.capability_name, "test")
        self.assertEqual(data.timestamp, timestamp)
        self.assertEqual(data.data["key"], "value")
        self.assertIsNone(data.error)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime.utcnow()
        data = CapabilityData(
            capability_name="test",
            timestamp=timestamp,
            data={"key": "value"}
        )

        dict_data = data.to_dict()

        self.assertIsInstance(dict_data, dict)
        self.assertEqual(dict_data["capability"], "test")
        self.assertIn("timestamp", dict_data)
        self.assertEqual(dict_data["data"]["key"], "value")


class TestPluginRegistry(unittest.TestCase):
    """Test cases for PluginRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = PluginRegistry()

    def test_initialization(self):
        """Test registry initialization."""
        self.assertEqual(len(self.registry._plugins), 0)
        self.assertEqual(len(self.registry._instances), 0)

    def test_register_plugin(self):
        """Test plugin registration."""
        self.registry.register(MockPlugin, "mock")

        self.assertIn("mock", self.registry._plugins)
        self.assertEqual(self.registry._plugins["mock"], MockPlugin)

    def test_register_duplicate(self):
        """Test registering duplicate plugin."""
        self.registry.register(MockPlugin, "mock")

        with self.assertRaises(ValueError):
            self.registry.register(MockPlugin, "mock")

    def test_unregister_plugin(self):
        """Test plugin unregistration."""
        self.registry.register(MockPlugin, "mock")
        self.registry.unregister("mock")

        self.assertNotIn("mock", self.registry._plugins)

    @patch('builtins.__import__')
    def test_get_plugin(self, mock_import):
        """Test getting plugin instance."""
        mock_import.return_value = MagicMock()
        self.registry.register(MockPlugin, "mock")

        plugin = self.registry.get_plugin("mock")

        self.assertIsNotNone(plugin)
        self.assertIsInstance(plugin, MockPlugin)
        self.assertIn("mock", self.registry._instances)

    def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin."""
        plugin = self.registry.get_plugin("nonexistent")
        self.assertIsNone(plugin)

    def test_list_plugins(self):
        """Test listing registered plugins."""
        self.registry.register(MockPlugin, "mock1")
        self.registry.register(MockPlugin, "mock2")

        plugins = self.registry.list_plugins()

        self.assertEqual(len(plugins), 2)
        self.assertIn("mock1", plugins)
        self.assertIn("mock2", plugins)

    @patch('builtins.__import__')
    def test_shutdown_all(self, mock_import):
        """Test shutting down all plugins."""
        mock_import.return_value = MagicMock()
        self.registry.register(MockPlugin, "mock")

        plugin = self.registry.get_plugin("mock")
        self.assertIsNotNone(plugin)

        self.registry.shutdown_all()

        self.assertEqual(len(self.registry._instances), 0)


if __name__ == '__main__':
    unittest.main()
