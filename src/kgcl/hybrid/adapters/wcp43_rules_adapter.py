"""WCP43RulesAdapter - Wraps wcp43_physics to implement RulesProvider protocol.

This adapter provides the RulesProvider interface using the WCP43_COMPLETE_PHYSICS
constant and helper functions from wcp43_physics.py.

Examples
--------
>>> adapter = WCP43RulesAdapter()
>>> rules = adapter.get_rules()
>>> "WCP-1" in rules
True
"""

from __future__ import annotations

import logging

from kgcl.hybrid.wcp43_physics import STANDARD_PREFIXES, WCP43_COMPLETE_PHYSICS, get_pattern_rule

logger = logging.getLogger(__name__)


class WCP43RulesAdapter:
    """Adapter wrapping wcp43_physics to implement RulesProvider protocol.

    This adapter provides access to the complete WCP-43 physics rules,
    with support for selective rule loading.

    Attributes
    ----------
    full_rules : str
        The complete WCP-43 physics rules.

    Examples
    --------
    Get complete rules:

    >>> adapter = WCP43RulesAdapter()
    >>> rules = adapter.get_rules()
    >>> len(rules) > 1000
    True
    >>> "WCP-1" in rules
    True

    Get rules for specific patterns:

    >>> subset = adapter.get_rule_subset([1, 2, 3])
    >>> "WCP-1" in subset
    True
    >>> "WCP-43" in subset
    False
    """

    def __init__(self) -> None:
        """Initialize WCP43RulesAdapter."""
        self.full_rules = WCP43_COMPLETE_PHYSICS
        logger.info("WCP43RulesAdapter initialized with complete physics")

    def get_rules(self) -> str:
        """Get the complete N3 physics rules.

        Returns the full set of WCP-43 physics rules for workflow
        control pattern processing.

        Returns
        -------
        str
            Complete N3 rules string (all 43 WCP patterns).

        Examples
        --------
        >>> adapter = WCP43RulesAdapter()
        >>> rules = adapter.get_rules()
        >>> "WCP-1" in rules
        True
        >>> "SEQUENCE" in rules
        True
        """
        return self.full_rules

    def get_rule_subset(self, pattern_ids: list[int]) -> str:
        """Get rules for specific WCP pattern IDs.

        Enables selective rule loading for testing specific patterns
        or optimizing performance by excluding unused patterns.

        Parameters
        ----------
        pattern_ids : list[int]
            WCP pattern numbers (1-43) to include.

        Returns
        -------
        str
            N3 rules for specified patterns only (with prefixes).

        Examples
        --------
        Get just basic control flow patterns:

        >>> adapter = WCP43RulesAdapter()
        >>> subset = adapter.get_rule_subset([1, 2, 3, 4, 5])
        >>> "WCP-1" in subset
        True
        >>> "WCP-43" in subset
        False

        Empty list returns just prefixes:

        >>> subset = adapter.get_rule_subset([])
        >>> "@prefix" in subset
        True
        """
        rules_parts = [STANDARD_PREFIXES]

        for pattern_id in pattern_ids:
            rule = get_pattern_rule(pattern_id)
            if rule is not None:
                rules_parts.append(rule)
            else:
                logger.warning(f"Pattern WCP-{pattern_id} not found, skipping")

        return "\n".join(rules_parts)

    def get_basic_patterns(self) -> str:
        """Get rules for basic control flow patterns (WCP 1-5).

        Convenience method for common use case of just basic patterns.

        Returns
        -------
        str
            N3 rules for WCP 1-5.

        Examples
        --------
        >>> adapter = WCP43RulesAdapter()
        >>> basic = adapter.get_basic_patterns()
        >>> "SEQUENCE" in basic
        True
        >>> "PARALLEL SPLIT" in basic
        True
        """
        return self.get_rule_subset([1, 2, 3, 4, 5])

    def get_join_patterns(self) -> str:
        """Get rules for join/synchronization patterns.

        Returns rules for AND-join, OR-join, and discriminator patterns.

        Returns
        -------
        str
            N3 rules for join patterns.

        Examples
        --------
        >>> adapter = WCP43RulesAdapter()
        >>> joins = adapter.get_join_patterns()
        >>> "SYNCHRONIZATION" in joins or "AND-JOIN" in joins
        True
        """
        return self.get_rule_subset([3, 5, 7, 9, 28, 29, 30, 31, 32, 33])

    def get_cancellation_patterns(self) -> str:
        """Get rules for cancellation patterns (WCP 19-20, 25-27).

        Returns rules for task and case cancellation.

        Returns
        -------
        str
            N3 rules for cancellation patterns.

        Examples
        --------
        >>> adapter = WCP43RulesAdapter()
        >>> cancel = adapter.get_cancellation_patterns()
        >>> "CANCEL" in cancel
        True
        """
        return self.get_rule_subset([19, 20, 25, 26, 27])
