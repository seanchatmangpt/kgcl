"""Token marking for a net (mirrors Java YMarking).

Maps condition IDs to sets of token IDs currently at that condition.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class YMarking:
    """Token marking for a net (mirrors Java YMarking).

    The marking represents the current state of a workflow execution
    by mapping each condition (place) to the set of tokens currently
    residing there. This is the fundamental state representation in
    Petri net semantics.

    Parameters
    ----------
    _marking : dict[str, set[str]]
        Internal mapping of condition_id → token_ids

    Examples
    --------
    >>> marking = YMarking()
    >>> marking.add_token("start", "token-1")
    >>> marking.has_tokens("start")
    True
    >>> marking.token_count("start")
    1
    """

    _marking: dict[str, set[str]] = field(default_factory=dict)

    def add_token(self, condition_id: str, token_id: str) -> None:
        """Add token to condition.

        Parameters
        ----------
        condition_id : str
            ID of condition to add token to
        token_id : str
            ID of token to add

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> "t1" in marking.get_tokens("c1")
        True
        """
        if condition_id not in self._marking:
            self._marking[condition_id] = set()
        self._marking[condition_id].add(token_id)

    def remove_token(self, condition_id: str, token_id: str) -> bool:
        """Remove specific token from condition.

        Parameters
        ----------
        condition_id : str
            ID of condition
        token_id : str
            ID of token to remove

        Returns
        -------
        bool
            True if token was present and removed

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.remove_token("c1", "t1")
        True
        >>> marking.has_tokens("c1")
        False
        """
        if condition_id in self._marking:
            if token_id in self._marking[condition_id]:
                self._marking[condition_id].discard(token_id)
                return True
        return False

    def remove_one_token(self, condition_id: str) -> str | None:
        """Remove and return one token from condition.

        Parameters
        ----------
        condition_id : str
            ID of condition

        Returns
        -------
        str | None
            Token ID that was removed, or None if empty

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.remove_one_token("c1")
        't1'
        >>> marking.remove_one_token("c1") is None
        True
        """
        if self._marking.get(condition_id):
            return self._marking[condition_id].pop()
        return None

    def has_tokens(self, condition_id: str) -> bool:
        """Check if condition has any tokens.

        Parameters
        ----------
        condition_id : str
            ID of condition

        Returns
        -------
        bool
            True if condition has at least one token

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.has_tokens("c1")
        False
        >>> marking.add_token("c1", "t1")
        >>> marking.has_tokens("c1")
        True
        """
        return bool(self._marking.get(condition_id))

    def get_tokens(self, condition_id: str) -> set[str]:
        """Get all token IDs at condition.

        Parameters
        ----------
        condition_id : str
            ID of condition

        Returns
        -------
        set[str]
            Copy of token IDs at condition

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.add_token("c1", "t2")
        >>> marking.get_tokens("c1") == {"t1", "t2"}
        True
        """
        return self._marking.get(condition_id, set()).copy()

    def token_count(self, condition_id: str) -> int:
        """Count tokens at condition.

        Parameters
        ----------
        condition_id : str
            ID of condition

        Returns
        -------
        int
            Number of tokens at condition

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.add_token("c1", "t2")
        >>> marking.token_count("c1")
        2
        """
        return len(self._marking.get(condition_id, set()))

    def total_token_count(self) -> int:
        """Count total tokens across all conditions.

        Returns
        -------
        int
            Total number of tokens

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.add_token("c2", "t2")
        >>> marking.total_token_count()
        2
        """
        return sum(len(tokens) for tokens in self._marking.values())

    def is_empty(self) -> bool:
        """Check if marking has no tokens anywhere.

        Returns
        -------
        bool
            True if no tokens in any condition

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.is_empty()
        True
        >>> marking.add_token("c1", "t1")
        >>> marking.is_empty()
        False
        """
        return all(len(tokens) == 0 for tokens in self._marking.values())

    def get_marked_conditions(self) -> list[str]:
        """Get IDs of all conditions with tokens.

        Returns
        -------
        list[str]
            Condition IDs with at least one token

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.add_token("c2", "t2")
        >>> set(marking.get_marked_conditions()) == {"c1", "c2"}
        True
        """
        return [cid for cid, tokens in self._marking.items() if tokens]

    def clear(self) -> None:
        """Remove all tokens from all conditions.

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> marking.clear()
        >>> marking.is_empty()
        True
        """
        self._marking.clear()

    def copy(self) -> YMarking:
        """Create a deep copy of this marking.

        Returns
        -------
        YMarking
            New marking with same tokens

        Examples
        --------
        >>> marking = YMarking()
        >>> marking.add_token("c1", "t1")
        >>> copy = marking.copy()
        >>> marking.remove_token("c1", "t1")
        True
        >>> copy.has_tokens("c1")
        True
        """
        new_marking = YMarking()
        for cid, tokens in self._marking.items():
            new_marking._marking[cid] = tokens.copy()
        return new_marking

    def __repr__(self) -> str:
        """String representation showing marked conditions."""
        marked = {k: v for k, v in self._marking.items() if v}
        return f"YMarking({marked})"
