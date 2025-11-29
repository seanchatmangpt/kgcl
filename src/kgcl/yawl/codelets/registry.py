"""Codelet registry with decorator support.

Provides a registry for codelet implementations that can be
looked up by name. Includes a decorator for easy registration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Type, TypeVar

from kgcl.yawl.codelets.base import Codelet, CodeletContext, CodeletResult

T = TypeVar("T", bound=Codelet)


@dataclass
class CodeletRegistry:
    """Registry for codelet implementations.

    Codelets can be registered by name and looked up for execution.

    Parameters
    ----------
    codelets : dict[str, Codelet]
        Registered codelets by name
    """

    codelets: dict[str, Codelet] = field(default_factory=dict)

    def register(self, name: str, codelet: Codelet) -> None:
        """Register a codelet.

        Parameters
        ----------
        name : str
            Registration name
        codelet : Codelet
            Codelet instance
        """
        self.codelets[name] = codelet

    def register_class(self, name: str, cls: type[Codelet]) -> None:
        """Register a codelet class (instantiates automatically).

        Parameters
        ----------
        name : str
            Registration name
        cls : Type[Codelet]
            Codelet class
        """
        self.codelets[name] = cls()

    def unregister(self, name: str) -> bool:
        """Unregister a codelet.

        Parameters
        ----------
        name : str
            Codelet name

        Returns
        -------
        bool
            True if unregistered
        """
        if name in self.codelets:
            del self.codelets[name]
            return True
        return False

    def get(self, name: str) -> Codelet | None:
        """Get codelet by name.

        Parameters
        ----------
        name : str
            Codelet name

        Returns
        -------
        Codelet | None
            Codelet or None
        """
        return self.codelets.get(name)

    def is_registered(self, name: str) -> bool:
        """Check if codelet is registered.

        Parameters
        ----------
        name : str
            Codelet name

        Returns
        -------
        bool
            True if registered
        """
        return name in self.codelets

    def list_names(self) -> list[str]:
        """List registered codelet names.

        Returns
        -------
        list[str]
            Codelet names
        """
        return list(self.codelets.keys())

    def clear(self) -> None:
        """Clear all registrations."""
        self.codelets.clear()


# Global registry instance
_global_registry = CodeletRegistry()


def get_global_registry() -> CodeletRegistry:
    """Get the global codelet registry.

    Returns
    -------
    CodeletRegistry
        Global registry
    """
    return _global_registry


def codelet(name: str | None = None) -> Callable[[type[T]], type[T]]:
    """Decorator to register a codelet class.

    Parameters
    ----------
    name : str | None
        Registration name (uses class name if None)

    Returns
    -------
    Callable
        Decorator function

    Examples
    --------
    >>> @codelet("my_codelet")
    ... class MyCodelet(AbstractCodelet):
    ...     def do_execute(self, context):
    ...         return CodeletResult.success_result()
    """

    def decorator(cls: type[T]) -> type[T]:
        registration_name = name if name else cls.__name__
        _global_registry.register_class(registration_name, cls)
        return cls

    return decorator


class FunctionCodelet:
    """Codelet wrapper for simple functions.

    Allows plain functions to be used as codelets.

    Parameters
    ----------
    func : Callable[[CodeletContext], CodeletResult]
        Function to wrap
    name : str
        Codelet name
    """

    def __init__(self, func: Callable[[CodeletContext], CodeletResult], name: str = "") -> None:
        """Initialize function codelet.

        Parameters
        ----------
        func : Callable[[CodeletContext], CodeletResult]
            Function to wrap
        name : str
            Codelet name
        """
        self.func = func
        self.name = name or func.__name__

    def execute(self, context: CodeletContext) -> CodeletResult:
        """Execute the wrapped function.

        Parameters
        ----------
        context : CodeletContext
            Execution context

        Returns
        -------
        CodeletResult
            Function result
        """
        return self.func(context)


def register_function(
    name: str | None = None, registry: CodeletRegistry | None = None
) -> Callable[[Callable[[CodeletContext], CodeletResult]], Callable[[CodeletContext], CodeletResult]]:
    """Decorator to register a function as a codelet.

    Parameters
    ----------
    name : str | None
        Registration name
    registry : CodeletRegistry | None
        Registry to use (global if None)

    Returns
    -------
    Callable
        Decorator function

    Examples
    --------
    >>> @register_function("calculate_total")
    ... def calculate_total(context: CodeletContext) -> CodeletResult:
    ...     total = sum(context.input_data.get("items", []))
    ...     return CodeletResult.success_result({"total": total})
    """
    target_registry = registry or _global_registry

    def decorator(func: Callable[[CodeletContext], CodeletResult]) -> Callable[[CodeletContext], CodeletResult]:
        registration_name = name if name else func.__name__
        codelet_instance = FunctionCodelet(func, registration_name)
        target_registry.register(registration_name, codelet_instance)
        return func

    return decorator
