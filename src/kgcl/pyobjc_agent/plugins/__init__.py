"""
Plugin system for PyObjC capability discovery.

This package provides:
- Base plugin interface
- Plugin registry and loader
- Built-in plugins for common macOS features
"""

from typing import Dict, List, Optional, Type
import logging
from .base import (
    BaseCapabilityPlugin,
    CapabilityDescriptor,
    CapabilityData,
    PluginStatus,
    EntitlementLevel
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Registry for capability discovery plugins.

    Manages plugin lifecycle:
    - Registration
    - Initialization
    - Discovery
    - Data collection
    """

    def __init__(self):
        self._plugins: Dict[str, Type[BaseCapabilityPlugin]] = {}
        self._instances: Dict[str, BaseCapabilityPlugin] = {}
        logger.debug("Initialized plugin registry")

    def register(
        self,
        plugin_class: Type[BaseCapabilityPlugin],
        plugin_id: Optional[str] = None
    ) -> None:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register
            plugin_id: Optional custom plugin ID

        Raises:
            ValueError: If plugin_id already registered
        """
        if plugin_id is None:
            plugin_id = plugin_class.__name__

        if plugin_id in self._plugins:
            raise ValueError(f"Plugin {plugin_id} already registered")

        self._plugins[plugin_id] = plugin_class
        logger.info(f"Registered plugin: {plugin_id}")

    def unregister(self, plugin_id: str) -> None:
        """
        Unregister a plugin.

        Args:
            plugin_id: ID of plugin to unregister
        """
        # Shutdown instance if exists
        if plugin_id in self._instances:
            self._instances[plugin_id].shutdown()
            del self._instances[plugin_id]

        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            logger.info(f"Unregistered plugin: {plugin_id}")

    def get_plugin(
        self,
        plugin_id: str,
        config: Optional[Dict] = None,
        auto_initialize: bool = True
    ) -> Optional[BaseCapabilityPlugin]:
        """
        Get or create a plugin instance.

        Args:
            plugin_id: Plugin ID
            config: Optional plugin configuration
            auto_initialize: Whether to initialize plugin automatically

        Returns:
            Plugin instance or None if not found
        """
        # Return existing instance
        if plugin_id in self._instances:
            return self._instances[plugin_id]

        # Create new instance
        if plugin_id not in self._plugins:
            logger.error(f"Plugin {plugin_id} not registered")
            return None

        plugin_class = self._plugins[plugin_id]
        instance = plugin_class(plugin_id=plugin_id, config=config)

        if auto_initialize:
            if not instance.initialize():
                logger.error(f"Failed to initialize plugin {plugin_id}")
                return None

        self._instances[plugin_id] = instance
        return instance

    def list_plugins(self) -> List[str]:
        """
        List all registered plugin IDs.

        Returns:
            List of plugin IDs
        """
        return list(self._plugins.keys())

    def list_initialized_plugins(self) -> List[str]:
        """
        List all initialized plugin instances.

        Returns:
            List of plugin IDs that are initialized
        """
        return list(self._instances.keys())

    def get_all_capabilities(self) -> Dict[str, List[CapabilityDescriptor]]:
        """
        Get capabilities from all initialized plugins.

        Returns:
            Dictionary mapping plugin IDs to their capabilities
        """
        capabilities = {}

        for plugin_id, plugin in self._instances.items():
            try:
                capabilities[plugin_id] = plugin.get_capabilities()
            except Exception as e:
                logger.error(f"Failed to get capabilities from {plugin_id}: {e}")
                capabilities[plugin_id] = []

        return capabilities

    def collect_all_data(
        self,
        parameters: Optional[Dict] = None
    ) -> Dict[str, List[CapabilityData]]:
        """
        Collect data from all initialized plugins.

        Args:
            parameters: Optional collection parameters

        Returns:
            Dictionary mapping plugin IDs to their collected data
        """
        results = {}

        for plugin_id, plugin in self._instances.items():
            try:
                results[plugin_id] = plugin.collect_all_capabilities(parameters)
            except Exception as e:
                logger.error(f"Failed to collect from {plugin_id}: {e}")
                results[plugin_id] = []

        return results

    def shutdown_all(self) -> None:
        """Shutdown all plugin instances."""
        for plugin_id, plugin in list(self._instances.items()):
            try:
                plugin.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {plugin_id}: {e}")

        self._instances.clear()
        logger.info("All plugins shut down")


# Global registry instance
_global_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _global_registry


def register_plugin(
    plugin_class: Type[BaseCapabilityPlugin],
    plugin_id: Optional[str] = None
) -> None:
    """
    Register a plugin with the global registry.

    Args:
        plugin_class: Plugin class to register
        plugin_id: Optional custom plugin ID
    """
    _global_registry.register(plugin_class, plugin_id)


def load_builtin_plugins() -> None:
    """Load all built-in plugins."""
    try:
        from .appkit_plugin import AppKitPlugin
        register_plugin(AppKitPlugin, "appkit")
    except ImportError as e:
        logger.warning(f"Failed to load AppKit plugin: {e}")

    try:
        from .browser_plugin import BrowserPlugin
        register_plugin(BrowserPlugin, "browser")
    except ImportError as e:
        logger.warning(f"Failed to load Browser plugin: {e}")

    try:
        from .calendar_plugin import CalendarPlugin
        register_plugin(CalendarPlugin, "calendar")
    except ImportError as e:
        logger.warning(f"Failed to load Calendar plugin: {e}")

    logger.info(f"Loaded {len(_global_registry.list_plugins())} built-in plugins")


__all__ = [
    "BaseCapabilityPlugin",
    "CapabilityDescriptor",
    "CapabilityData",
    "PluginStatus",
    "EntitlementLevel",
    "PluginRegistry",
    "get_registry",
    "register_plugin",
    "load_builtin_plugins"
]
