"""
Unit tests for PyObjC framework crawler.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from ..crawler import (
    CapabilityClass,
    CapabilityMethod,
    FrameworkCapabilities,
    FrameworkName,
    PyObjCFrameworkCrawler,
)


class TestPyObjCFrameworkCrawler(unittest.TestCase):
    """Test cases for PyObjC framework crawler."""

    def setUp(self):
        """Set up test fixtures."""
        self.crawler = PyObjCFrameworkCrawler(safe_mode=True)

    def test_initialization(self):
        """Test crawler initialization."""
        self.assertTrue(self.crawler.safe_mode)
        self.assertEqual(len(self.crawler.loaded_frameworks), 0)
        self.assertEqual(len(self.crawler._capability_cache), 0)

    def test_is_observable_method(self):
        """Test observable method detection."""
        # Observable prefixes
        self.assertTrue(self.crawler._is_observable_method("getFoo"))
        self.assertTrue(self.crawler._is_observable_method("isActive"))
        self.assertTrue(self.crawler._is_observable_method("hasValue"))
        self.assertTrue(self.crawler._is_observable_method("canExecute"))
        self.assertTrue(self.crawler._is_observable_method("currentState"))

        # Readonly patterns
        self.assertTrue(self.crawler._is_observable_method("description"))
        self.assertTrue(self.crawler._is_observable_method("identifier"))
        self.assertTrue(self.crawler._is_observable_method("name"))

        # Non-observable
        self.assertFalse(self.crawler._is_observable_method("setFoo"))
        self.assertFalse(self.crawler._is_observable_method("doSomething"))
        self.assertFalse(self.crawler._is_observable_method("execute:withOptions:"))

    @patch("builtins.__import__")
    def test_load_framework_success(self, mock_import):
        """Test successful framework loading."""
        mock_framework = MagicMock()
        mock_import.return_value = mock_framework

        result = self.crawler.load_framework(FrameworkName.FOUNDATION)

        self.assertTrue(result)
        self.assertIn("Foundation", self.crawler.loaded_frameworks)
        mock_import.assert_called_once_with("Foundation")

    @patch("builtins.__import__")
    def test_load_framework_failure(self, mock_import):
        """Test framework loading failure."""
        mock_import.side_effect = ImportError("Framework not found")

        result = self.crawler.load_framework(FrameworkName.APPKIT)

        self.assertFalse(result)
        self.assertNotIn("AppKit", self.crawler.loaded_frameworks)

    def test_enumerate_classes_not_loaded(self):
        """Test enumerating classes when framework not loaded."""
        classes = self.crawler.enumerate_classes(FrameworkName.APPKIT)
        self.assertEqual(classes, [])

    @patch("builtins.__import__")
    def test_enumerate_classes_success(self, mock_import):
        """Test successful class enumeration."""
        # Mock framework with classes
        mock_class1 = type("MockClass1", (), {})
        mock_class2 = type("MockClass2", (), {})
        mock_framework = MagicMock()
        mock_framework.__dir__ = lambda self: [
            "MockClass1",
            "MockClass2",
            "not_a_class",
        ]
        mock_framework.MockClass1 = mock_class1
        mock_framework.MockClass2 = mock_class2
        mock_framework.not_a_class = "string"

        mock_import.return_value = mock_framework

        self.crawler.load_framework(FrameworkName.FOUNDATION)
        classes = self.crawler.enumerate_classes(FrameworkName.FOUNDATION)

        self.assertIn("MockClass1", classes)
        self.assertIn("MockClass2", classes)
        self.assertNotIn("not_a_class", classes)

    def test_generate_jsonld(self):
        """Test JSON-LD generation."""
        # Create test capabilities
        method = CapabilityMethod(
            selector="isActive",
            return_type="bool",
            is_property=True,
            is_observable=True,
        )

        cls = CapabilityClass(
            name="TestClass", framework="TestFramework", methods=[method]
        )

        capabilities = FrameworkCapabilities(
            framework_name="TestFramework", classes=[cls]
        )

        # Generate JSON-LD
        jsonld = self.crawler.generate_jsonld(capabilities)

        # Verify structure
        self.assertIn("@context", jsonld)
        self.assertIn("@type", jsonld)
        self.assertEqual(jsonld["@type"], "framework")
        self.assertEqual(jsonld["name"], "TestFramework")
        self.assertEqual(jsonld["capabilityCount"], 1)
        self.assertIsInstance(jsonld["capabilities"], list)

        # Verify capability
        cap = jsonld["capabilities"][0]
        self.assertEqual(cap["className"], "TestClass")
        self.assertEqual(cap["selector"], "isActive")
        self.assertTrue(cap["isProperty"])
        self.assertTrue(cap["isObservable"])

    def test_export_capabilities(self):
        """Test capabilities export."""
        import os
        import tempfile

        # Create test capabilities
        capabilities = {
            "TestFramework": FrameworkCapabilities(
                framework_name="TestFramework", classes=[]
            )
        }

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonld") as f:
            temp_path = f.name

        try:
            self.crawler.export_capabilities(capabilities, temp_path, format="jsonld")

            # Verify file created
            self.assertTrue(os.path.exists(temp_path))

            # Verify content
            with open(temp_path) as f:
                data = json.load(f)

            self.assertIn("@context", data)
            self.assertIn("@graph", data)

        finally:
            os.unlink(temp_path)


class TestCapabilityDataStructures(unittest.TestCase):
    """Test capability data structures."""

    def test_capability_method_creation(self):
        """Test CapabilityMethod creation."""
        method = CapabilityMethod(
            selector="getValue",
            return_type="NSString",
            argument_types=["NSObject"],
            is_property=False,
            is_observable=True,
            description="Get a value",
        )

        self.assertEqual(method.selector, "getValue")
        self.assertEqual(method.return_type, "NSString")
        self.assertFalse(method.is_property)
        self.assertTrue(method.is_observable)

    def test_capability_class_creation(self):
        """Test CapabilityClass creation."""
        method1 = CapabilityMethod(selector="method1", return_type="void")
        method2 = CapabilityMethod(selector="method2", return_type="int")

        cls = CapabilityClass(
            name="TestClass",
            framework="Foundation",
            methods=[method1, method2],
            protocols=["NSObject"],
        )

        self.assertEqual(cls.name, "TestClass")
        self.assertEqual(cls.framework, "Foundation")
        self.assertEqual(len(cls.methods), 2)
        self.assertIn("NSObject", cls.protocols)

    def test_framework_capabilities_creation(self):
        """Test FrameworkCapabilities creation."""
        capabilities = FrameworkCapabilities(framework_name="AppKit", version="1.0")

        self.assertEqual(capabilities.framework_name, "AppKit")
        self.assertEqual(capabilities.version, "1.0")
        self.assertEqual(len(capabilities.classes), 0)
        self.assertIsNotNone(capabilities.discovered_at)


if __name__ == "__main__":
    unittest.main()
