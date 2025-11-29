"""Predicate parser utility for expression evaluation.

Parses strings, replacing substrings of the form ${expression} with the
result of expression evaluation.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

from kgcl.yawl.util.string_util import join


class YPredicateParser:
    """Parser for expressions in strings.

    Parses strings, replacing substrings of the form ${expression} with
    the result of expression evaluation. Subclasses can override value_of
    to handle custom expressions.

    Examples
    --------
    >>> parser = YPredicateParser()
    >>> parser.parse("Current time: ${now}")
    'Current time: 2024-01-01 12:00:00'
    """

    def __init__(self) -> None:
        """Initialize predicate parser."""
        pass

    def parse(self, s: str | None) -> str | None:
        """Parse a string, replacing ${expression} with evaluations.

        Parameters
        ----------
        s : str | None
            String to parse

        Returns
        -------
        str | None
            String with expressions replaced, or None if input is None
        """
        if s is None or "${" not in s:
            return s

        # Split on points immediately before "${" or after "}"
        # Pattern: (?=\$\{) matches position before "${"
        #          (?<=\}) matches position after "}"
        phrases = re.split(r"(?=\$\{)|(?<=\})", s)

        for i, phrase in enumerate(phrases):
            if self._is_delimited(phrase):
                try:
                    phrases[i] = self.value_of(phrase)
                except Exception:
                    phrases[i] = "n/a"

        return join(phrases, "")

    def value_of(self, s: str) -> str:
        """Evaluate an expression and return the result.

        Subclasses should override this method to handle custom expressions
        before calling this version for general expression evaluations.

        Parameters
        ----------
        s : str
            Expression string of the form ${expression}

        Returns
        -------
        str
            Result of expression evaluation, or unchanged string if
            expression is unrecognized
        """
        s_upper = s.upper()
        now_ms = int(datetime.now(UTC).timestamp() * 1000)

        if s_upper == "${NOW}":
            return self._date_time_string(now_ms)
        elif s_upper == "${DATE}":
            return datetime.now(UTC).strftime("%Y-%m-%d")
        elif s_upper == "${TIME}":
            return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]

        return s

    def _date_time_string(self, time_ms: int) -> str:
        """Convert time value to full date & time string.

        Parameters
        ----------
        time_ms : int
            Time in milliseconds since epoch

        Returns
        -------
        str
            Formatted date/time string
        """
        dt = datetime.fromtimestamp(time_ms / 1000.0, tz=UTC)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def get_attribute_value(self, map_data: dict[str, str] | None, s: str) -> str | None:
        """Extract key from expression and get value from map.

        Parameters
        ----------
        map_data : dict[str, str] | None
            Map of string pairs
        s : str
            Expression of form ${expression:key}

        Returns
        -------
        str | None
            Corresponding value, or None if map is None or key not found
        """
        if map_data is None:
            return None

        key = self._extract_key(self._strip_delimiters(s))
        return map_data.get(key)

    def names_to_csv(self, names: set[str] | None) -> str:
        """Transform set of strings into comma-separated values.

        Parameters
        ----------
        names : set[str] | None
            Set of strings to transform

        Returns
        -------
        str
            Comma-separated string, or "Nil" if set is None or empty
        """
        if not names:
            return "Nil"

        return ", ".join(names)

    def evaluate_query(self, s: str, data: Element | None) -> str:
        """Evaluate XQuery embedded in delimited expression.

        Parameters
        ----------
        s : str
            Delimited expression of form ${query} or ${expression:query}
        data : Element | None
            XML data that may be referenced by expression

        Returns
        -------
        str
            Evaluation result, or "__evaluation_error__" if evaluation fails
        """
        expression = self._strip_delimiters(s)
        if expression.startswith("expression:"):
            expression = self._extract_key(expression)

        return self._evaluate_xquery(expression, data)

    def _evaluate_xquery(self, s: str, data: Element | None) -> str:
        """Evaluate an XQuery expression.

        Parameters
        ----------
        s : str
            Query expression
        data : Element | None
            XML data

        Returns
        -------
        str
            Evaluation result, or "__evaluation_error__" if evaluation fails
        """
        try:
            from kgcl.yawl.util.misc.saxon_util import evaluate_query

            return evaluate_query(s, data)
        except ImportError:
            return "__evaluation_error__"

    def _strip_delimiters(self, s: str) -> str:
        """Remove surrounding ${...} from string.

        Parameters
        ----------
        s : str
            Delimited string

        Returns
        -------
        str
            Inner contents with delimiters removed
        """
        if s.startswith("${") and s.endswith("}"):
            return s[2:-1]
        return s

    def _extract_key(self, s: str) -> str:
        """Extract key part from expression of form "expression:key".

        Parameters
        ----------
        s : str
            String containing key

        Returns
        -------
        str
            Key part of string
        """
        last_colon = s.rfind(":")
        if last_colon != -1:
            return s[last_colon + 1 :]
        return s

    def _is_delimited(self, s: str) -> bool:
        """Check if string is a delimited expression.

        Parameters
        ----------
        s : str
            String to check

        Returns
        -------
        bool
            True if string is of form ${...}
        """
        return s.startswith("${") and s.endswith("}")


class YNetElementDocoParser(YPredicateParser):
    """Parser for net element documentation with XQuery support.

    Extends YPredicateParser to evaluate XQuery expressions against
    net data.

    Parameters
    ----------
    net_data : Element | None
        Net data document for XQuery evaluation
    """

    def __init__(self, net_data: Element | None) -> None:
        """Initialize net element documentation parser.

        Parameters
        ----------
        net_data : Element | None
            Net data document
        """
        super().__init__()
        self._data: Element | None = net_data

    def value_of(self, s: str) -> str:
        """Evaluate expression using XQuery against net data.

        Parameters
        ----------
        s : str
            Expression string

        Returns
        -------
        str
            Evaluation result
        """
        return self._evaluate_xquery(self._strip_delimiters(s), self._data)
