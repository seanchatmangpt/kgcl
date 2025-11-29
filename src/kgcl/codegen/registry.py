"""Generator registry for discovering and creating code generators.

This module provides a centralized registry for all code generators,
enabling dynamic discovery and instantiation.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from kgcl.codegen.base.generator import BaseGenerator


class GeneratorNotFoundError(Exception):
    """Raised when requested generator is not registered."""

    pass


# Type alias for generator factory functions
GeneratorFactory = Callable[..., BaseGenerator[Any]]


class GeneratorRegistry:
    """Registry for code generators.

    Provides centralized management of available generators with
    automatic discovery and factory pattern instantiation.

    Examples
    --------
    >>> from pathlib import Path
    >>> registry = GeneratorRegistry()
    >>> generator = registry.create("cli", template_dir=Path("templates"))
    >>> result = generator.generate(Path("input.ttl"))
    """

    def __init__(self) -> None:
        """Initialize generator registry."""
        self._generators: dict[str, GeneratorFactory] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(self, name: str, factory: GeneratorFactory, description: str = "", **metadata: Any) -> None:
        """Register a generator factory.

        Parameters
        ----------
        name : str
            Generator identifier
        factory : GeneratorFactory
            Factory function that creates generator instances
        description : str
            Human-readable description
        **metadata : Any
            Additional metadata (e.g., file_types, category)

        Examples
        --------
        >>> def cli_factory(**kwargs):
        ...     return CliGenerator(**kwargs)
        >>> registry.register("cli", cli_factory, description="CLI generator")
        """
        self._generators[name] = factory
        self._metadata[name] = {"description": description, **metadata}

    def unregister(self, name: str) -> None:
        """Unregister a generator.

        Parameters
        ----------
        name : str
            Generator identifier

        Raises
        ------
        GeneratorNotFoundError
            If generator not registered
        """
        if name not in self._generators:
            msg = f"Generator not registered: {name}"
            raise GeneratorNotFoundError(msg)

        del self._generators[name]
        del self._metadata[name]

    def create(self, name: str, **kwargs: Any) -> BaseGenerator[Any]:
        """Create generator instance.

        Parameters
        ----------
        name : str
            Generator identifier
        **kwargs : Any
            Generator initialization parameters

        Returns
        -------
        BaseGenerator[Any]
            Generator instance

        Raises
        ------
        GeneratorNotFoundError
            If generator not registered

        Examples
        --------
        >>> generator = registry.create("cli", template_dir=Path("templates/cli"), output_dir=Path("src"))
        """
        if name not in self._generators:
            msg = f"Generator not registered: {name}"
            raise GeneratorNotFoundError(msg)

        factory = self._generators[name]
        return factory(**kwargs)

    def list_generators(self) -> list[str]:
        """List all registered generators.

        Returns
        -------
        list[str]
            List of generator names
        """
        return sorted(self._generators.keys())

    def get_metadata(self, name: str) -> dict[str, Any]:
        """Get generator metadata.

        Parameters
        ----------
        name : str
            Generator identifier

        Returns
        -------
        dict[str, Any]
            Generator metadata

        Raises
        ------
        GeneratorNotFoundError
            If generator not registered
        """
        if name not in self._metadata:
            msg = f"Generator not registered: {name}"
            raise GeneratorNotFoundError(msg)

        return self._metadata[name].copy()

    def discover_generators(self) -> None:
        """Discover and register all built-in generators.

        This method automatically imports and registers all generators
        from kgcl.codegen.generators module.
        """
        # Import generators to trigger registration decorators
        try:
            from kgcl.codegen.generators.cli_generator import CliGenerator

            self.register(
                "cli",
                lambda **kwargs: CliGenerator(**kwargs),
                description="Generate Typer CLI from RDF ontology",
                file_types=[".ttl", ".rdf"],
                category="cli",
            )
        except ImportError:
            pass

        try:
            from kgcl.codegen.generators.java_generator import JavaGenerator

            self.register(
                "java",
                lambda **kwargs: JavaGenerator(**kwargs),
                description="Generate Python client from Java service",
                file_types=[".java"],
                category="language",
            )
        except ImportError:
            pass


# Global registry instance
_global_registry = GeneratorRegistry()


def register_generator(
    name: str, description: str = "", **metadata: Any
) -> Callable[[GeneratorFactory], GeneratorFactory]:
    """Decorator for registering generators.

    Parameters
    ----------
    name : str
        Generator identifier
    description : str
        Human-readable description
    **metadata : Any
        Additional metadata

    Returns
    -------
    Callable[[GeneratorFactory], GeneratorFactory]
        Decorator function

    Examples
    --------
    >>> @register_generator("custom", description="My custom generator")
    ... def create_custom_generator(**kwargs):
    ...     return CustomGenerator(**kwargs)
    """

    def decorator(factory: GeneratorFactory) -> GeneratorFactory:
        _global_registry.register(name, factory, description, **metadata)
        return factory

    return decorator


def get_registry() -> GeneratorRegistry:
    """Get global generator registry.

    Returns
    -------
    GeneratorRegistry
        Global registry instance
    """
    return _global_registry


__all__ = ["GeneratorRegistry", "GeneratorNotFoundError", "GeneratorFactory", "register_generator", "get_registry"]
