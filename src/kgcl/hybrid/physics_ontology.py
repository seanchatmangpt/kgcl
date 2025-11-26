"""KGC Physics Ontology - N3 Rules as Dark Matter.

This module provides the physics ontology containing N3 rules that define
how tokens flow through workflow graphs. The rules are "Dark Matter" -
they exist in RDF but get compiled to SPARQL for execution.

The Compiled Physics Architecture:
- N3 defines logic declaratively
- Python compiles N3 -> SPARQL UPDATE
- Oxigraph executes SPARQL at Rust speed
- Manual Tick controls when physics apply
"""

from __future__ import annotations

# ==============================================================================
# STANDARD PREFIXES
# ==============================================================================

STANDARD_PREFIXES: str = """
PREFIX kgc: <https://kgc.org/ns/>
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# ==============================================================================
# PHYSICS ONTOLOGY (Dark Matter)
# ==============================================================================

PHYSICS_ONTOLOGY: str = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# ==============================================================================
# CLASS DEFINITIONS
# ==============================================================================

kgc:PhysicsRule a rdfs:Class ;
    rdfs:label "Physics Rule"@en ;
    rdfs:comment "A rule that defines how tokens flow through the graph."@en .

kgc:Verb a rdfs:Class ;
    rdfs:label "Verb"@en ;
    rdfs:comment "One of the 5 KGC verbs: Transmute, Copy, Filter, Await, Void."@en .

kgc:Pattern a rdfs:Class ;
    rdfs:label "Workflow Control Pattern"@en ;
    rdfs:comment "A YAWL Workflow Control Pattern (WCP)."@en .

# ==============================================================================
# PROPERTY DEFINITIONS
# ==============================================================================

kgc:signature a rdf:Property ;
    rdfs:label "signature"@en ;
    rdfs:domain kgc:PhysicsRule ;
    rdfs:range xsd:string ;
    rdfs:comment "The verb type: Transmute, Copy, Filter, Await, Void."@en .

kgc:n3Logic a rdf:Property ;
    rdfs:label "N3 Logic"@en ;
    rdfs:domain kgc:PhysicsRule ;
    rdfs:range xsd:string ;
    rdfs:comment "The N3 rule in { premise } => { conclusion } format."@en .

kgc:premise a rdf:Property ;
    rdfs:label "premise"@en ;
    rdfs:domain kgc:PhysicsRule ;
    rdfs:range xsd:string ;
    rdfs:comment "The IF part of the rule (WHERE clause)."@en .

kgc:conclusion a rdf:Property ;
    rdfs:label "conclusion"@en ;
    rdfs:domain kgc:PhysicsRule ;
    rdfs:range xsd:string ;
    rdfs:comment "The THEN part of the rule (mutations)."@en .

kgc:status a rdf:Property ;
    rdfs:label "status"@en ;
    rdfs:range xsd:string ;
    rdfs:comment "Task status: Active, Completed, Waiting, Voided."@en .

# ==============================================================================
# VERB DEFINITIONS
# ==============================================================================

kgc:Transmute a kgc:Verb ;
    rdfs:label "Transmute"@en ;
    rdfs:comment "Move token from source to target (sequence flow)."@en .

kgc:Copy a kgc:Verb ;
    rdfs:label "Copy"@en ;
    rdfs:comment "Copy token to all targets (parallel split)."@en .

kgc:Filter a kgc:Verb ;
    rdfs:label "Filter"@en ;
    rdfs:comment "Route token based on predicate (exclusive/multi choice)."@en .

kgc:Await a kgc:Verb ;
    rdfs:label "Await"@en ;
    rdfs:comment "Wait for threshold arrivals before firing (synchronization)."@en .

kgc:Void a kgc:Verb ;
    rdfs:label "Void"@en ;
    rdfs:comment "Remove tokens from scope (cancellation/termination)."@en .

# ==============================================================================
# WCP-1: SEQUENCE (Transmute)
# ==============================================================================

kgc:WCP1_SequenceRule a kgc:PhysicsRule ;
    rdfs:label "WCP-1: Sequence"@en ;
    kgc:signature "Transmute" ;
    kgc:n3Logic \"\"\"
        {
            ?task kgc:status "Active" .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?next kgc:status "Active"
        }
    \"\"\" ;
    rdfs:comment "Sequential flow: complete source, activate target."@en .

# ==============================================================================
# WCP-2: PARALLEL SPLIT (Copy)
# ==============================================================================

kgc:WCP2_ParallelSplitRule a kgc:PhysicsRule ;
    rdfs:label "WCP-2: Parallel Split"@en ;
    kgc:signature "Copy" ;
    kgc:n3Logic \"\"\"
        {
            ?task kgc:status "Active" .
            ?task yawl:hasSplit yawl:ControlTypeAnd .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?next kgc:status "Active"
        }
    \"\"\" ;
    rdfs:comment "AND-split: copy token to ALL outgoing branches."@en .

# ==============================================================================
# WCP-3: SYNCHRONIZATION (Await)
# ==============================================================================

kgc:WCP3_SynchronizationRule a kgc:PhysicsRule ;
    rdfs:label "WCP-3: Synchronization"@en ;
    kgc:signature "Await" ;
    kgc:n3Logic \"\"\"
        {
            ?task yawl:hasJoin yawl:ControlTypeAnd .
            ?incoming yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?task .
            ?incoming kgc:status "Completed"
        }
        =>
        {
            ?task kgc:status "Active"
        }
    \"\"\" ;
    rdfs:comment "AND-join: wait for ALL incoming branches to complete."@en .

# ==============================================================================
# WCP-4: EXCLUSIVE CHOICE (Filter)
# ==============================================================================

kgc:WCP4_ExclusiveChoiceRule a kgc:PhysicsRule ;
    rdfs:label "WCP-4: Exclusive Choice"@en ;
    kgc:signature "Filter" ;
    kgc:n3Logic \"\"\"
        {
            ?task kgc:status "Active" .
            ?task yawl:hasSplit yawl:ControlTypeXor .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            ?flow yawl:hasPredicate ?pred .
            ?pred kgc:evaluatesTo true
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?next kgc:status "Active"
        }
    \"\"\" ;
    rdfs:comment "XOR-split: route token to ONE branch based on predicate."@en .

# ==============================================================================
# WCP-5: SIMPLE MERGE (Transmute)
# ==============================================================================

kgc:WCP5_SimpleMergeRule a kgc:PhysicsRule ;
    rdfs:label "WCP-5: Simple Merge"@en ;
    kgc:signature "Transmute" ;
    kgc:n3Logic \"\"\"
        {
            ?task yawl:hasJoin yawl:ControlTypeXor .
            ?incoming yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?task .
            ?incoming kgc:status "Completed"
        }
        =>
        {
            ?task kgc:status "Active"
        }
    \"\"\" ;
    rdfs:comment "XOR-join: fire on first arrival (no sync needed)."@en .

# ==============================================================================
# WCP-6: MULTI-CHOICE (Filter)
# ==============================================================================

kgc:WCP6_MultiChoiceRule a kgc:PhysicsRule ;
    rdfs:label "WCP-6: Multi-Choice"@en ;
    kgc:signature "Filter" ;
    kgc:n3Logic \"\"\"
        {
            ?task kgc:status "Active" .
            ?task yawl:hasSplit yawl:ControlTypeOr .
            ?task yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            ?flow yawl:hasPredicate ?pred .
            ?pred kgc:evaluatesTo true
        }
        =>
        {
            ?next kgc:status "Active"
        }
    \"\"\" ;
    rdfs:comment "OR-split: route token to MULTIPLE branches based on predicates."@en .

# ==============================================================================
# WCP-43: EXPLICIT TERMINATION (Void)
# ==============================================================================

kgc:WCP43_ExplicitTerminationRule a kgc:PhysicsRule ;
    rdfs:label "WCP-43: Explicit Termination"@en ;
    kgc:signature "Void" ;
    kgc:n3Logic \"\"\"
        {
            ?task a yawl:OutputCondition .
            ?task kgc:status "Active"
        }
        =>
        {
            ?task kgc:status "Completed" .
            ?task kgc:terminatedAt ?now
        }
    \"\"\" ;
    rdfs:comment "Terminal node: void all remaining tokens, end workflow."@en .

# ==============================================================================
# WCP-11: IMPLICIT TERMINATION (Void)
# ==============================================================================

kgc:WCP11_ImplicitTerminationRule a kgc:PhysicsRule ;
    rdfs:label "WCP-11: Implicit Termination"@en ;
    kgc:signature "Void" ;
    kgc:n3Logic \"\"\"
        {
            ?task kgc:status "Active" .
            FILTER NOT EXISTS { ?task yawl:flowsInto ?any }
        }
        =>
        {
            ?task kgc:status "Completed"
        }
    \"\"\" ;
    rdfs:comment "Dead-end: task with no outgoing flows completes naturally."@en .
"""


def load_physics_ontology() -> str:
    """Load the complete KGC Physics Ontology.

    Returns
    -------
    str
        The ontology in Turtle format containing:
        - Class definitions (PhysicsRule, Verb, Pattern)
        - Property definitions (signature, n3Logic, etc.)
        - N3 rules for all 5 KGC verbs
        - WCP pattern implementations (1-6, 11, 43)

    Examples
    --------
    >>> ontology = load_physics_ontology()
    >>> "kgc:WCP1_SequenceRule" in ontology
    True
    """
    return PHYSICS_ONTOLOGY


def get_verb_rule(verb_name: str) -> str | None:
    """Extract the N3 rule for a specific verb.

    Parameters
    ----------
    verb_name : str
        One of: Transmute, Copy, Filter, Await, Void

    Returns
    -------
    str | None
        The N3 logic string, or None if verb not found.
    """
    verb_map = {
        "Transmute": "WCP1_SequenceRule",
        "Copy": "WCP2_ParallelSplitRule",
        "Filter": "WCP4_ExclusiveChoiceRule",
        "Await": "WCP3_SynchronizationRule",
        "Void": "WCP43_ExplicitTerminationRule",
    }
    rule_name = verb_map.get(verb_name)
    if not rule_name:
        return None

    # Extract from ontology (simple parse)
    import re

    pattern = rf'kgc:{rule_name}.*?kgc:n3Logic\s+"""(.*?)"""'
    match = re.search(pattern, PHYSICS_ONTOLOGY, re.DOTALL)
    return match.group(1).strip() if match else None


def get_wcp_rule(wcp_number: int) -> str | None:
    """Extract the N3 rule for a specific WCP pattern.

    Parameters
    ----------
    wcp_number : int
        The WCP pattern number (1-6, 11, 43 supported)

    Returns
    -------
    str | None
        The N3 logic string, or None if WCP not found.
    """
    wcp_map = {
        1: "WCP1_SequenceRule",
        2: "WCP2_ParallelSplitRule",
        3: "WCP3_SynchronizationRule",
        4: "WCP4_ExclusiveChoiceRule",
        5: "WCP5_SimpleMergeRule",
        6: "WCP6_MultiChoiceRule",
        11: "WCP11_ImplicitTerminationRule",
        43: "WCP43_ExplicitTerminationRule",
    }
    rule_name = wcp_map.get(wcp_number)
    if not rule_name:
        return None

    import re

    pattern = rf'kgc:{rule_name}.*?kgc:n3Logic\s+"""(.*?)"""'
    match = re.search(pattern, PHYSICS_ONTOLOGY, re.DOTALL)
    return match.group(1).strip() if match else None


def list_all_verbs() -> list[str]:
    """List all 5 KGC verbs.

    Returns
    -------
    list[str]
        The verb names: Transmute, Copy, Filter, Await, Void
    """
    return ["Transmute", "Copy", "Filter", "Await", "Void"]


def list_all_patterns() -> list[int]:
    """List all implemented WCP patterns.

    Returns
    -------
    list[int]
        The WCP numbers with implementations.
    """
    return [1, 2, 3, 4, 5, 6, 11, 43]


# ==============================================================================
# SAMPLE TOPOLOGY TEMPLATES
# ==============================================================================

SIMPLE_SEQUENCE_TOPOLOGY: str = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Active" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:Middle> .

<urn:task:Middle> a yawl:Task ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:2> yawl:nextElementRef <urn:task:End> .

<urn:task:End> a yawl:OutputCondition .
"""

PARALLEL_SPLIT_TOPOLOGY: str = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Active" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:BranchA> .
<urn:flow:2> yawl:nextElementRef <urn:task:BranchB> .

<urn:task:BranchA> a yawl:Task ;
    yawl:flowsInto <urn:flow:3> .

<urn:task:BranchB> a yawl:Task ;
    yawl:flowsInto <urn:flow:4> .

<urn:flow:3> yawl:nextElementRef <urn:task:Join> .
<urn:flow:4> yawl:nextElementRef <urn:task:Join> .

<urn:task:Join> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:5> .

<urn:flow:5> yawl:nextElementRef <urn:task:End> .

<urn:task:End> a yawl:OutputCondition .
"""

XOR_SPLIT_TOPOLOGY: str = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Active" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto <urn:flow:high>, <urn:flow:low> .

<urn:flow:high>
    yawl:nextElementRef <urn:task:HighValue> ;
    yawl:hasPredicate <urn:pred:high> .

<urn:pred:high> kgc:expression "amount > 1000" .

<urn:flow:low>
    yawl:nextElementRef <urn:task:LowValue> ;
    yawl:hasPredicate <urn:pred:low> .

<urn:pred:low> kgc:expression "amount <= 1000" .

<urn:task:HighValue> a yawl:Task ;
    yawl:flowsInto <urn:flow:merge1> .

<urn:task:LowValue> a yawl:Task ;
    yawl:flowsInto <urn:flow:merge2> .

<urn:flow:merge1> yawl:nextElementRef <urn:task:End> .
<urn:flow:merge2> yawl:nextElementRef <urn:task:End> .

<urn:task:End> a yawl:OutputCondition ;
    yawl:hasJoin yawl:ControlTypeXor .
"""
