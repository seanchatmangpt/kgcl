"""Tests for N3 rule parser.

This module tests the N3 rule parsing logic that converts N3 notation
rules into Python datastructures for the KGC hybrid engine.
"""

from dataclasses import FrozenInstanceError

import pytest

from kgcl.hybrid.n3_parser import N3Parser, N3Rule

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def simple_rule() -> str:
    """Simple N3 rule with single triple in premise and conclusion.

    Returns
    -------
    str
        N3 rule text with basic A => B structure.
    """
    return """
    {
        ?task unrdf:requiresInput ?inputType .
    } => {
        ?task unrdf:status "ready" .
    } .
    """


@pytest.fixture
def multi_triple_premise() -> str:
    """N3 rule with multiple triples in WHERE clause.

    Returns
    -------
    str
        N3 rule with complex premise.
    """
    return """
    {
        ?capability unrdf:tier tier:Essential .
        ?capability unrdf:status "available" .
        ?capability unrdf:dependencies ?depList .
    } => {
        ?capability unrdf:availabilityLevel "core" .
    } .
    """


@pytest.fixture
def multi_triple_conclusion() -> str:
    """N3 rule with multiple mutations in conclusion.

    Returns
    -------
    str
        N3 rule with multiple conclusion triples.
    """
    return """
    {
        ?capability unrdf:tier tier:Essential .
    } => {
        ?capability unrdf:availabilityLevel "core" .
        ?capability unrdf:loadPriority 1 .
        ?capability unrdf:status "ready" .
    } .
    """


@pytest.fixture
def rule_with_prefixes() -> str:
    """N3 rule with SPARQL prefix declarations.

    Returns
    -------
    str
        Complete N3 document with prefixes and rule.
    """
    return """
    @prefix unrdf: <https://unrdf.org/schema/> .
    @prefix tier: <https://unrdf.org/tier/> .

    {
        ?capability unrdf:tier tier:Essential .
    } => {
        ?capability unrdf:availabilityLevel "core" .
    } .
    """


@pytest.fixture
def whitespace_variations() -> str:
    """N3 rule with various whitespace (tabs, newlines, spaces).

    Returns
    -------
    str
        N3 rule with mixed whitespace formatting.
    """
    return """{
    \t?task   unrdf:requiresInput\t\t?inputType.
    } =>{
        ?task unrdf:status\t"ready"   .
    }.
    """


@pytest.fixture
def invalid_rule() -> str:
    """Invalid N3 rule syntax.

    Returns
    -------
    str
        Malformed N3 rule text.
    """
    return """
    {
        ?task unrdf:requiresInput ?inputType
    } =>
        ?task unrdf:status "ready"
    """


@pytest.fixture
def parser() -> N3Parser:
    """N3Parser instance.

    Returns
    -------
    N3Parser
        Fresh parser instance.
    """
    return N3Parser()


# ============================================================================
# N3Rule Dataclass Tests
# ============================================================================


def test_n3rule_is_frozen() -> None:
    """Test N3Rule dataclass is immutable (frozen).

    Verifies that N3Rule uses @dataclass(frozen=True) to enforce
    immutability of parsed rule data.
    """
    rule = N3Rule(
        uri="test:rule/example",
        signature="Transmute",
        premise="?x rdf:type unrdf:Task",
        conclusion="?x unrdf:status 'ready'",
        deletions=(),
        insertions=("?x unrdf:status 'ready'",),
    )

    with pytest.raises(FrozenInstanceError):
        rule.premise = ""  # type: ignore[misc]


def test_n3rule_all_fields_populated() -> None:
    """Test N3Rule has all required fields populated correctly.

    Verifies that all N3Rule fields are present and contain expected
    data types.
    """
    uri = "test:rule/example"
    signature = "Transmute"
    premise = "?task unrdf:requiresInput ?inputType"
    conclusion = "?task unrdf:status 'ready'"
    deletions = ("?task unrdf:requiresInput ?inputType",)
    insertions = ("?task unrdf:status 'ready'",)

    rule = N3Rule(
        uri=uri, signature=signature, premise=premise, conclusion=conclusion, deletions=deletions, insertions=insertions
    )

    assert rule.uri == uri
    assert rule.signature == signature
    assert rule.premise == premise
    assert rule.conclusion == conclusion
    assert rule.deletions == deletions
    assert rule.insertions == insertions


def test_n3rule_empty_tuples_allowed() -> None:
    """Test N3Rule allows empty deletions/insertions tuples.

    Edge case: Some rules may have only insertions or only deletions.
    N3Rule should accept these without raising errors.
    """
    rule = N3Rule(uri="test:rule/empty", signature="Transmute", premise="", conclusion="", deletions=(), insertions=())

    assert rule.deletions == ()
    assert rule.insertions == ()


# ============================================================================
# N3Parser Basic Parsing Tests
# ============================================================================


def test_parse_simple_sequence_rule(parser: N3Parser, simple_rule: str) -> None:
    """Test parsing of basic A => B rule.

    Verifies parser extracts premise, conclusion from simple N3 rule.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    simple_rule : str
        Simple N3 rule fixture.
    """
    result = parser.parse(simple_rule, uri="test:rule/simple", signature="Transmute")

    assert result is not None
    assert "requiresInput" in result.premise
    assert "status" in result.conclusion
    assert len(result.insertions) >= 1


def test_parse_multi_triple_premise(parser: N3Parser, multi_triple_premise: str) -> None:
    """Test parsing complex WHERE clause with multiple triples.

    Verifies parser correctly extracts all triples from premise section
    when rule has multiple conditions.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    multi_triple_premise : str
        Rule with complex premise.
    """
    result = parser.parse(multi_triple_premise, uri="test:rule/multi", signature="Filter")

    assert result is not None
    # Verify all premise content is present
    assert "tier:Essential" in result.premise
    assert "status" in result.premise
    assert "dependencies" in result.premise


def test_parse_multi_triple_conclusion(parser: N3Parser, multi_triple_conclusion: str) -> None:
    """Test parsing multiple mutations in conclusion.

    Verifies parser extracts all assertion triples from conclusion
    when rule asserts multiple properties.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    multi_triple_conclusion : str
        Rule with multiple conclusion triples.
    """
    result = parser.parse(multi_triple_conclusion, uri="test:rule/multi-conc", signature="Transmute")

    assert result is not None
    # Verify all conclusion assertions
    assert "availabilityLevel" in result.conclusion
    assert "loadPriority" in result.conclusion
    assert "status" in result.conclusion


def test_parse_with_prefixes(parser: N3Parser, rule_with_prefixes: str) -> None:
    """Test handling of SPARQL prefixes.

    Verifies parser correctly processes N3 documents containing
    @prefix declarations before rule definitions.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    rule_with_prefixes : str
        N3 document with prefixes.
    """
    result = parser.parse(rule_with_prefixes, uri="test:rule/prefix", signature="Transmute")

    assert result is not None
    # Verify prefixes are handled (either preserved or stripped)
    assert "tier:Essential" in result.premise or "Essential" in result.premise


def test_parse_whitespace_variations(parser: N3Parser, whitespace_variations: str) -> None:
    """Test parsing with tabs, newlines, and varied spacing.

    Verifies parser is resilient to whitespace variations in N3 syntax,
    normalizing input before parsing.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    whitespace_variations : str
        Rule with mixed whitespace.
    """
    result = parser.parse(whitespace_variations, uri="test:rule/ws", signature="Transmute")

    assert result is not None
    # Verify parsing succeeded despite whitespace
    assert "requiresInput" in result.premise


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_parse_invalid_rule_raises(parser: N3Parser, invalid_rule: str) -> None:
    """Test error handling for malformed N3 syntax.

    Verifies parser raises ValueError when given invalid N3 rule syntax.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    invalid_rule : str
        Malformed N3 rule.
    """
    with pytest.raises(ValueError, match="Invalid N3 rule syntax"):
        parser.parse(invalid_rule, uri="test:rule/invalid", signature="Transmute")


def test_parse_empty_string_raises(parser: N3Parser) -> None:
    """Test parsing empty string input.

    Verifies parser raises ValueError for empty input.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    with pytest.raises(ValueError, match="Invalid N3 rule syntax"):
        parser.parse("", uri="test:rule/empty", signature="Transmute")


def test_parse_none_input_raises(parser: N3Parser) -> None:
    """Test parsing None input.

    Verifies parser raises TypeError for None input.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    with pytest.raises((TypeError, AttributeError)):
        parser.parse(None, uri="test:rule/none", signature="Transmute")  # type: ignore[arg-type]


# ============================================================================
# Triple Extraction Tests
# ============================================================================


def test_extract_triples_simple(parser: N3Parser) -> None:
    """Test extraction of triples from simple text.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    text = "?task unrdf:status pending"
    triples = parser.extract_triples(text)

    assert len(triples) == 1
    assert "?task" in triples[0]


def test_extract_triples_with_semicolons(parser: N3Parser) -> None:
    """Test extraction of semicolon-separated triples.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    text = '?x a kgcl:Task ; kgcl:status "pending"'
    triples = parser.extract_triples(text)

    assert len(triples) == 2
    assert any("kgcl:Task" in t for t in triples)
    assert any("status" in t for t in triples)


def test_extract_triples_multiple_statements(parser: N3Parser) -> None:
    """Test extraction from multiple period-separated statements.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    text = "?x a kgcl:Task . ?y a kgcl:Flow"
    triples = parser.extract_triples(text)

    assert len(triples) == 2


# ============================================================================
# Mutation Identification Tests
# ============================================================================


def test_identify_mutations_basic(parser: N3Parser) -> None:
    """Test basic mutation identification.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    premise = ['?x kgcl:status "pending"']
    conclusion = ['?x kgcl:status "running"']

    deletions, insertions = parser.identify_mutations(premise, conclusion)

    # Conclusion triples become insertions
    assert len(insertions) == 1
    assert "running" in insertions[0]


def test_identify_mutations_empty(parser: N3Parser) -> None:
    """Test mutation identification with empty inputs.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    deletions, insertions = parser.identify_mutations([], [])

    assert deletions == ()
    assert insertions == ()


# ============================================================================
# Integration Tests
# ============================================================================


def test_parse_real_unrdf_rule(parser: N3Parser) -> None:
    """Test parsing actual UNRDF rule from rules.n3.

    Integration test using real rule from the UNRDF codebase to
    verify parser handles production rules correctly.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    rule = """
    {
        ?capability unrdf:tier tier:Essential .
    } => {
        ?capability unrdf:availabilityLevel "core" .
        ?capability unrdf:loadPriority 1 .
    } .
    """

    result = parser.parse(rule, uri="unrdf:rule/tier-essential", signature="Transmute")

    assert result is not None
    assert result.uri == "unrdf:rule/tier-essential"
    assert result.signature == "Transmute"
    assert "tier:Essential" in result.premise
    assert "availabilityLevel" in result.conclusion
    assert "loadPriority" in result.conclusion


def test_parse_workflow_composition_rule(parser: N3Parser) -> None:
    """Test parsing workflow dependency rule.

    Tests parser on rule defining workflow step ordering,
    verifying it handles common KGC use case.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    rule = """
    {
        ?step1 unrdf:produces ?output .
        ?step2 unrdf:requires ?output .
    } => {
        ?step2 unrdf:dependsOn ?step1 .
        ?step1 unrdf:precedes ?step2 .
    } .
    """

    result = parser.parse(rule, uri="kgcl:rule/workflow-deps", signature="Transmute")

    assert result is not None
    assert "produces" in result.premise
    assert "requires" in result.premise
    assert "dependsOn" in result.conclusion
    assert "precedes" in result.conclusion


def test_parse_transmute_rule(parser: N3Parser) -> None:
    """Test parsing WCP-1 Sequence transmute rule.

    Parameters
    ----------
    parser : N3Parser
        Parser instance.
    """
    rule = """
    {
        ?task kgc:status "Active" .
        ?task yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?next .
    } => {
        ?task kgc:status "Completed" .
        ?next kgc:status "Active" .
    } .
    """

    result = parser.parse(rule, uri="kgc:WCP1_Sequence", signature="Transmute")

    assert result is not None
    assert result.signature == "Transmute"
    assert "Active" in result.premise
    assert "Completed" in result.conclusion
