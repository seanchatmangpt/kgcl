"""RulesProvider - Protocol for providing physics rules.

This module defines the abstract interface for N3 rules providers.
The hybrid engine depends on this protocol for getting physics rules.

Examples
--------
>>> from kgcl.hybrid.ports.rules_port import RulesProvider
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RulesProvider(Protocol):
    """Protocol for providing N3 physics rules.

    This protocol defines the interface for components that provide
    N3 rules for the hybrid engine. The primary implementation wraps
    the WCP43_COMPLETE_PHYSICS constant.

    Methods
    -------
    get_rules()
        Get the complete N3 physics rules.
    get_rule_subset(pattern_ids)
        Get rules for specific WCP pattern IDs.

    Examples
    --------
    Any class implementing this protocol can be used:

    >>> class SimpleRulesProvider:
    ...     def get_rules(self) -> str:
    ...         return "@prefix ex: <http://example.org/> . { ?x a ex:Task } => { ?x ex:processed true } ."
    ...
    ...     def get_rule_subset(self, pattern_ids: list[int]) -> str:
    ...         return self.get_rules()  # Simple impl returns all rules
    """

    def get_rules(self) -> str:
        """Get the complete N3 physics rules.

        Returns the full set of N3 rules for workflow physics.
        This includes all WCP patterns and supporting rules.

        Returns
        -------
        str
            Complete N3 rules string.
        """
        ...

    def get_rule_subset(self, pattern_ids: list[int]) -> str:
        """Get rules for specific WCP pattern IDs.

        Enables selective rule loading for testing or
        performance optimization.

        Parameters
        ----------
        pattern_ids : list[int]
            WCP pattern numbers (1-43) to include.

        Returns
        -------
        str
            N3 rules for specified patterns only.
        """
        ...
