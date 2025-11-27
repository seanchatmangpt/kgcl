"""TemplateRegistry Protocol - Abstract interface for template storage.

This module defines the protocol for loading and discovering templates
with their frontmatter. Implementations include filesystem-based loading
and in-memory registries for testing.

Examples
--------
>>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
>>> class MockRegistry:
...     def get(self, name: str) -> TemplateDescriptor | None:
...         return None
...
...     def list_templates(self) -> list[str]:
...         return []
...
...     def exists(self, name: str) -> bool:
...         return False
>>> registry = MockRegistry()
>>> isinstance(registry, TemplateRegistry)
True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from kgcl.projection.domain.bundle import BundleDescriptor
    from kgcl.projection.domain.descriptors import TemplateDescriptor


@runtime_checkable
class TemplateRegistry(Protocol):
    """Protocol for template storage and discovery.

    This protocol defines the interface for loading templates with their
    parsed frontmatter. Implementations handle filesystem loading, caching,
    and frontmatter parsing.

    Methods
    -------
    get(name)
        Load and parse a template by name.
    list_templates()
        List all available template names.
    exists(name)
        Check if a template exists.

    Examples
    --------
    >>> class InMemoryRegistry:
    ...     def __init__(self) -> None:
    ...         self._templates: dict[str, TemplateDescriptor] = {}
    ...
    ...     def add(self, desc: TemplateDescriptor) -> None:
    ...         self._templates[desc.template_path] = desc
    ...
    ...     def get(self, name: str) -> TemplateDescriptor | None:
    ...         return self._templates.get(name)
    ...
    ...     def list_templates(self) -> list[str]:
    ...         return list(self._templates.keys())
    ...
    ...     def exists(self, name: str) -> bool:
    ...         return name in self._templates
    """

    def get(self, name: str) -> TemplateDescriptor | None:
        """Load and return a template descriptor by name.

        Parameters
        ----------
        name : str
            Template name or path (relative to template root).

        Returns
        -------
        TemplateDescriptor | None
            Parsed template with frontmatter, or None if not found.

        Examples
        --------
        >>> class R:
        ...     def get(self, n: str) -> TemplateDescriptor | None:
        ...         return None
        ...
        ...     def list_templates(self) -> list[str]:
        ...         return []
        ...
        ...     def exists(self, n: str) -> bool:
        ...         return False
        >>> R().get("api.j2") is None
        True
        """
        ...

    def list_templates(self) -> list[str]:
        """List all available template names.

        Returns
        -------
        list[str]
            Template names/paths.

        Examples
        --------
        >>> class R:
        ...     def get(self, n: str) -> TemplateDescriptor | None:
        ...         return None
        ...
        ...     def list_templates(self) -> list[str]:
        ...         return ["a.j2", "b.j2"]
        ...
        ...     def exists(self, n: str) -> bool:
        ...         return True
        >>> R().list_templates()
        ['a.j2', 'b.j2']
        """
        ...

    def exists(self, name: str) -> bool:
        """Check if a template exists.

        Parameters
        ----------
        name : str
            Template name to check.

        Returns
        -------
        bool
            True if template exists.

        Examples
        --------
        >>> class R:
        ...     def get(self, n: str) -> TemplateDescriptor | None:
        ...         return None
        ...
        ...     def list_templates(self) -> list[str]:
        ...         return []
        ...
        ...     def exists(self, n: str) -> bool:
        ...         return n == "api.j2"
        >>> R().exists("api.j2")
        True
        >>> R().exists("missing.j2")
        False
        """
        ...


@runtime_checkable
class BundleRegistry(Protocol):
    """Protocol for bundle storage and discovery.

    This protocol defines the interface for loading bundle definitions.
    Bundles are YAML files that specify multi-file projections.

    Methods
    -------
    get_bundle(name)
        Load and parse a bundle by name.
    list_bundles()
        List all available bundle names.
    exists_bundle(name)
        Check if a bundle exists.

    Examples
    --------
    >>> class MockBundleRegistry:
    ...     def get_bundle(self, name: str) -> BundleDescriptor | None:
    ...         return None
    ...
    ...     def list_bundles(self) -> list[str]:
    ...         return []
    ...
    ...     def exists_bundle(self, name: str) -> bool:
    ...         return False
    """

    def get_bundle(self, name: str) -> BundleDescriptor | None:
        """Load and return a bundle descriptor by name.

        Parameters
        ----------
        name : str
            Bundle name or path.

        Returns
        -------
        BundleDescriptor | None
            Parsed bundle definition, or None if not found.

        Examples
        --------
        >>> class R:
        ...     def get_bundle(self, n: str) -> BundleDescriptor | None:
        ...         return None
        ...
        ...     def list_bundles(self) -> list[str]:
        ...         return []
        ...
        ...     def exists_bundle(self, n: str) -> bool:
        ...         return False
        >>> R().get_bundle("api-bundle.yaml") is None
        True
        """
        ...

    def list_bundles(self) -> list[str]:
        """List all available bundle names.

        Returns
        -------
        list[str]
            Bundle names/paths.

        Examples
        --------
        >>> class R:
        ...     def get_bundle(self, n: str) -> BundleDescriptor | None:
        ...         return None
        ...
        ...     def list_bundles(self) -> list[str]:
        ...         return ["crud.yaml"]
        ...
        ...     def exists_bundle(self, n: str) -> bool:
        ...         return True
        >>> R().list_bundles()
        ['crud.yaml']
        """
        ...

    def exists_bundle(self, name: str) -> bool:
        """Check if a bundle exists.

        Parameters
        ----------
        name : str
            Bundle name to check.

        Returns
        -------
        bool
            True if bundle exists.

        Examples
        --------
        >>> class R:
        ...     def get_bundle(self, n: str) -> BundleDescriptor | None:
        ...         return None
        ...
        ...     def list_bundles(self) -> list[str]:
        ...         return []
        ...
        ...     def exists_bundle(self, n: str) -> bool:
        ...         return n == "api.yaml"
        >>> R().exists_bundle("api.yaml")
        True
        """
        ...


class InMemoryTemplateRegistry:
    """In-memory template registry for testing.

    Provides a simple dictionary-backed registry for use in tests.

    Examples
    --------
    >>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
    >>> registry = InMemoryTemplateRegistry()
    >>> registry.list_templates()
    []
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._templates: dict[str, TemplateDescriptor] = {}

    def add(self, descriptor: TemplateDescriptor) -> None:
        """Add a template to the registry.

        Parameters
        ----------
        descriptor : TemplateDescriptor
            Template to register (uses template_path as key).

        Examples
        --------
        >>> from kgcl.projection.domain.descriptors import TemplateDescriptor, OntologyConfig, TemplateMetadata
        >>> r = InMemoryTemplateRegistry()
        >>> d = TemplateDescriptor(
        ...     id="x",
        ...     engine="jinja2",
        ...     language="py",
        ...     framework="",
        ...     version="1.0",
        ...     ontology=OntologyConfig("main"),
        ...     queries=(),
        ...     n3_rules=(),
        ...     metadata=TemplateMetadata(),
        ...     template_path="test.j2",
        ...     raw_content="",
        ... )
        >>> r.add(d)
        >>> r.exists("test.j2")
        True
        """
        self._templates[descriptor.template_path] = descriptor

    def get(self, name: str) -> TemplateDescriptor | None:
        """Get template by name.

        Parameters
        ----------
        name : str
            Template path.

        Returns
        -------
        TemplateDescriptor | None
            Template or None.
        """
        return self._templates.get(name)

    def list_templates(self) -> list[str]:
        """List all template names.

        Returns
        -------
        list[str]
            Template paths.
        """
        return list(self._templates.keys())

    def exists(self, name: str) -> bool:
        """Check if template exists.

        Parameters
        ----------
        name : str
            Template path.

        Returns
        -------
        bool
            True if exists.
        """
        return name in self._templates
