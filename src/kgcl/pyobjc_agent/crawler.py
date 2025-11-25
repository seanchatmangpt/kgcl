"""
PyObjC Framework Crawler for macOS Feature Discovery.

This module provides functionality to:
- Load PyObjC frameworks dynamically
- Enumerate classes, protocols, and selectors
- Filter for observable/queryable state methods
- Generate capability JSON-LD from discovered APIs
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FrameworkName(str, Enum):
    """Supported PyObjC frameworks for capability discovery."""

    APPKIT = "AppKit"
    FOUNDATION = "Foundation"
    EVENTKIT = "EventKit"
    CORELOCATION = "CoreLocation"
    AVFOUNDATION = "AVFoundation"
    WEBKIT = "WebKit"
    CONTACTS = "Contacts"
    CALENDARSTORE = "CalendarStore"


@dataclass
class CapabilityMethod:
    """Represents a discoverable method in a PyObjC class."""

    selector: str
    return_type: str
    argument_types: list[str] = field(default_factory=list)
    is_property: bool = False
    is_observable: bool = False
    requires_entitlement: str | None = None
    description: str = ""


@dataclass
class CapabilityClass:
    """Represents a PyObjC class with discoverable capabilities."""

    name: str
    framework: str
    protocols: list[str] = field(default_factory=list)
    methods: list[CapabilityMethod] = field(default_factory=list)
    parent_class: str | None = None


@dataclass
class FrameworkCapabilities:
    """Aggregated capabilities from a PyObjC framework."""

    framework_name: str
    version: str | None = None
    classes: list[CapabilityClass] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PyObjCFrameworkCrawler:
    """
    Crawls PyObjC frameworks to discover available capabilities.

    This crawler:
    1. Dynamically loads PyObjC frameworks
    2. Enumerates classes, protocols, and methods
    3. Filters for state-queryable methods (getters, properties)
    4. Generates structured capability metadata
    """

    # Method prefixes that typically indicate queryable state
    OBSERVABLE_PREFIXES = {
        "get",
        "is",
        "has",
        "can",
        "should",
        "count",
        "current",
        "active",
        "visible",
        "enabled",
        "available",
        "frontmost",
    }

    # Method patterns for read-only state access
    READONLY_PATTERNS = {
        "description",
        "identifier",
        "name",
        "title",
        "url",
        "date",
        "location",
        "status",
        "state",
        "value",
        "path",
        "bundle",
    }

    def __init__(self, safe_mode: bool = True):
        """
        Initialize the framework crawler.

        Args:
            safe_mode: If True, only enumerate read-only methods
        """
        self.safe_mode = safe_mode
        self.loaded_frameworks: dict[str, Any] = {}
        self._capability_cache: dict[str, FrameworkCapabilities] = {}

    def load_framework(self, framework_name: FrameworkName) -> bool:
        """
        Dynamically load a PyObjC framework.

        Args:
            framework_name: Name of the framework to load

        Returns
        -------
            True if framework loaded successfully, False otherwise
        """
        if framework_name.value in self.loaded_frameworks:
            logger.debug(f"Framework {framework_name.value} already loaded")
            return True

        try:
            # Dynamic import of PyObjC framework
            module = __import__(framework_name.value)
            self.loaded_frameworks[framework_name.value] = module
            logger.info(f"Successfully loaded framework: {framework_name.value}")
            return True

        except ImportError as e:
            logger.warning(f"Failed to load framework {framework_name.value}: {e}")
            logger.info(
                f"Framework may not be available or requires installation: pip install pyobjc-framework-{framework_name.value}"
            )
            return False

        except Exception as e:
            logger.error(f"Unexpected error loading framework {framework_name.value}: {e}")
            return False

    def enumerate_classes(self, framework_name: FrameworkName) -> list[str]:
        """
        Enumerate all classes in a loaded framework.

        Args:
            framework_name: Framework to enumerate

        Returns
        -------
            List of class names
        """
        if framework_name.value not in self.loaded_frameworks:
            logger.warning(f"Framework {framework_name.value} not loaded")
            return []

        framework = self.loaded_frameworks[framework_name.value]
        classes = []

        try:
            # Get all attributes from the framework module
            for attr_name in dir(framework):
                attr = getattr(framework, attr_name)
                # Check if it's a class (type)
                if isinstance(attr, type):
                    classes.append(attr_name)

            logger.debug(f"Found {len(classes)} classes in {framework_name.value}")

        except Exception as e:
            logger.error(f"Error enumerating classes in {framework_name.value}: {e}")

        return classes

    def _is_observable_method(self, selector: str) -> bool:
        """
        Check if a method selector indicates observable/queryable state.

        Args:
            selector: ObjC selector string

        Returns
        -------
            True if method appears to be state-queryable
        """
        selector_lower = selector.lower()

        # Check for observable prefixes
        for prefix in self.OBSERVABLE_PREFIXES:
            if selector_lower.startswith(prefix):
                return True

        # Check for readonly patterns
        for pattern in self.READONLY_PATTERNS:
            if pattern in selector_lower:
                return True

        # No arguments and returns value typically indicates getter
        if ":" not in selector and not selector.startswith("set"):
            return True

        return False

    def enumerate_methods(
        self, framework_name: FrameworkName, class_name: str
    ) -> list[CapabilityMethod]:
        """
        Enumerate methods for a specific class.

        Args:
            framework_name: Framework containing the class
            class_name: Name of the class to examine

        Returns
        -------
            List of discoverable capability methods
        """
        if framework_name.value not in self.loaded_frameworks:
            return []

        framework = self.loaded_frameworks[framework_name.value]
        methods = []

        try:
            cls = getattr(framework, class_name)

            # Get all methods/attributes
            for attr_name in dir(cls):
                # Skip private methods
                if attr_name.startswith("_"):
                    continue

                # Skip if safe_mode and not observable
                if self.safe_mode and not self._is_observable_method(attr_name):
                    continue

                try:
                    attr = getattr(cls, attr_name)

                    # Check if it's a property
                    is_property = isinstance(attr, property)

                    # Check if it's a method
                    is_method = callable(attr)

                    if is_property or (is_method and self._is_observable_method(attr_name)):
                        method = CapabilityMethod(
                            selector=attr_name,
                            return_type="unknown",  # Would need objc introspection
                            is_property=is_property,
                            is_observable=self._is_observable_method(attr_name),
                        )
                        methods.append(method)

                except Exception as e:
                    logger.debug(f"Skipping attribute {attr_name}: {e}")
                    continue

        except AttributeError:
            logger.warning(f"Class {class_name} not found in {framework_name.value}")
        except Exception as e:
            logger.error(f"Error enumerating methods for {class_name}: {e}")

        return methods

    def crawl_framework(self, framework_name: FrameworkName) -> FrameworkCapabilities:
        """
        Fully crawl a framework to discover all capabilities.

        Args:
            framework_name: Framework to crawl

        Returns
        -------
            Complete framework capabilities structure
        """
        # Check cache
        if framework_name.value in self._capability_cache:
            logger.debug(f"Returning cached capabilities for {framework_name.value}")
            return self._capability_cache[framework_name.value]

        # Load framework if needed
        if not self.load_framework(framework_name):
            return FrameworkCapabilities(framework_name=framework_name.value)

        capabilities = FrameworkCapabilities(framework_name=framework_name.value)

        # Enumerate all classes
        class_names = self.enumerate_classes(framework_name)

        for class_name in class_names:
            # Enumerate methods for each class
            methods = self.enumerate_methods(framework_name, class_name)

            if methods:  # Only include classes with discoverable methods
                capability_class = CapabilityClass(
                    name=class_name, framework=framework_name.value, methods=methods
                )
                capabilities.classes.append(capability_class)

        logger.info(
            f"Crawled {framework_name.value}: "
            f"{len(capabilities.classes)} classes, "
            f"{sum(len(c.methods) for c in capabilities.classes)} methods"
        )

        # Cache results
        self._capability_cache[framework_name.value] = capabilities

        return capabilities

    def generate_jsonld(self, capabilities: FrameworkCapabilities) -> dict[str, Any]:
        """
        Generate JSON-LD representation of framework capabilities.

        Args:
            capabilities: Framework capabilities to serialize

        Returns
        -------
            JSON-LD dictionary
        """
        context = {
            "@vocab": "https://kgcl.dev/ontology/macos#",
            "framework": "macos:Framework",
            "capability": "macos:Capability",
            "method": "macos:Method",
            "selector": "macos:selector",
            "discoveredAt": {
                "@id": "macos:discoveredAt",
                "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
            },
        }

        capabilities_list = []
        for cls in capabilities.classes:
            for method in cls.methods:
                capability = {
                    "@type": "capability",
                    "className": cls.name,
                    "framework": capabilities.framework_name,
                    "selector": method.selector,
                    "isProperty": method.is_property,
                    "isObservable": method.is_observable,
                }

                if method.requires_entitlement:
                    capability["requiresEntitlement"] = method.requires_entitlement

                capabilities_list.append(capability)

        jsonld = {
            "@context": context,
            "@type": "framework",
            "name": capabilities.framework_name,
            "discoveredAt": capabilities.discovered_at,
            "capabilityCount": len(capabilities_list),
            "capabilities": capabilities_list,
        }

        return jsonld

    def crawl_all_frameworks(self) -> dict[str, FrameworkCapabilities]:
        """
        Crawl all supported frameworks.

        Returns
        -------
            Dictionary mapping framework names to their capabilities
        """
        all_capabilities = {}

        for framework_name in FrameworkName:
            logger.info(f"Crawling framework: {framework_name.value}")
            capabilities = self.crawl_framework(framework_name)
            all_capabilities[framework_name.value] = capabilities

        return all_capabilities

    def export_capabilities(
        self,
        capabilities: dict[str, FrameworkCapabilities],
        output_path: str,
        format: str = "jsonld",
    ) -> None:
        """
        Export discovered capabilities to file.

        Args:
            capabilities: Capabilities to export
            output_path: Path to output file
            format: Export format ('jsonld' or 'json')
        """
        try:
            if format == "jsonld":
                # Generate JSON-LD for each framework
                output = {
                    "@context": "https://kgcl.dev/ontology/macos",
                    "@graph": [self.generate_jsonld(cap) for cap in capabilities.values()],
                }
            else:
                # Plain JSON export
                output = {name: asdict(cap) for name, cap in capabilities.items()}

            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            logger.info(f"Exported capabilities to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export capabilities: {e}")
            raise


def main():
    """CLI entry point for framework crawler."""
    logging.basicConfig(level=logging.INFO)

    crawler = PyObjCFrameworkCrawler(safe_mode=True)

    # Crawl all frameworks
    all_capabilities = crawler.crawl_all_frameworks()

    # Export to JSON-LD
    crawler.export_capabilities(
        all_capabilities, "/Users/sac/dev/kgcl/capabilities.jsonld", format="jsonld"
    )

    # Print summary
    total_classes = sum(len(cap.classes) for cap in all_capabilities.values())
    total_methods = sum(
        sum(len(cls.methods) for cls in cap.classes) for cap in all_capabilities.values()
    )

    print("\n=== Capability Discovery Summary ===")
    print(f"Frameworks crawled: {len(all_capabilities)}")
    print(f"Total classes: {total_classes}")
    print(f"Total methods: {total_methods}")
    print("\nOutput: /Users/sac/dev/kgcl/capabilities.jsonld")


if __name__ == "__main__":
    main()
