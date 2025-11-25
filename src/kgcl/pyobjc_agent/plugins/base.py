"""
Base plugin interface for PyObjC capability discovery.

This module defines the abstract base class for capability plugins that
discover and monitor specific macOS features through PyObjC frameworks.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """Status of a capability plugin."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


class EntitlementLevel(str, Enum):
    """Required entitlement levels for capabilities."""
    NONE = "none"
    BASIC = "basic"
    SCREEN_RECORDING = "screen_recording"
    ACCESSIBILITY = "accessibility"
    FULL_DISK_ACCESS = "full_disk_access"
    CONTACTS = "contacts"
    CALENDAR = "calendar"
    LOCATION = "location"
    CAMERA = "camera"
    MICROPHONE = "microphone"


@dataclass
class CapabilityDescriptor:
    """
    Describes a capability that can be discovered by a plugin.

    Attributes:
        name: Unique capability identifier
        description: Human-readable description
        framework: PyObjC framework providing this capability
        required_entitlement: Entitlement level needed to access
        data_schema: JSON schema for capability data
        refresh_interval: Recommended refresh interval in seconds
        is_continuous: Whether capability provides continuous data stream
        tags: Classification tags for capability
    """
    name: str
    description: str
    framework: str
    required_entitlement: EntitlementLevel = EntitlementLevel.NONE
    data_schema: Optional[Dict[str, Any]] = None
    refresh_interval: float = 60.0
    is_continuous: bool = False
    tags: Set[str] = field(default_factory=set)


@dataclass
class CapabilityData:
    """
    Data returned by a capability query.

    Attributes:
        capability_name: Name of the capability
        timestamp: When data was collected
        data: The actual capability data
        metadata: Additional metadata about collection
        error: Error message if collection failed
    """
    capability_name: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "capability": self.capability_name,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error
        }


class BaseCapabilityPlugin(ABC):
    """
    Abstract base class for capability discovery plugins.

    Plugins implement discovery and monitoring of specific macOS features
    through PyObjC frameworks. Each plugin:
    - Declares capabilities it can discover
    - Checks for required entitlements
    - Implements data collection methods
    - Handles errors gracefully
    """

    def __init__(self, plugin_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin.

        Args:
            plugin_id: Unique identifier for this plugin instance
            config: Optional configuration dictionary
        """
        self.plugin_id = plugin_id
        self.config = config or {}
        self.status = PluginStatus.UNINITIALIZED
        self._error_message: Optional[str] = None
        self._capabilities_cache: Optional[List[CapabilityDescriptor]] = None

        logger.debug(f"Initialized plugin: {plugin_id}")

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Human-readable plugin name."""
        pass

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Plugin version string."""
        pass

    @property
    @abstractmethod
    def required_frameworks(self) -> List[str]:
        """List of PyObjC frameworks required by this plugin."""
        pass

    @abstractmethod
    def discover_capabilities(self) -> List[CapabilityDescriptor]:
        """
        Discover available capabilities provided by this plugin.

        Returns:
            List of capability descriptors

        Raises:
            RuntimeError: If plugin is not initialized
        """
        pass

    @abstractmethod
    def check_entitlements(self) -> Dict[str, bool]:
        """
        Check if required entitlements are available.

        Returns:
            Dictionary mapping entitlement names to availability status
        """
        pass

    @abstractmethod
    def collect_capability_data(
        self,
        capability_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> CapabilityData:
        """
        Collect data for a specific capability.

        Args:
            capability_name: Name of capability to query
            parameters: Optional parameters for data collection

        Returns:
            Collected capability data

        Raises:
            ValueError: If capability_name is not supported
            RuntimeError: If collection fails
        """
        pass

    def initialize(self) -> bool:
        """
        Initialize the plugin and verify requirements.

        Returns:
            True if initialization successful, False otherwise
        """
        if self.status == PluginStatus.READY:
            logger.debug(f"Plugin {self.plugin_id} already initialized")
            return True

        self.status = PluginStatus.INITIALIZING
        logger.info(f"Initializing plugin: {self.plugin_name}")

        try:
            # Check framework availability
            if not self._check_frameworks():
                self._error_message = "Required frameworks not available"
                self.status = PluginStatus.ERROR
                return False

            # Check entitlements
            entitlements = self.check_entitlements()
            missing = [k for k, v in entitlements.items() if not v]
            if missing:
                logger.warning(
                    f"Plugin {self.plugin_id} missing entitlements: {missing}"
                )

            # Discover capabilities
            self._capabilities_cache = self.discover_capabilities()
            logger.info(
                f"Plugin {self.plugin_id} discovered "
                f"{len(self._capabilities_cache)} capabilities"
            )

            self.status = PluginStatus.READY
            return True

        except Exception as e:
            logger.error(f"Failed to initialize plugin {self.plugin_id}: {e}")
            self._error_message = str(e)
            self.status = PluginStatus.ERROR
            return False

    def _check_frameworks(self) -> bool:
        """
        Verify all required frameworks are available.

        Returns:
            True if all frameworks available, False otherwise
        """
        for framework in self.required_frameworks:
            try:
                __import__(framework)
            except ImportError:
                logger.error(
                    f"Required framework {framework} not available. "
                    f"Install with: pip install pyobjc-framework-{framework}"
                )
                return False

        return True

    def get_capabilities(self) -> List[CapabilityDescriptor]:
        """
        Get list of available capabilities.

        Returns:
            List of capability descriptors

        Raises:
            RuntimeError: If plugin not initialized
        """
        if self.status != PluginStatus.READY:
            raise RuntimeError(
                f"Plugin {self.plugin_id} not ready. Status: {self.status}"
            )

        if self._capabilities_cache is None:
            self._capabilities_cache = self.discover_capabilities()

        return self._capabilities_cache

    def get_capability_by_name(self, name: str) -> Optional[CapabilityDescriptor]:
        """
        Get a specific capability descriptor by name.

        Args:
            name: Capability name

        Returns:
            Capability descriptor or None if not found
        """
        capabilities = self.get_capabilities()
        for cap in capabilities:
            if cap.name == name:
                return cap
        return None

    def collect_all_capabilities(
        self,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityData]:
        """
        Collect data for all available capabilities.

        Args:
            parameters: Optional parameters for collection

        Returns:
            List of collected capability data
        """
        if self.status != PluginStatus.READY:
            logger.warning(
                f"Cannot collect from plugin {self.plugin_id}. Status: {self.status}"
            )
            return []

        results = []
        capabilities = self.get_capabilities()

        for capability in capabilities:
            try:
                data = self.collect_capability_data(capability.name, parameters)
                results.append(data)
            except Exception as e:
                logger.error(
                    f"Failed to collect {capability.name} from {self.plugin_id}: {e}"
                )
                # Add error result
                results.append(CapabilityData(
                    capability_name=capability.name,
                    timestamp=datetime.utcnow(),
                    data={},
                    error=str(e)
                ))

        return results

    def get_status(self) -> Dict[str, Any]:
        """
        Get current plugin status information.

        Returns:
            Status dictionary
        """
        return {
            "plugin_id": self.plugin_id,
            "plugin_name": self.plugin_name,
            "version": self.plugin_version,
            "status": self.status.value,
            "error": self._error_message,
            "capabilities_count": (
                len(self._capabilities_cache)
                if self._capabilities_cache
                else 0
            ),
            "required_frameworks": self.required_frameworks
        }

    def shutdown(self) -> None:
        """
        Clean up plugin resources.

        Subclasses should override to perform cleanup.
        """
        logger.info(f"Shutting down plugin: {self.plugin_id}")
        self.status = PluginStatus.DISABLED

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"id={self.plugin_id} "
            f"status={self.status.value}>"
        )
