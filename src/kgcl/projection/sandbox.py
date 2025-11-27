"""Sandboxed Jinja environment for secure template rendering.

Provides KGCLSandboxedEnvironment with strict security controls:
- Blocks dangerous attributes (__class__, __subclasses__, etc.)
- Blocks dangerous modules (os, sys, subprocess, eval, exec)
- Provides safe globals and filters for RDF template projection
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from jinja2.sandbox import ImmutableSandboxedEnvironment

from kgcl.projection.filters.rdf_filters import RDF_FILTERS
from kgcl.projection.filters.safe_filters import SAFE_FILTERS
from kgcl.projection.filters.type_mapping import TYPE_MAPPING_FILTERS

__all__ = ["KGCLSandboxedEnvironment", "create_projection_environment"]


class KGCLSandboxedEnvironment(ImmutableSandboxedEnvironment):
    """Enhanced sandboxed Jinja environment with security restrictions.

    Blocks dangerous attributes and provides safe globals/filters
    for RDF template projection.

    Parameters
    ----------
    **kwargs
        Additional arguments passed to ImmutableSandboxedEnvironment

    Examples
    --------
    >>> env = KGCLSandboxedEnvironment()
    >>> template = env.from_string("{{ value | upper }}")
    >>> template.render(value="hello")
    'HELLO'

    Notes
    -----
    This environment blocks:
    - Dunder attributes (__class__, __subclasses__, etc.)
    - Dangerous modules (os, sys, subprocess)
    - Dangerous builtins (eval, exec, compile, open)
    """

    BLOCKED_ATTRIBUTES: frozenset[str] = frozenset(
        {
            "__class__",
            "__subclasses__",
            "__mro__",
            "__bases__",
            "__globals__",
            "__builtins__",
            "__code__",
            "__reduce__",
            "__reduce_ex__",
            "__getattribute__",
            "__setattr__",
            "__delattr__",
            "__init__",
            "__new__",
            "__repr__",
            "__dict__",
            "__doc__",
            "__module__",
            "__weakref__",
        }
    )

    BLOCKED_MODULES: frozenset[str] = frozenset({"os", "sys", "subprocess", "importlib", "__import__"})

    BLOCKED_BUILTINS: frozenset[str] = frozenset(
        {
            "eval",
            "exec",
            "compile",
            "open",
            "__import__",
            "globals",
            "locals",
            "vars",
            "dir",
            "getattr",
            "setattr",
            "delattr",
        }
    )

    SAFE_GLOBALS: dict[str, Any] = {
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "sorted": sorted,
        "min": min,
        "max": max,
        "sum": sum,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "isinstance": isinstance,
        "hasattr": hasattr,
        "zip": zip,
        "map": map,
        "filter": filter,
        "True": True,
        "False": False,
        "None": None,
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize sandboxed environment with safe filters.

        Parameters
        ----------
        **kwargs
            Additional arguments passed to parent class
        """
        super().__init__(**kwargs)

        # Add all safe filters
        self.filters.update(SAFE_FILTERS)
        self.filters.update(RDF_FILTERS)
        self.filters.update(TYPE_MAPPING_FILTERS)

        # Add safe globals
        self.globals.update(self.SAFE_GLOBALS)

    def is_safe_attribute(self, obj: Any, attr: str, value: Any) -> bool:
        """Check if attribute access is safe.

        Parameters
        ----------
        obj : Any
            Object being accessed
        attr : str
            Attribute name
        value : Any
            Attribute value

        Returns
        -------
        bool
            True if attribute access is safe

        Notes
        -----
        Blocks all attributes in BLOCKED_ATTRIBUTES set.
        """
        # Block dangerous dunder attributes - this must come first
        if attr in self.BLOCKED_ATTRIBUTES:
            return False

        # Block access to dangerous modules
        if hasattr(obj, "__name__"):
            try:
                name = obj.__name__
                if name in self.BLOCKED_MODULES:
                    return False
            except AttributeError:
                pass

        # Use parent class's safety check
        return super().is_safe_attribute(obj, attr, value)

    def getattr(self, obj: Any, attribute: str) -> Any:
        """Get attribute with security checks.

        Parameters
        ----------
        obj : Any
            Object to get attribute from
        attribute : str
            Attribute name

        Returns
        -------
        Any
            Attribute value

        Raises
        ------
        SecurityError
            If attribute access is not safe
        """
        # Block dangerous attributes
        if attribute in self.BLOCKED_ATTRIBUTES:
            from jinja2.exceptions import SecurityError

            raise SecurityError(f"Access to attribute '{attribute}' is not allowed")

        # Use parent's getattr which includes safety checks
        return super().getattr(obj, attribute)

    def is_safe_callable(self, obj: Any) -> bool:
        """Check if callable is safe to execute.

        Parameters
        ----------
        obj : Any
            Callable object

        Returns
        -------
        bool
            True if callable is safe

        Notes
        -----
        Blocks all callables in BLOCKED_BUILTINS set.
        """
        # Block dangerous builtins
        if hasattr(obj, "__name__") and obj.__name__ in self.BLOCKED_BUILTINS:
            return False

        # Block access to type constructors that could be dangerous
        if obj in {type, object, property}:
            return False

        # Use parent class's safety check
        return super().is_safe_callable(obj)


def create_projection_environment(
    extra_filters: dict[str, Callable[..., Any]] | None = None, extra_globals: dict[str, Any] | None = None
) -> KGCLSandboxedEnvironment:
    """Factory to create configured projection environment.

    Parameters
    ----------
    extra_filters : dict[str, Callable[..., Any]] | None
        Additional custom filters to add
    extra_globals : dict[str, Any] | None
        Additional global variables to add

    Returns
    -------
    KGCLSandboxedEnvironment
        Configured sandboxed environment

    Examples
    --------
    >>> def custom_filter(value: str) -> str:
    ...     return value.upper()
    >>> env = create_projection_environment(extra_filters={"custom": custom_filter}, extra_globals={"VERSION": "1.0.0"})
    >>> template = env.from_string("{{ VERSION }}: {{ value | custom }}")
    >>> template.render(value="hello")
    '1.0.0: HELLO'
    """
    env = KGCLSandboxedEnvironment()

    # Add extra filters if provided
    if extra_filters:
        env.filters.update(extra_filters)

    # Add extra globals if provided
    if extra_globals:
        env.globals.update(extra_globals)

    return env
