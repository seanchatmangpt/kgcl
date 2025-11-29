"""N3 Rule Parser for KGC Hybrid Engine.

Parses N3-style logical rules from `{ premise } => { conclusion }` syntax
into structured N3Rule dataclass objects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class N3Rule:
    """N3 logical rule representation.

    Parameters
    ----------
    uri : str
        Rule identifier (e.g., 'kgcl:rule/task-pending-to-running')
    signature : str
        Verb type: Transmute, Filter, Copy, Await, Void
    premise : str
        The "IF" part containing WHERE clause conditions
    conclusion : str
        The "THEN" part containing mutations to apply
    deletions : tuple[str, ...]
        Triples to delete from graph
    insertions : tuple[str, ...]
        Triples to insert into graph

    Examples
    --------
    >>> rule = N3Rule(
    ...     uri="kgcl:rule/example",
    ...     signature="Transmute",
    ...     premise='?task a kgcl:Task ; kgcl:status "pending"',
    ...     conclusion='?task kgcl:status "running"',
    ...     deletions=('?task kgcl:status "pending"',),
    ...     insertions=('?task kgcl:status "running"',),
    ... )
    >>> rule.signature
    'Transmute'
    """

    uri: str
    signature: str
    premise: str
    conclusion: str
    deletions: tuple[str, ...]
    insertions: tuple[str, ...]


class N3Parser:
    """Parser for N3-style logical rules.

    Converts N3 rule syntax `{ premise } => { conclusion }` into
    structured N3Rule objects with extracted triples.

    Methods
    -------
    parse(rule_text: str, uri: str, signature: str) -> N3Rule
        Parse N3 rule text into N3Rule object
    extract_triples(text: str) -> list[str]
        Extract individual triples from N3 text block
    identify_mutations(premise_triples: list[str], conclusion_triples: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]
        Identify which triples are deletions vs insertions

    Examples
    --------
    >>> parser = N3Parser()
    >>> rule = parser.parse(
    ...     '{ ?task a kgcl:Task ; kgcl:status "pending" } => { ?task kgcl:status "running" }',
    ...     uri="kgcl:rule/example",
    ...     signature="Transmute",
    ... )
    >>> rule.signature
    'Transmute'
    """

    def __init__(self) -> None:
        """Initialize N3 parser with regex patterns."""
        # Pattern to split premise and conclusion
        self.rule_pattern = re.compile(r"\{\s*(.+?)\s*\}\s*=>\s*\{\s*(.+?)\s*\}", re.DOTALL)

        # Pattern to extract prefix declarations
        self.prefix_pattern = re.compile(r"@prefix\s+(\w+):\s*<([^>]+)>\s*\.", re.MULTILINE)

    def parse(self, rule_text: str, uri: str, signature: str) -> N3Rule:
        """Parse N3 rule text into structured N3Rule object.

        Parameters
        ----------
        rule_text : str
            N3 rule in format `{ premise } => { conclusion }`
        uri : str
            Rule identifier (e.g., 'kgcl:rule/task-transmute')
        signature : str
            Verb type: Transmute, Filter, Copy, Await, Void

        Returns
        -------
        N3Rule
            Parsed rule with extracted triples

        Raises
        ------
        ValueError
            If rule_text does not match N3 syntax

        Examples
        --------
        >>> parser = N3Parser()
        >>> rule = parser.parse(
        ...     "{ ?x a kgcl:Task } => { ?x kgcl:done true }", uri="kgcl:rule/mark-done", signature="Transmute"
        ... )
        >>> len(rule.insertions)
        1
        """
        # Strip prefix declarations (they don't affect N3 rule body parsing)
        cleaned_text = self.prefix_pattern.sub("", rule_text).strip()

        # Extract premise and conclusion
        match = self.rule_pattern.search(cleaned_text)
        if not match:
            msg = f"Invalid N3 rule syntax: {rule_text}"
            raise ValueError(msg)

        premise_text = match.group(1).strip()
        conclusion_text = match.group(2).strip()

        # Extract triples from both parts
        premise_triples = self.extract_triples(premise_text)
        conclusion_triples = self.extract_triples(conclusion_text)

        # Identify mutations (deletions and insertions)
        deletions, insertions = self.identify_mutations(premise_triples, conclusion_triples)

        return N3Rule(
            uri=uri,
            signature=signature,
            premise=premise_text,
            conclusion=conclusion_text,
            deletions=deletions,
            insertions=insertions,
        )

    def extract_triples(self, text: str) -> list[str]:
        """Extract individual triples from N3 text block.

        Handles both full triple syntax and semicolon-separated predicates.

        Parameters
        ----------
        text : str
            N3 text block containing triples

        Returns
        -------
        list[str]
            List of individual triples

        Examples
        --------
        >>> parser = N3Parser()
        >>> triples = parser.extract_triples('?x a kgcl:Task ; kgcl:status "pending"')
        >>> len(triples)
        2
        """
        triples: list[str] = []

        # Normalize whitespace
        normalized = " ".join(text.split())

        # Split by period (statement separator)
        statements = [s.strip() for s in normalized.split(".") if s.strip()]

        for stmt in statements:
            # Handle semicolon-separated predicates (shared subject)
            if ";" in stmt:
                parts = [p.strip() for p in stmt.split(";")]
                # First part has subject + predicate + object
                first_triple = parts[0]
                triples.append(first_triple)

                # Extract subject from first triple
                subject_match = re.match(r"(\S+)\s+", first_triple)
                if subject_match:
                    subject = subject_match.group(1)
                    # Remaining parts are predicate + object pairs
                    for part in parts[1:]:
                        if part.strip():
                            triple = f"{subject} {part.strip()}"
                            triples.append(triple)
            # Single triple
            elif stmt.strip():
                triples.append(stmt.strip())

        return triples

    def identify_mutations(
        self, premise_triples: list[str], conclusion_triples: list[str]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Identify which triples are deletions vs insertions.

        Compares premise and conclusion triples to determine mutations.
        Triples in premise but not conclusion are deletions.
        Triples in conclusion but not premise are insertions.

        Parameters
        ----------
        premise_triples : list[str]
            Triples from premise (IF part)
        conclusion_triples : list[str]
            Triples from conclusion (THEN part)

        Returns
        -------
        tuple[tuple[str, ...], tuple[str, ...]]
            (deletions, insertions) tuple

        Examples
        --------
        >>> parser = N3Parser()
        >>> premise = ['?x kgcl:status "pending"']
        >>> conclusion = ['?x kgcl:status "running"']
        >>> deletions, insertions = parser.identify_mutations(premise, conclusion)
        >>> len(deletions)
        1
        >>> len(insertions)
        1
        """
        # Normalize triples for comparison
        premise_set = {self._normalize_triple(t) for t in premise_triples}
        conclusion_set = {self._normalize_triple(t) for t in conclusion_triples}

        # Deletions: in premise but not in conclusion
        deletions_set = premise_set - conclusion_set

        # Insertions: in conclusion but not in premise
        insertions_set = conclusion_set - premise_set

        return (tuple(sorted(deletions_set)), tuple(sorted(insertions_set)))

    def _normalize_triple(self, triple: str) -> str:
        """Normalize triple for comparison.

        Parameters
        ----------
        triple : str
            Triple to normalize

        Returns
        -------
        str
            Normalized triple with consistent whitespace

        Examples
        --------
        >>> parser = N3Parser()
        >>> parser._normalize_triple("  ?x   a   kgcl:Task  ")
        '?x a kgcl:Task'
        """
        return " ".join(triple.split())


# =============================================================================
# Chicago School TDD Tests
# =============================================================================


def test_n3_rule_frozen() -> None:
    """Verify N3Rule is immutable (frozen dataclass)."""
    rule = N3Rule(
        uri="test:rule",
        signature="Transmute",
        premise="?x a kgcl:Task",
        conclusion="?x kgcl:done true",
        deletions=(),
        insertions=("?x kgcl:done true",),
    )

    try:
        rule.uri = "changed"  # type: ignore[misc]
        msg = "N3Rule should be frozen"
        raise AssertionError(msg)
    except AttributeError:
        pass  # Expected - frozen dataclass


def test_parse_simple_rule() -> None:
    """Parse simple N3 rule with single premise and conclusion."""
    parser = N3Parser()
    rule_text = "{ ?task a kgcl:Task } => { ?task kgcl:processed true }"

    rule = parser.parse(rule_text, uri="test:simple", signature="Transmute")

    assert rule.uri == "test:simple"
    assert rule.signature == "Transmute"
    assert "?task a kgcl:Task" in rule.premise
    assert "?task kgcl:processed true" in rule.conclusion
    assert len(rule.insertions) == 1
    assert "?task kgcl:processed true" in rule.insertions


def test_parse_status_change_rule() -> None:
    """Parse rule with status mutation (deletion + insertion)."""
    parser = N3Parser()
    rule_text = """
    {
        ?task a kgcl:Task ;
              kgcl:status "pending" .
    }
    =>
    {
        ?task kgcl:status "running" .
    }
    """

    rule = parser.parse(rule_text, uri="test:status", signature="Transmute")

    assert len(rule.deletions) == 1
    assert len(rule.insertions) == 1
    assert any('status "pending"' in d for d in rule.deletions)
    assert any('status "running"' in i for i in rule.insertions)


def test_extract_triples_simple() -> None:
    """Extract triples from simple N3 text."""
    parser = N3Parser()
    text = "?x a kgcl:Task"

    triples = parser.extract_triples(text)

    assert len(triples) == 1
    assert triples[0] == "?x a kgcl:Task"


def test_extract_triples_semicolon() -> None:
    """Extract triples with semicolon-separated predicates."""
    parser = N3Parser()
    text = '?task a kgcl:Task ; kgcl:status "pending" ; kgcl:priority 5'

    triples = parser.extract_triples(text)

    assert len(triples) == 3
    assert any("a kgcl:Task" in t for t in triples)
    assert any('status "pending"' in t for t in triples)
    assert any("priority 5" in t for t in triples)


def test_extract_triples_multiline() -> None:
    """Extract triples from multi-line N3 text."""
    parser = N3Parser()
    text = """
        ?task a kgcl:Task ;
              kgcl:status "pending" .
        ?flow a kgcl:Flow .
    """

    triples = parser.extract_triples(text)

    assert len(triples) >= 2
    assert any("?task" in t and "kgcl:Task" in t for t in triples)
    assert any("?flow" in t and "kgcl:Flow" in t for t in triples)


def test_identify_mutations_status_change() -> None:
    """Identify deletions and insertions for status change."""
    parser = N3Parser()
    premise = ['?task kgcl:status "pending"', "?task a kgcl:Task"]
    conclusion = ['?task kgcl:status "running"', "?task a kgcl:Task"]

    deletions, insertions = parser.identify_mutations(premise, conclusion)

    assert len(deletions) == 1
    assert len(insertions) == 1
    assert '?task kgcl:status "pending"' in deletions
    assert '?task kgcl:status "running"' in insertions


def test_identify_mutations_no_change() -> None:
    """Identify mutations when premise equals conclusion."""
    parser = N3Parser()
    premise = ["?task a kgcl:Task", '?task kgcl:id "123"']
    conclusion = ["?task a kgcl:Task", '?task kgcl:id "123"']

    deletions, insertions = parser.identify_mutations(premise, conclusion)

    assert len(deletions) == 0
    assert len(insertions) == 0


def test_identify_mutations_only_insertions() -> None:
    """Identify mutations with only new triples."""
    parser = N3Parser()
    premise = ["?task a kgcl:Task"]
    conclusion = ["?task a kgcl:Task", "?task kgcl:done true"]

    deletions, insertions = parser.identify_mutations(premise, conclusion)

    assert len(deletions) == 0
    assert len(insertions) == 1
    assert "?task kgcl:done true" in insertions


def test_normalize_triple_whitespace() -> None:
    """Normalize triple with irregular whitespace."""
    parser = N3Parser()
    triple = "  ?x   a   kgcl:Task  "

    normalized = parser._normalize_triple(triple)

    assert normalized == "?x a kgcl:Task"


def test_parse_with_prefixes() -> None:
    """Parse rule with @prefix declarations."""
    parser = N3Parser()
    rule_text = """
    @prefix kgcl: <http://example.org/kgcl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

    { ?task a kgcl:Task } => { ?task kgcl:done true }
    """

    rule = parser.parse(rule_text, uri="test:prefix", signature="Transmute")

    assert rule.uri == "test:prefix"
    assert "?task a kgcl:Task" in rule.premise


def test_parse_invalid_syntax_raises() -> None:
    """Parse invalid N3 syntax raises ValueError."""
    parser = N3Parser()
    invalid_text = "not a valid rule"

    try:
        parser.parse(invalid_text, uri="test:invalid", signature="Transmute")
        msg = "Should raise ValueError for invalid syntax"
        raise AssertionError(msg)
    except ValueError as e:
        assert "Invalid N3 rule syntax" in str(e)


def test_parse_filter_signature() -> None:
    """Parse rule with Filter signature."""
    parser = N3Parser()
    rule_text = "{ ?task kgcl:priority ?p } => { ?task kgcl:highPriority true }"

    rule = parser.parse(rule_text, uri="test:filter", signature="Filter")

    assert rule.signature == "Filter"
    assert len(rule.insertions) == 1


def test_parse_complex_rule() -> None:
    """Parse complex rule with multiple premises and conclusions."""
    parser = N3Parser()
    rule_text = """
    {
        ?task a kgcl:Task ;
              kgcl:status "pending" ;
              kgcl:flow ?flow .
        ?flow a kgcl:Flow ;
              kgcl:active true .
    }
    =>
    {
        ?task kgcl:status "running" ;
              kgcl:startTime ?now .
    }
    """

    rule = parser.parse(rule_text, uri="test:complex", signature="Transmute")

    assert len(rule.deletions) >= 1
    assert len(rule.insertions) >= 1
    assert any('status "pending"' in d for d in rule.deletions)
    assert any('status "running"' in i for i in rule.insertions)


def test_n3_rule_all_signatures() -> None:
    """Verify all verb signatures can be assigned."""
    signatures = ["Transmute", "Filter", "Copy", "Await", "Void"]

    for sig in signatures:
        rule = N3Rule(
            uri=f"test:{sig.lower()}",
            signature=sig,
            premise="?x a kgcl:Task",
            conclusion="?x kgcl:done true",
            deletions=(),
            insertions=("?x kgcl:done true",),
        )
        assert rule.signature == sig


if __name__ == "__main__":
    # Run all tests
    test_n3_rule_frozen()
    test_parse_simple_rule()
    test_parse_status_change_rule()
    test_extract_triples_simple()
    test_extract_triples_semicolon()
    test_extract_triples_multiline()
    test_identify_mutations_status_change()
    test_identify_mutations_no_change()
    test_identify_mutations_only_insertions()
    test_normalize_triple_whitespace()
    test_parse_with_prefixes()
    test_parse_invalid_syntax_raises()
    test_parse_filter_signature()
    test_parse_complex_rule()
    test_n3_rule_all_signatures()

    print("✓ All N3 parser tests passed")
