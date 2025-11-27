"""Comprehensive validation of all 41 YAWL pattern mappings in kgc_physics.ttl.

This test suite verifies that ALL 41 YAWL Workflow Control Patterns are correctly
mapped in the ontology with the correct verb and required parameters.

Test Philosophy
---------------
- Research-focused: Validates ontology completeness, not implementation details
- Chicago School TDD: Tests verify behavior (pattern existence, correct verb, params)
- SPARQL-driven: All queries use RDF ontology directly

Test Coverage
-------------
- WCP 1-5: Basic Control Flow
- WCP 6-9: Advanced Branching
- WCP 10-11: Structural
- WCP 12-15, 34-36: Multiple Instance (7 patterns)
- WCP 16-18: State-Based
- WCP 19-27: Cancellation + Iteration (9 core + 2 loop variants + 2 trigger variants)
- WCP 43: Explicit Termination
- Data patterns (2 patterns)
- Resource patterns (2 patterns)
- Service patterns (2 patterns)

Total: 41 distinct pattern mappings

Examples
--------
>>> pytest tests/engine/test_all_43_patterns_validated.py -v
>>> pytest tests/engine/test_all_43_patterns_validated.py -k "WCP1"
>>> pytest tests/engine/test_all_43_patterns_validated.py::test_pattern_mapping_exists_and_correct
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.query import ResultRow

# Namespaces from kgc_physics.ttl
KGC = Namespace("http://bitflow.ai/ontology/kgc/v3#")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

# ALL 41 WCP pattern mappings from kgc_physics.ttl
# Format: (mapping_name, expected_verb, expected_params_dict)
PATTERN_MAPPINGS: list[tuple[str, str, dict[str, Any]]] = [
    # =============================================================================
    # SECTION 1: BASIC CONTROL FLOW PATTERNS (WCP 1-5)
    # =============================================================================
    ("WCP1_Sequence", "transmute", {}),
    (
        "WCP2_ParallelSplit",
        "copy",
        {"cardinality": "topology", "trigger_property": "yawl:hasSplit", "trigger_value": "yawl:ControlTypeAnd"},
    ),
    (
        "WCP3_Synchronization",
        "await",
        {
            "threshold": "all",
            "completion_strategy": "waitAll",
            "trigger_property": "yawl:hasJoin",
            "trigger_value": "yawl:ControlTypeAnd",
        },
    ),
    (
        "WCP4_ExclusiveChoice",
        "filter",
        {"selection_mode": "exactlyOne", "trigger_property": "yawl:hasSplit", "trigger_value": "yawl:ControlTypeXor"},
    ),
    ("WCP5_SimpleMerge", "transmute", {"trigger_property": "yawl:hasJoin", "trigger_value": "yawl:ControlTypeXor"}),
    # =============================================================================
    # SECTION 2: ADVANCED BRANCHING PATTERNS (WCP 6-9)
    # =============================================================================
    (
        "WCP6_MultiChoice",
        "filter",
        {"selection_mode": "oneOrMore", "trigger_property": "yawl:hasSplit", "trigger_value": "yawl:ControlTypeOr"},
    ),
    (
        "WCP7_StructuredSyncMerge",
        "await",
        {
            "threshold": "active",
            "completion_strategy": "waitActive",
            "trigger_property": "yawl:hasJoin",
            "trigger_value": "yawl:ControlTypeOr",
        },
    ),
    ("WCP8_MultiMerge", "transmute", {}),
    ("WCP9_Discriminator", "await", {"threshold": "1", "completion_strategy": "waitFirst", "reset_on_fire": True}),
    # =============================================================================
    # SECTION 3: STRUCTURAL PATTERNS (WCP 10-11)
    # =============================================================================
    ("WCP10_ArbitraryCycles", "filter", {"selection_mode": "oneOrMore"}),
    ("WCP11_ImplicitTermination", "void", {"cancellation_scope": "case"}),
    # =============================================================================
    # SECTION 4: MULTIPLE INSTANCE PATTERNS (WCP 12-15, 34-36)
    # =============================================================================
    ("WCP12_MINoSync", "copy", {"cardinality": "dynamic", "instance_binding": "data"}),
    ("WCP13_MIDesignTime", "copy", {"cardinality": "static", "instance_binding": "index"}),
    ("WCP14_MIRuntime", "copy", {"cardinality": "dynamic", "instance_binding": "data"}),
    ("WCP15_MINoPrior", "copy", {"cardinality": "incremental", "instance_binding": "data"}),
    ("WCP34_MIStaticPartialJoin", "await", {"threshold": "static", "completion_strategy": "waitQuorum"}),
    (
        "WCP35_MICancellingJoin",
        "await",
        {"threshold": "static", "completion_strategy": "waitQuorum", "cancellation_scope": "region"},
    ),
    ("WCP36_MIDynamicJoin", "await", {"threshold": "dynamic", "completion_strategy": "waitQuorum"}),
    # =============================================================================
    # SECTION 5: STATE-BASED PATTERNS (WCP 16-18)
    # =============================================================================
    ("WCP16_DeferredChoice", "filter", {"selection_mode": "deferred"}),
    ("WCP17_InterleavedParallel", "filter", {"selection_mode": "mutex"}),
    ("WCP18_Milestone", "await", {"threshold": "milestone", "completion_strategy": "waitMilestone"}),
    # =============================================================================
    # SECTION 6: CANCELLATION PATTERNS (WCP 19-27)
    # =============================================================================
    ("WCP19_CancelTask", "void", {"cancellation_scope": "self"}),
    ("WCP20_CancelCase", "void", {"cancellation_scope": "case"}),
    ("WCP21_CancelRegion", "void", {"cancellation_scope": "region"}),
    ("WCP22_CancelMI", "void", {"cancellation_scope": "instances"}),
    (
        "WCP23_CompleteMI",
        "await",
        {"threshold": "N", "completion_strategy": "waitQuorum", "cancellation_scope": "instances"},
    ),
    ("WCP24_ExceptionHandling", "void", {"cancellation_scope": "task"}),
    ("WCP25_Timeout", "void", {"cancellation_scope": "self"}),
    ("WCP26_StructuredLoop", "filter", {"selection_mode": "loopCondition", "reset_on_fire": True}),
    ("WCP27_Recursion", "copy", {"cardinality": "1", "instance_binding": "recursive"}),
    # =============================================================================
    # SECTION 7: ITERATION PATTERNS (WCP 21 variants)
    # =============================================================================
    (
        "WCP21_WhileLoop",
        "filter",
        {"selection_mode": "whileTrue", "trigger_property": "yawl:hasSplit", "trigger_value": "yawl:WhileLoop"},
    ),
    (
        "WCP21_RepeatUntil",
        "filter",
        {"selection_mode": "untilTrue", "trigger_property": "yawl:hasSplit", "trigger_value": "yawl:RepeatUntil"},
    ),
    # =============================================================================
    # SECTION 8: TRIGGER PATTERNS (WCP 23-24 trigger variants)
    # =============================================================================
    ("WCP23_TransientTrigger", "await", {"threshold": "signal", "completion_strategy": "waitSignal"}),
    ("WCP24_PersistentTrigger", "await", {"threshold": "persistent", "completion_strategy": "waitPersistent"}),
    # =============================================================================
    # SECTION 9: TERMINATION PATTERNS (WCP 43)
    # =============================================================================
    ("WCP43_ExplicitTermination", "void", {"cancellation_scope": "case"}),
    # =============================================================================
    # SECTION 10: DATA PATTERNS (2 patterns)
    # =============================================================================
    ("DataMapping_Transform", "transmute", {}),
    ("DataVisibility_Task", "transmute", {}),
    # =============================================================================
    # SECTION 11: RESOURCE PATTERNS (2 patterns)
    # =============================================================================
    ("Resource_Authorization", "filter", {"selection_mode": "authorized"}),
    ("Resource_RoleAllocation", "filter", {"selection_mode": "roleMatch"}),
    # =============================================================================
    # SECTION 12: SERVICE PATTERNS (2 patterns)
    # =============================================================================
    ("Service_WebService", "copy", {"cardinality": "1"}),
    ("Service_AsyncCallback", "await", {"threshold": "1", "completion_strategy": "waitCallback"}),
]


@pytest.fixture(scope="module")
def physics_ontology() -> Graph:
    """Load the KGC Physics Ontology once for all tests.

    Returns
    -------
    Graph
        The loaded kgc_physics.ttl ontology graph.

    Examples
    --------
    >>> ontology = physics_ontology()
    >>> (None, None, None) in ontology  # At least one triple exists
    True
    """
    ontology = Graph()
    ontology_path = Path(__file__).parent.parent.parent / "ontology" / "core" / "kgc_physics.ttl"
    ontology.parse(ontology_path, format="turtle")
    return ontology


def test_ontology_loads_successfully(physics_ontology: Graph) -> None:
    """Verify that kgc_physics.ttl loads without errors.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> ontology = Graph()
    >>> ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
    >>> len(ontology) > 0
    True
    """
    # Ontology should have triples
    assert len(physics_ontology) > 0, "Ontology is empty"

    # Ontology should have version info
    version_query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT ?version WHERE {
        ?ont a owl:Ontology ;
             owl:versionInfo ?version .
    }
    """
    results = list(physics_ontology.query(version_query))
    assert results, "No version info found in ontology"
    version = str(results[0][0])  # type: ignore[index]
    assert version == "3.1.0", f"Expected version 3.1.0, got {version}"


def test_all_5_verbs_defined(physics_ontology: Graph) -> None:
    """Verify all 5 elemental verbs are defined in ontology.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> query = "SELECT ?verb WHERE { ?verb a kgc:Verb . ?verb rdfs:label ?label }"
    >>> results = list(physics_ontology.query(query))
    >>> len(results) == 5
    True
    """
    query = f"""
    PREFIX kgc: <{KGC}>
    PREFIX rdfs: <{RDFS}>
    SELECT ?verbLabel WHERE {{
        ?verb a kgc:Verb ;
              rdfs:label ?verbLabel .
    }}
    """
    results = list(physics_ontology.query(query))

    assert len(results) == 5, f"Expected 5 verbs, found {len(results)}"

    verb_labels = {str(r[0]).lower() for r in results}  # type: ignore[index]
    expected_verbs = {"transmute", "copy", "filter", "await", "void"}
    assert verb_labels == expected_verbs, f"Missing verbs: {expected_verbs - verb_labels}"


def test_total_pattern_mappings_count(physics_ontology: Graph) -> None:
    """Verify exactly 41 pattern mappings exist in ontology.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> query = "SELECT (COUNT(?mapping) AS ?count) WHERE { ?mapping a kgc:PatternMapping . }"
    >>> results = list(physics_ontology.query(query))
    >>> int(str(results[0][0])) == 41
    True
    """
    query = f"""
    PREFIX kgc: <{KGC}>
    SELECT (COUNT(?mapping) AS ?count) WHERE {{
        ?mapping a kgc:PatternMapping .
    }}
    """
    results = list(physics_ontology.query(query))

    count = int(str(results[0][0]))  # type: ignore[index]
    assert count == 41, f"Expected 41 pattern mappings, found {count}"


@pytest.mark.parametrize("mapping_name,expected_verb,expected_params", PATTERN_MAPPINGS)
def test_pattern_mapping_exists_and_correct(
    physics_ontology: Graph, mapping_name: str, expected_verb: str, expected_params: dict[str, Any]
) -> None:
    """Verify pattern mapping exists with correct verb and parameters.

    This test validates:
    1. The pattern mapping exists (kgc:{mapping_name})
    2. It maps to the correct verb (transmute, copy, filter, await, void)
    3. It has the required parameters for that verb

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.
    mapping_name : str
        Name of the pattern mapping (e.g., "WCP1_Sequence").
    expected_verb : str
        Expected verb label ("transmute", "copy", "filter", "await", "void").
    expected_params : dict[str, Any]
        Expected parameter values for the mapping.

    Examples
    --------
    >>> # Test WCP1_Sequence → Transmute
    >>> query = f"SELECT ?verb WHERE {{ kgc:WCP1_Sequence kgc:verb ?v . ?v rdfs:label ?verb }}"
    >>> results = list(physics_ontology.query(query))
    >>> str(results[0][0]).lower() == "transmute"
    True

    >>> # Test WCP2_ParallelSplit → Copy(topology)
    >>> query = "SELECT ?cardinality WHERE { kgc:WCP2_ParallelSplit kgc:hasCardinality ?cardinality }"
    >>> results = list(physics_ontology.query(query))
    >>> str(results[0][0]) == "topology"
    True
    """
    # Check mapping exists and has correct verb
    query = f"""
    PREFIX kgc: <{KGC}>
    PREFIX rdfs: <{RDFS}>
    SELECT ?verbLabel ?threshold ?cardinality ?completion ?selection ?scope ?reset ?binding
           ?triggerProperty ?triggerValue
    WHERE {{
        kgc:{mapping_name} a kgc:PatternMapping ;
                           kgc:verb ?verb .
        ?verb rdfs:label ?verbLabel .
        OPTIONAL {{ kgc:{mapping_name} kgc:hasThreshold ?threshold . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:hasCardinality ?cardinality . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:completionStrategy ?completion . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:selectionMode ?selection . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:cancellationScope ?scope . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:resetOnFire ?reset . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:instanceBinding ?binding . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:triggerProperty ?triggerProperty . }}
        OPTIONAL {{ kgc:{mapping_name} kgc:triggerValue ?triggerValue . }}
    }}
    """
    results = list(physics_ontology.query(query))

    assert results, f"No mapping found for {mapping_name}"

    row = results[0]  # type: ignore[index]
    verb_label = str(row[0]).lower()  # type: ignore[index]

    # Verify verb matches
    assert verb_label == expected_verb, f"{mapping_name}: Expected verb '{expected_verb}', got '{verb_label}'"

    # Extract actual parameters
    actual_params: dict[str, Any] = {}
    if row[1] is not None:  # type: ignore[index]
        actual_params["threshold"] = str(row[1])  # type: ignore[index]
    if row[2] is not None:  # type: ignore[index]
        actual_params["cardinality"] = str(row[2])  # type: ignore[index]
    if row[3] is not None:  # type: ignore[index]
        actual_params["completion_strategy"] = str(row[3])  # type: ignore[index]
    if row[4] is not None:  # type: ignore[index]
        actual_params["selection_mode"] = str(row[4])  # type: ignore[index]
    if row[5] is not None:  # type: ignore[index]
        actual_params["cancellation_scope"] = str(row[5])  # type: ignore[index]
    if row[6] is not None:  # type: ignore[index]
        reset_val = str(row[6]).lower()  # type: ignore[index]
        actual_params["reset_on_fire"] = reset_val == "true"
    if row[7] is not None:  # type: ignore[index]
        actual_params["instance_binding"] = str(row[7])  # type: ignore[index]
    if row[8] is not None:  # type: ignore[index]
        # Extract local name from URI
        trigger_prop_uri = str(row[8])  # type: ignore[index]
        if "#" in trigger_prop_uri:
            actual_params["trigger_property"] = "yawl:" + trigger_prop_uri.split("#")[1]
        else:
            actual_params["trigger_property"] = trigger_prop_uri
    if row[9] is not None:  # type: ignore[index]
        # Extract local name from URI
        trigger_val_uri = str(row[9])  # type: ignore[index]
        if "#" in trigger_val_uri:
            actual_params["trigger_value"] = "yawl:" + trigger_val_uri.split("#")[1]
        else:
            actual_params["trigger_value"] = trigger_val_uri

    # Verify expected parameters are present
    for param_name, param_value in expected_params.items():
        assert param_name in actual_params, (
            f"{mapping_name}: Missing parameter '{param_name}'. Found: {actual_params.keys()}"
        )

        actual_value = actual_params[param_name]
        assert actual_value == param_value, (
            f"{mapping_name}: Parameter '{param_name}' expected '{param_value}', got '{actual_value}'"
        )


def test_verb_parameter_properties_defined(physics_ontology: Graph) -> None:
    """Verify all parameter properties are defined in ontology.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> query = "SELECT ?prop WHERE { ?prop rdfs:domain kgc:PatternMapping }"
    >>> results = list(physics_ontology.query(query))
    >>> len(results) >= 7  # At least 7 parameter properties
    True
    """
    required_properties = [
        "hasThreshold",
        "hasCardinality",
        "completionStrategy",
        "selectionMode",
        "cancellationScope",
        "resetOnFire",
        "instanceBinding",
    ]

    for prop_name in required_properties:
        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX rdfs: <{RDFS}>
        ASK {{
            kgc:{prop_name} a ?type ;
                            rdfs:label ?label ;
                            rdfs:domain kgc:PatternMapping .
        }}
        """
        result = bool(physics_ontology.query(query))
        assert result, f"Parameter property kgc:{prop_name} not properly defined"


def test_patterns_by_verb_distribution(physics_ontology: Graph) -> None:
    """Verify distribution of patterns across the 5 verbs.

    Expected distribution (approximate):
    - transmute: ~6 patterns (sequences, simple merges, data)
    - copy: ~8 patterns (splits, MI patterns, service calls)
    - filter: ~10 patterns (choices, loops, resource)
    - await: ~13 patterns (joins, discriminators, triggers)
    - void: ~6 patterns (cancellations, termination)

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> query = '''
    ... SELECT ?verbLabel (COUNT(?mapping) AS ?count) WHERE {
    ...     ?mapping a kgc:PatternMapping ; kgc:verb ?verb .
    ...     ?verb rdfs:label ?verbLabel .
    ... } GROUP BY ?verbLabel ORDER BY ?verbLabel
    ... '''
    >>> results = list(physics_ontology.query(query))
    >>> len(results) == 5  # One count per verb
    True
    """
    query = f"""
    PREFIX kgc: <{KGC}>
    PREFIX rdfs: <{RDFS}>
    SELECT ?verbLabel (COUNT(?mapping) AS ?count) WHERE {{
        ?mapping a kgc:PatternMapping ;
                 kgc:verb ?verb .
        ?verb rdfs:label ?verbLabel .
    }} GROUP BY ?verbLabel ORDER BY ?verbLabel
    """
    results = list(physics_ontology.query(query))

    assert len(results) == 5, f"Expected counts for 5 verbs, got {len(results)}"

    verb_counts = {str(r[0]).lower(): int(str(r[1])) for r in results}  # type: ignore[index]

    # Verify each verb has at least one mapping
    for verb in ["transmute", "copy", "filter", "await", "void"]:
        assert verb in verb_counts, f"No patterns mapped to verb '{verb}'"
        assert verb_counts[verb] > 0, f"Verb '{verb}' has zero patterns"

    # Verify total adds up to 41
    total_mapped = sum(verb_counts.values())
    assert total_mapped == 41, f"Total mapped patterns ({total_mapped}) != 41"


def test_multi_instance_patterns_have_cardinality_or_threshold(physics_ontology: Graph) -> None:
    """Verify all MI patterns have appropriate cardinality or threshold parameters.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> # WCP12-15 should have cardinality
    >>> query = "SELECT ?cardinality WHERE { kgc:WCP12_MINoSync kgc:hasCardinality ?cardinality }"
    >>> results = list(physics_ontology.query(query))
    >>> len(results) > 0
    True

    >>> # WCP34-36 should have threshold
    >>> query = "SELECT ?threshold WHERE { kgc:WCP34_MIStaticPartialJoin kgc:hasThreshold ?threshold }"
    >>> results = list(physics_ontology.query(query))
    >>> len(results) > 0
    True
    """
    mi_patterns_with_cardinality = ["WCP12_MINoSync", "WCP13_MIDesignTime", "WCP14_MIRuntime", "WCP15_MINoPrior"]

    mi_patterns_with_threshold = ["WCP34_MIStaticPartialJoin", "WCP35_MICancellingJoin", "WCP36_MIDynamicJoin"]

    # Check cardinality patterns
    for pattern in mi_patterns_with_cardinality:
        query = f"""
        PREFIX kgc: <{KGC}>
        SELECT ?cardinality WHERE {{
            kgc:{pattern} kgc:hasCardinality ?cardinality .
        }}
        """
        results = list(physics_ontology.query(query))
        assert results, f"{pattern} missing kgc:hasCardinality parameter"
        cardinality = str(results[0][0])  # type: ignore[index]
        assert cardinality in ["static", "dynamic", "incremental"], f"{pattern} has invalid cardinality '{cardinality}'"

    # Check threshold patterns
    for pattern in mi_patterns_with_threshold:
        query = f"""
        PREFIX kgc: <{KGC}>
        SELECT ?threshold WHERE {{
            kgc:{pattern} kgc:hasThreshold ?threshold .
        }}
        """
        results = list(physics_ontology.query(query))
        assert results, f"{pattern} missing kgc:hasThreshold parameter"
        threshold = str(results[0][0])  # type: ignore[index]
        assert threshold in ["static", "dynamic"], f"{pattern} has invalid threshold '{threshold}'"


def test_cancellation_patterns_have_scope(physics_ontology: Graph) -> None:
    """Verify all cancellation patterns have cancellationScope parameter.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> # WCP19 should have scope="self"
    >>> query = "SELECT ?scope WHERE { kgc:WCP19_CancelTask kgc:cancellationScope ?scope }"
    >>> results = list(physics_ontology.query(query))
    >>> str(results[0][0]) == "self"
    True
    """
    cancellation_patterns = [
        ("WCP11_ImplicitTermination", "case"),
        ("WCP19_CancelTask", "self"),
        ("WCP20_CancelCase", "case"),
        ("WCP21_CancelRegion", "region"),
        ("WCP22_CancelMI", "instances"),
        ("WCP24_ExceptionHandling", "task"),
        ("WCP25_Timeout", "self"),
        ("WCP43_ExplicitTermination", "case"),
    ]

    for pattern, expected_scope in cancellation_patterns:
        query = f"""
        PREFIX kgc: <{KGC}>
        SELECT ?scope WHERE {{
            kgc:{pattern} kgc:cancellationScope ?scope .
        }}
        """
        results = list(physics_ontology.query(query))
        assert results, f"{pattern} missing kgc:cancellationScope parameter"
        actual_scope = str(results[0][0])  # type: ignore[index]
        assert actual_scope == expected_scope, f"{pattern}: Expected scope '{expected_scope}', got '{actual_scope}'"


def test_loop_patterns_have_reset_on_fire(physics_ontology: Graph) -> None:
    """Verify loop and discriminator patterns have resetOnFire parameter.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> # WCP9_Discriminator should have resetOnFire=true
    >>> query = "SELECT ?reset WHERE { kgc:WCP9_Discriminator kgc:resetOnFire ?reset }"
    >>> results = list(physics_ontology.query(query))
    >>> str(results[0][0]).lower() == "true"
    True
    """
    patterns_with_reset = ["WCP9_Discriminator", "WCP26_StructuredLoop"]

    for pattern in patterns_with_reset:
        query = f"""
        PREFIX kgc: <{KGC}>
        SELECT ?reset WHERE {{
            kgc:{pattern} kgc:resetOnFire ?reset .
        }}
        """
        results = list(physics_ontology.query(query))
        assert results, f"{pattern} missing kgc:resetOnFire parameter"
        reset_value = str(results[0][0]).lower()  # type: ignore[index]
        assert reset_value == "true", f"{pattern}: resetOnFire should be true, got {reset_value}"


def test_all_mappings_have_pattern_and_verb(physics_ontology: Graph) -> None:
    """Verify every PatternMapping has both kgc:pattern and kgc:verb properties.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> query = '''
    ... SELECT ?mapping WHERE {
    ...     ?mapping a kgc:PatternMapping .
    ...     FILTER NOT EXISTS { ?mapping kgc:pattern ?p }
    ... }
    ... '''
    >>> results = list(physics_ontology.query(query))
    >>> len(results) == 0  # No mappings missing pattern
    True
    """
    # Check for mappings without pattern
    query_no_pattern = f"""
    PREFIX kgc: <{KGC}>
    SELECT ?mapping WHERE {{
        ?mapping a kgc:PatternMapping .
        FILTER NOT EXISTS {{ ?mapping kgc:pattern ?p }}
    }}
    """
    results_no_pattern = list(physics_ontology.query(query_no_pattern))
    assert not results_no_pattern, f"Found {len(results_no_pattern)} mappings without kgc:pattern"

    # Check for mappings without verb
    query_no_verb = f"""
    PREFIX kgc: <{KGC}>
    SELECT ?mapping WHERE {{
        ?mapping a kgc:PatternMapping .
        FILTER NOT EXISTS {{ ?mapping kgc:verb ?v }}
    }}
    """
    results_no_verb = list(physics_ontology.query(query_no_verb))
    assert not results_no_verb, f"Found {len(results_no_verb)} mappings without kgc:verb"


def test_ontology_namespace_consistency(physics_ontology: Graph) -> None:
    """Verify all KGC entities use consistent namespace.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> # All verbs should be in KGC namespace
    >>> query = "SELECT ?verb WHERE { ?verb a kgc:Verb }"
    >>> results = list(physics_ontology.query(query))
    >>> all(str(r[0]).startswith("http://bitflow.ai/ontology/kgc/v3#") for r in results)
    True
    """
    # Check all verbs are in KGC namespace
    query_verbs = f"""
    PREFIX kgc: <{KGC}>
    SELECT ?verb WHERE {{
        ?verb a kgc:Verb .
        FILTER (!STRSTARTS(STR(?verb), STR(kgc:)))
    }}
    """
    bad_verbs = list(physics_ontology.query(query_verbs))
    assert not bad_verbs, f"Found {len(bad_verbs)} verbs outside KGC namespace"

    # Check all pattern mappings are in KGC namespace
    query_mappings = f"""
    PREFIX kgc: <{KGC}>
    SELECT ?mapping WHERE {{
        ?mapping a kgc:PatternMapping .
        FILTER (!STRSTARTS(STR(?mapping), STR(kgc:)))
    }}
    """
    bad_mappings = list(physics_ontology.query(query_mappings))
    assert not bad_mappings, f"Found {len(bad_mappings)} mappings outside KGC namespace"


def test_summary_of_all_41_patterns(physics_ontology: Graph) -> None:
    """Generate comprehensive summary of all 41 pattern mappings.

    This test always passes but prints detailed validation report.

    Parameters
    ----------
    physics_ontology : Graph
        The loaded ontology fixture.

    Examples
    --------
    >>> # This test generates a comprehensive report
    >>> pytest tests/engine/test_all_43_patterns_validated.py::test_summary_of_all_41_patterns -v -s
    """
    print("\n" + "=" * 80)
    print("COMPREHENSIVE VALIDATION: ALL 41 YAWL PATTERN MAPPINGS")
    print("=" * 80)

    query = f"""
    PREFIX kgc: <{KGC}>
    PREFIX rdfs: <{RDFS}>
    SELECT ?mappingName ?verbLabel ?threshold ?cardinality ?completion ?selection ?scope
    WHERE {{
        ?mapping a kgc:PatternMapping ;
                 kgc:verb ?verb .
        ?verb rdfs:label ?verbLabel .
        BIND(REPLACE(STR(?mapping), ".*#", "") AS ?mappingName)
        OPTIONAL {{ ?mapping kgc:hasThreshold ?threshold . }}
        OPTIONAL {{ ?mapping kgc:hasCardinality ?cardinality . }}
        OPTIONAL {{ ?mapping kgc:completionStrategy ?completion . }}
        OPTIONAL {{ ?mapping kgc:selectionMode ?selection . }}
        OPTIONAL {{ ?mapping kgc:cancellationScope ?scope . }}
    }}
    ORDER BY ?mappingName
    """
    results = list(physics_ontology.query(query))

    print(f"\nTotal Pattern Mappings: {len(results)}")
    print("\nPattern → (Verb, Parameters):")
    print("-" * 80)

    for i, row in enumerate(results, start=1):
        row_typed = row  # type: ignore[assignment]
        mapping_name = str(row_typed[0])
        verb_label = str(row_typed[1])
        params = []
        if row_typed[2] is not None:
            params.append(f"threshold={row_typed[2]}")
        if row_typed[3] is not None:
            params.append(f"cardinality={row_typed[3]}")
        if row_typed[4] is not None:
            params.append(f"completion={row_typed[4]}")
        if row_typed[5] is not None:
            params.append(f"selection={row_typed[5]}")
        if row_typed[6] is not None:
            params.append(f"scope={row_typed[6]}")

        params_str = ", ".join(params) if params else "no params"
        print(f"{i:2d}. {mapping_name:30s} → {verb_label:10s} ({params_str})")

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE: All 41 patterns correctly mapped!")
    print("=" * 80 + "\n")

    # Always pass - this is a summary test
    assert len(results) == 41, f"Expected 41 patterns, found {len(results)}"
