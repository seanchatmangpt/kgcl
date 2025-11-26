# SPARQL Template Architecture for RDF-Native Verb Execution

**STATUS**: Architecture Design
**VERSION**: 1.0.0
**DATE**: 2025-11-25

## Executive Summary

This document specifies a pure RDF architecture that eliminates Python if/else logic from verb execution by storing SPARQL query templates in the ontology alongside parameter values.

**Current Problem**: `knowledge_engine.py` extracts parameter VALUES from the ontology but interprets them with Python conditionals (lines 397-577).

**Solution**: Store SPARQL EXECUTION TEMPLATES in the ontology. Each parameter value maps to a pre-compiled SPARQL subquery. Verbs execute templates directly.

---

## Architecture Overview

### The Data Flow (Current vs. Proposed)

**CURRENT (Hybrid - BAD)**:
```
RDF Ontology → SPARQL Query → Python if/else → SPARQL Execution
   (params)      (extract)        (interpret)      (execute)
```

**PROPOSED (Pure RDF - GOOD)**:
```
RDF Ontology → SPARQL Query → SPARQL Template Execution
   (params +      (extract +         (execute)
   templates)     templates)
```

---

## 1. Unified Parameter Extraction Query

### 1.1 Query Structure

This single SPARQL query extracts ALL 7 parameters AND their execution templates:

```sparql
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

SELECT
    ?verbLabel
    ?threshold ?thresholdTemplate
    ?cardinality ?cardinalityTemplate
    ?completion ?completionTemplate
    ?selection ?selectionTemplate
    ?scope ?scopeTemplate
    ?reset
    ?binding ?bindingTemplate
WHERE {
    # Core mapping (unchanged)
    ?mapping kgc:pattern <PATTERN_URI> ;
             kgc:verb ?verb .
    ?verb rdfs:label ?verbLabel .

    # Parameter 1: Threshold (AWAIT)
    OPTIONAL {
        ?mapping kgc:hasThreshold ?threshold .
        ?threshold kgc:executionTemplate ?thresholdTemplate .
    }

    # Parameter 2: Cardinality (COPY)
    OPTIONAL {
        ?mapping kgc:hasCardinality ?cardinality .
        ?cardinality kgc:executionTemplate ?cardinalityTemplate .
    }

    # Parameter 3: Completion Strategy (AWAIT)
    OPTIONAL {
        ?mapping kgc:completionStrategy ?completion .
        ?completion kgc:executionTemplate ?completionTemplate .
    }

    # Parameter 4: Selection Mode (FILTER)
    OPTIONAL {
        ?mapping kgc:selectionMode ?selection .
        ?selection kgc:executionTemplate ?selectionTemplate .
    }

    # Parameter 5: Cancellation Scope (VOID)
    OPTIONAL {
        ?mapping kgc:cancellationScope ?scope .
        ?scope kgc:executionTemplate ?scopeTemplate .
    }

    # Parameter 6: Reset on Fire (boolean - no template)
    OPTIONAL {
        ?mapping kgc:resetOnFire ?reset .
    }

    # Parameter 7: Instance Binding (MI patterns)
    OPTIONAL {
        ?mapping kgc:instanceBinding ?binding .
        ?binding kgc:executionTemplate ?bindingTemplate .
    }
}
```

### 1.2 Key Differences from Current Query

| Aspect | Current (knowledge_engine.py:1003-1033) | Proposed |
|--------|----------------------------------------|----------|
| **Returns** | Parameter values only | Values + SPARQL templates |
| **Interpretation** | Python if/else (lines 397-577) | SPARQL template execution |
| **Extensibility** | Requires code changes | Add new templates to ontology |
| **Compliance** | Violates "RDF-only" architecture | Pure RDF execution |

---

## 2. Execution Template Schema

### 2.1 Ontology Extensions (Add to kgc_physics.ttl)

```turtle
# =============================================================================
# SECTION 18: EXECUTION TEMPLATES (NEW)
# =============================================================================

kgc:ExecutionTemplate a rdfs:Class ;
    rdfs:label "Execution Template"@en ;
    rdfs:comment "SPARQL query template for parameter-specific verb execution."@en .

kgc:executionTemplate a rdf:Property ;
    rdfs:label "execution template"@en ;
    rdfs:domain rdfs:Literal ;  # Domain is parameter value (e.g., "topology", "all")
    rdfs:range kgc:ExecutionTemplate ;
    rdfs:comment "Links parameter value to SPARQL execution template."@en .

kgc:targetQuery a rdf:Property ;
    rdfs:label "target query"@en ;
    rdfs:domain kgc:ExecutionTemplate ;
    rdfs:range xsd:string ;
    rdfs:comment "SPARQL SELECT query to find target nodes."@en .

kgc:tokenMutations a rdf:Property ;
    rdfs:label "token mutations"@en ;
    rdfs:domain kgc:ExecutionTemplate ;
    rdfs:range xsd:string ;
    rdfs:comment "SPARQL CONSTRUCT query to mutate token state."@en .

kgc:instanceGeneration a rdf:Property ;
    rdfs:label "instance generation"@en ;
    rdfs:domain kgc:ExecutionTemplate ;
    rdfs:range xsd:string ;
    rdfs:comment "SPARQL CONSTRUCT for MI instance creation."@en .

# Parameter Value Individuals (make them resources, not literals)
kgc:TopologyCardinality a rdfs:Resource ;
    rdfs:label "topology"@en ;
    kgc:description "Use graph topology to determine cardinality."@en .

kgc:DynamicCardinality a rdfs:Resource ;
    rdfs:label "dynamic"@en ;
    kgc:description "Determine cardinality from runtime data."@en .

kgc:AllThreshold a rdfs:Resource ;
    rdfs:label "all"@en ;
    kgc:description "Wait for ALL incoming branches."@en .

kgc:ExactlyOneSelection a rdfs:Resource ;
    rdfs:label "exactlyOne"@en ;
    kgc:description "Select exactly one path (XOR-split)."@en .

# ... (define all 7 parameter value resources)
```

### 2.2 Template Storage Pattern

Each parameter value becomes a RESOURCE with attached SPARQL templates:

```turtle
# =============================================================================
# COPY VERB - CARDINALITY TEMPLATES
# =============================================================================

# Template 1: Topology-based cardinality (WCP-2: Parallel Split)
kgc:TopologyCardinality
    kgc:executionTemplate kgc:TopologyTemplate .

kgc:TopologyTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Topology Cardinality Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        SELECT ?next WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            ?subject kgc:hasToken true .
            VALUES ?next { %TARGETS% }  # Injected from targetQuery results
            VALUES ?txId { %TX_ID% }    # Injected from context
        }
    """ .

# Template 2: Dynamic cardinality (WCP-14: MI with Runtime Knowledge)
kgc:DynamicCardinality
    kgc:executionTemplate kgc:DynamicTemplate .

kgc:DynamicTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Dynamic Cardinality Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        SELECT ?next WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
        LIMIT 1  # Get base target for instance generation
    """ ;
    kgc:instanceGeneration """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?instance a kgc:MIInstance ;
                      kgc:instanceId ?index ;
                      kgc:boundData ?item ;
                      kgc:baseTask ?baseTarget .
        } WHERE {
            VALUES ?baseTarget { %BASE_TARGET% }  # From targetQuery
            VALUES ?items { %MI_ITEMS% }          # From ctx.data
            BIND(URI(CONCAT(STR(?baseTarget), "_instance_", STR(?index))) AS ?instance)
            BIND(%INDEX_ITERATOR% AS ?index)     # Loop variable
            BIND(%ITEM_ITERATOR% AS ?item)       # Loop variable
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?instance kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            ?subject kgc:hasToken true .
            ?instance a kgc:MIInstance .
            VALUES ?txId { %TX_ID% }
        }
    """ .

# Template 3: Static cardinality (WCP-13: MI with Design-Time Knowledge)
kgc:StaticCardinality
    kgc:executionTemplate kgc:StaticTemplate .

kgc:StaticTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Static Cardinality Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        SELECT ?next ?min ?max WHERE {
            ?subject yawl:minimum ?min ;
                     yawl:maximum ?max ;
                     yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            FILTER(?min = ?max)  # Static = fixed count
        }
        LIMIT 1
    """ ;
    kgc:instanceGeneration """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?instance a kgc:MIInstance ;
                      kgc:instanceId ?index ;
                      kgc:baseTask ?baseTarget .
        } WHERE {
            VALUES ?baseTarget { %BASE_TARGET% }
            VALUES ?count { %STATIC_COUNT% }     # From targetQuery (?min or ?max)
            BIND(URI(CONCAT(STR(?baseTarget), "_instance_", STR(?index))) AS ?instance)
            BIND(%RANGE_ITERATOR% AS ?index)    # 0..count-1
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?instance kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            ?subject kgc:hasToken true .
            ?instance a kgc:MIInstance .
            VALUES ?txId { %TX_ID% }
        }
    """ .

# =============================================================================
# AWAIT VERB - THRESHOLD TEMPLATES
# =============================================================================

# Template 4: All threshold (WCP-3: Synchronization)
kgc:AllThreshold
    kgc:executionTemplate kgc:AllThresholdTemplate .

kgc:AllThresholdTemplate a kgc:ExecutionTemplate ;
    rdfs:label "All Threshold Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        SELECT ?next (COUNT(?incoming) AS ?total) (SUM(?hasToken) AS ?completed) WHERE {
            ?subject yawl:flowsInto ?outFlow .
            ?outFlow yawl:nextElementRef ?next .

            # Count incoming branches
            ?incoming yawl:flowsInto ?inFlow .
            ?inFlow yawl:nextElementRef ?subject .

            # Check which have tokens
            OPTIONAL {
                ?incoming kgc:hasToken ?hasToken .
            }
        }
        GROUP BY ?next
        HAVING (?total = ?completed)  # All branches must complete
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?incoming kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            VALUES ?next { %TARGETS% }        # From targetQuery
            VALUES ?txId { %TX_ID% }
            ?incoming yawl:flowsInto/yawl:nextElementRef ?subject .
            ?incoming kgc:hasToken true .
        }
    """ .

# Template 5: First threshold (WCP-9: Discriminator)
kgc:OneThreshold
    kgc:executionTemplate kgc:FirstThresholdTemplate .

kgc:FirstThresholdTemplate a kgc:ExecutionTemplate ;
    rdfs:label "First Threshold Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        SELECT ?next WHERE {
            ?subject yawl:flowsInto ?outFlow .
            ?outFlow yawl:nextElementRef ?next .

            # Check if subject already fired
            FILTER NOT EXISTS {
                ?subject kgc:discriminatorFired true .
            }
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?firstIncoming kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:discriminatorFired true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            VALUES ?next { %TARGETS% }
            VALUES ?txId { %TX_ID% }
            # Get first incoming with token
            {
                SELECT ?firstIncoming WHERE {
                    ?firstIncoming yawl:flowsInto/yawl:nextElementRef ?subject ;
                                   kgc:hasToken true .
                } LIMIT 1
            }
        }
    """ .

# =============================================================================
# FILTER VERB - SELECTION MODE TEMPLATES
# =============================================================================

# Template 6: Exactly One (WCP-4: Exclusive Choice)
kgc:ExactlyOneSelection
    kgc:executionTemplate kgc:ExactlyOneTemplate .

kgc:ExactlyOneTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Exactly One Selection Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        SELECT ?next ?predicate ?ordering WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            OPTIONAL {
                ?flow yawl:hasPredicate/yawl:query ?predicate ;
                      yawl:hasPredicate/yawl:ordering ?ordering .
            }
            # Inject predicate evaluation result from Python
            FILTER(%PREDICATE_EVAL%)  # Replaced by _evaluate_predicate() result
        }
        ORDER BY ?ordering
        LIMIT 1  # First match only (XOR)
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            VALUES ?next { %TARGETS% }
            VALUES ?txId { %TX_ID% }
            ?subject kgc:hasToken true .
        }
    """ .

# Template 7: One or More (WCP-6: Multi-Choice)
kgc:OneOrMoreSelection
    kgc:executionTemplate kgc:OneOrMoreTemplate .

kgc:OneOrMoreTemplate a kgc:ExecutionTemplate ;
    rdfs:label "One or More Selection Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        SELECT ?next WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
            OPTIONAL {
                ?flow yawl:hasPredicate/yawl:query ?predicate .
            }
            # Inject predicate evaluation result
            FILTER(%PREDICATE_EVAL%)
        }
        # No LIMIT - all matching paths selected (OR-split)
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            VALUES ?next { %TARGETS% }
            VALUES ?txId { %TX_ID% }
            ?subject kgc:hasToken true .
        }
    """ .

# =============================================================================
# VOID VERB - CANCELLATION SCOPE TEMPLATES
# =============================================================================

# Template 8: Self scope (WCP-19: Cancel Task)
kgc:SelfScope
    kgc:executionTemplate kgc:SelfScopeTemplate .

kgc:SelfScopeTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Self Scope Template"@en ;
    kgc:targetQuery """
        SELECT ?subject WHERE {
            VALUES ?subject { %SUBJECT% }  # Only cancel current node
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?subject kgc:voidedAt ?txId .
            ?subject kgc:status "Voided" .
        } WHERE {
            VALUES ?subject { %SUBJECT% }
            VALUES ?txId { %TX_ID% }
        }
    """ .

# Template 9: Region scope (WCP-21: Cancel Region)
kgc:RegionScope
    kgc:executionTemplate kgc:RegionScopeTemplate .

kgc:RegionScopeTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Region Scope Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        SELECT ?task WHERE {
            ?subject yawl:hasCancellationRegion ?region .
            ?region yawl:containsTask ?task .
            ?task kgc:hasToken true .  # Only cancel active tasks
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?task kgc:hasToken false .
            ?task kgc:voidedAt ?txId .
            ?task kgc:status "Voided" .
        } WHERE {
            VALUES ?task { %TARGETS% }  # From targetQuery
            VALUES ?txId { %TX_ID% }
        }
    """ .

# Template 10: Case scope (WCP-20: Cancel Case)
kgc:CaseScope
    kgc:executionTemplate kgc:CaseScopeTemplate .

kgc:CaseScopeTemplate a kgc:ExecutionTemplate ;
    rdfs:label "Case Scope Template"@en ;
    kgc:targetQuery """
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        SELECT ?task WHERE {
            ?subject yawl:belongsToCase ?case .
            ?task yawl:belongsToCase ?case ;
                  kgc:hasToken true .
        }
    """ ;
    kgc:tokenMutations """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        CONSTRUCT {
            ?task kgc:hasToken false .
            ?task kgc:voidedAt ?txId .
            ?task kgc:status "Voided" .
            ?case kgc:status "Terminated" .
        } WHERE {
            VALUES ?task { %TARGETS% }
            VALUES ?case { %CASE_URI% }
            VALUES ?txId { %TX_ID% }
        }
    """ .
```

---

## 3. Template Execution Engine

### 3.1 Modified VerbConfig Dataclass

```python
from dataclasses import dataclass
from rdflib import URIRef

@dataclass(frozen=True)
class ExecutionTemplate:
    """
    SPARQL execution template for parameter-specific verb execution.

    Parameters
    ----------
    target_query : str
        SPARQL SELECT to find target nodes.
    token_mutations : str
        SPARQL CONSTRUCT to mutate token state.
    instance_generation : str | None
        SPARQL CONSTRUCT for MI instance creation (optional).
    """

    target_query: str
    token_mutations: str
    instance_generation: str | None = None


@dataclass(frozen=True)
class VerbConfig:
    """
    Configuration for verb execution - The (verb, params, templates) tuple.

    Contains the verb name, parameters, AND execution templates.
    Templates are pre-compiled SPARQL queries from the ontology.

    Parameters
    ----------
    verb : str
        The verb name.
    threshold : str | None
        For AWAIT: threshold value.
    threshold_template : ExecutionTemplate | None
        For AWAIT: SPARQL template for threshold logic.
    cardinality : str | None
        For COPY: cardinality value.
    cardinality_template : ExecutionTemplate | None
        For COPY: SPARQL template for cardinality logic.
    completion_strategy : str | None
        For AWAIT: completion strategy value.
    completion_template : ExecutionTemplate | None
        For AWAIT: SPARQL template for completion logic.
    selection_mode : str | None
        For FILTER: selection mode value.
    selection_template : ExecutionTemplate | None
        For FILTER: SPARQL template for selection logic.
    cancellation_scope : str | None
        For VOID: cancellation scope value.
    scope_template : ExecutionTemplate | None
        For VOID: SPARQL template for scope logic.
    reset_on_fire : bool
        For AWAIT: whether to reset join state.
    instance_binding : str | None
        For MI: instance binding mode value.
    binding_template : ExecutionTemplate | None
        For MI: SPARQL template for instance generation.
    """

    verb: str
    threshold: str | None = None
    threshold_template: ExecutionTemplate | None = None
    cardinality: str | None = None
    cardinality_template: ExecutionTemplate | None = None
    completion_strategy: str | None = None
    completion_template: ExecutionTemplate | None = None
    selection_mode: str | None = None
    selection_template: ExecutionTemplate | None = None
    cancellation_scope: str | None = None
    scope_template: ExecutionTemplate | None = None
    reset_on_fire: bool = False
    instance_binding: str | None = None
    binding_template: ExecutionTemplate | None = None
```

### 3.2 Template Resolver (Modified resolve_verb)

```python
def resolve_verb(
    self,
    pattern: URIRef,
    node: URIRef,
    trigger_property: str | None = None,
    trigger_value: URIRef | None = None,
) -> VerbConfig:
    """
    Resolve verb AND execution templates from ontology.

    This is the ONLY place where SPARQL queries the ontology.
    Returns templates that verbs execute directly.

    Parameters
    ----------
    pattern : URIRef
        YAWL pattern to resolve.
    node : URIRef
        Node being processed.
    trigger_property : str | None
        Property that triggers mapping (e.g., "hasSplit").
    trigger_value : URIRef | None
        Value that triggers mapping (e.g., yawl:ControlTypeAnd).

    Returns
    -------
    VerbConfig
        Verb name, parameters, AND execution templates.
    """
    # Build unified query (see Section 1.1)
    query = self._build_template_query(pattern, trigger_property, trigger_value)
    results = list(self.physics_ontology.query(query))

    if not results:
        msg = f"No verb mapping found for pattern {pattern} on node {node}"
        raise ValueError(msg)

    row = cast(ResultRow, results[0])

    # Extract verb name
    verb_label = str(row[0]).lower()

    # Extract parameter values (existing logic)
    threshold = str(row[1]) if row[1] else None
    cardinality = str(row[3]) if row[3] else None
    completion = str(row[5]) if row[5] else None
    selection = str(row[7]) if row[7] else None
    scope = str(row[9]) if row[9] else None
    reset_raw = row[10] if row[10] else None
    reset = str(reset_raw).lower() == "true" if reset_raw is not None else False
    binding = str(row[11]) if row[11] else None

    # Extract execution templates (NEW)
    threshold_template = self._parse_template(row[2]) if row[2] else None
    cardinality_template = self._parse_template(row[4]) if row[4] else None
    completion_template = self._parse_template(row[6]) if row[6] else None
    selection_template = self._parse_template(row[8]) if row[8] else None
    scope_template = self._parse_template(row[10]) if row[10] else None
    binding_template = self._parse_template(row[12]) if row[12] else None

    return VerbConfig(
        verb=verb_label,
        threshold=threshold,
        threshold_template=threshold_template,
        cardinality=cardinality,
        cardinality_template=cardinality_template,
        completion_strategy=completion,
        completion_template=completion_template,
        selection_mode=selection,
        selection_template=selection_template,
        cancellation_scope=scope,
        scope_template=scope_template,
        reset_on_fire=reset,
        instance_binding=binding,
        binding_template=binding_template,
    )

def _parse_template(self, template_uri: URIRef) -> ExecutionTemplate:
    """
    Parse execution template from ontology.

    Queries the template URI to extract SPARQL queries.

    Parameters
    ----------
    template_uri : URIRef
        URI of the execution template.

    Returns
    -------
    ExecutionTemplate
        Parsed template with SPARQL queries.
    """
    query = f"""
    PREFIX kgc: <{KGC}>
    SELECT ?targetQuery ?tokenMutations ?instanceGen WHERE {{
        <{template_uri}> kgc:targetQuery ?targetQuery ;
                         kgc:tokenMutations ?tokenMutations .
        OPTIONAL {{
            <{template_uri}> kgc:instanceGeneration ?instanceGen .
        }}
    }}
    """
    results = list(self.physics_ontology.query(query))
    if not results:
        msg = f"No template found for {template_uri}"
        raise ValueError(msg)

    row = cast(ResultRow, results[0])
    return ExecutionTemplate(
        target_query=str(row[0]),
        token_mutations=str(row[1]),
        instance_generation=str(row[2]) if row[2] else None,
    )
```

### 3.3 Template Executor (Modified copy verb)

**BEFORE (lines 340-457 in knowledge_engine.py)**: Python if/else interprets cardinality.

**AFTER**: Execute SPARQL templates directly:

```python
@staticmethod
def copy(
    graph: Graph,
    subject: URIRef,
    ctx: TransactionContext,
    config: VerbConfig | None = None,
) -> QuadDelta:
    """
    VERB 2: COPY - Divergence (A → {B₁, B₂, ..., Bₙ}).

    Executes cardinality template from ontology.

    Parameters
    ----------
    graph : Graph
        The workflow graph.
    subject : URIRef
        The current node URI.
    ctx : TransactionContext
        Transaction context with data payload.
    config : VerbConfig | None
        Configuration with cardinality template.

    Returns
    -------
    QuadDelta
        Mutations to execute the parallel split.
    """
    if not config or not config.cardinality_template:
        msg = "COPY verb requires cardinality template"
        raise ValueError(msg)

    template = config.cardinality_template

    # Step 1: Execute target query to find targets
    target_query = template.target_query.replace("%SUBJECT%", str(subject))
    target_results = list(graph.query(target_query))

    if not target_results:
        return QuadDelta(additions=(), removals=())

    # Step 2: Generate MI instances if needed
    instances = []
    if template.instance_generation:
        instances = KnowledgeKernel._generate_instances(
            graph, template.instance_generation, target_results, ctx
        )

    # Step 3: Execute token mutation query
    targets = [str(cast(ResultRow, r)[0]) for r in target_results] if not instances else instances
    mutation_query = template.token_mutations.replace("%TARGETS%", ", ".join(f"<{t}>" for t in targets))
    mutation_query = mutation_query.replace("%TX_ID%", f'"{ctx.tx_id}"')

    # Execute CONSTRUCT to get triples
    mutation_graph = graph.query(mutation_query)
    additions = list(mutation_graph)
    removals = []  # Removals are implicit in CONSTRUCT

    return QuadDelta(additions=tuple(additions), removals=tuple(removals))

@staticmethod
def _generate_instances(
    graph: Graph,
    instance_template: str,
    target_results: list,
    ctx: TransactionContext,
) -> list[str]:
    """
    Generate MI instances using instance generation template.

    Parameters
    ----------
    graph : Graph
        Workflow graph.
    instance_template : str
        SPARQL CONSTRUCT for instance generation.
    target_results : list
        Results from target query.
    ctx : TransactionContext
        Context with runtime data.

    Returns
    -------
    list[str]
        List of generated instance URIs.
    """
    base_target = str(cast(ResultRow, target_results[0])[0])

    # Inject base target
    query = instance_template.replace("%BASE_TARGET%", f"<{base_target}>")

    # Handle MI data injection
    if "%MI_ITEMS%" in query:
        mi_items = ctx.data.get("mi_items", [])
        # Convert Python list to SPARQL VALUES syntax
        values_clause = " ".join(f'"{item}"' for item in mi_items)
        query = query.replace("%MI_ITEMS%", values_clause)

    # Execute instance generation
    instance_graph = graph.query(query)
    instances = [str(s) for s, p, o in instance_graph if p == KGC.instanceId]

    return instances
```

### 3.4 Complete Template Execution Pattern

```python
@staticmethod
def _execute_template(
    graph: Graph,
    subject: URIRef,
    ctx: TransactionContext,
    template: ExecutionTemplate,
) -> QuadDelta:
    """
    Generic template executor for ALL verbs.

    This replaces ALL Python if/else logic in verb methods.

    Parameters
    ----------
    graph : Graph
        Workflow graph.
    subject : URIRef
        Current node.
    ctx : TransactionContext
        Execution context.
    template : ExecutionTemplate
        SPARQL execution template from ontology.

    Returns
    -------
    QuadDelta
        Mutations to apply.
    """
    # 1. Find targets
    target_query = template.target_query.replace("%SUBJECT%", str(subject))
    target_results = list(graph.query(target_query))

    if not target_results:
        return QuadDelta(additions=(), removals=())

    # 2. Generate instances (for MI patterns)
    instances = []
    if template.instance_generation:
        instances = KnowledgeKernel._generate_instances(
            graph, template.instance_generation, target_results, ctx
        )

    # 3. Build target list
    targets = instances if instances else [str(cast(ResultRow, r)[0]) for r in target_results]

    # 4. Execute token mutations
    mutation_query = template.token_mutations
    mutation_query = mutation_query.replace("%TARGETS%", ", ".join(f"<{t}>" for t in targets))
    mutation_query = mutation_query.replace("%TX_ID%", f'"{ctx.tx_id}"')
    mutation_query = mutation_query.replace("%SUBJECT%", f"<{subject}>")

    # Inject context data
    for key, value in ctx.data.items():
        mutation_query = mutation_query.replace(f"%{key.upper()}%", f'"{value}"')

    # Execute CONSTRUCT
    mutation_graph = graph.query(mutation_query)
    additions = list(mutation_graph)

    return QuadDelta(additions=tuple(additions), removals=())
```

---

## 4. Migration Plan

### 4.1 Refactoring Phases

| Phase | Scope | Work | Validation |
|-------|-------|------|------------|
| **1. Ontology Extension** | Add template schema to kgc_physics.ttl | Define 18 execution template resources | SHACL validation |
| **2. Template Population** | Add SPARQL templates for all parameters | Write 10+ templates (see Section 2.2) | Test queries in rdflib |
| **3. VerbConfig Update** | Extend dataclass with template fields | Add ExecutionTemplate type | Type checking passes |
| **4. Resolver Update** | Modify resolve_verb() | Extract templates from ontology | Unit tests pass |
| **5. Executor Refactor** | Replace if/else with _execute_template() | Remove lines 397-577 in knowledge_engine.py | All tests pass |
| **6. Cleanup** | Delete dead code | Remove Python conditionals | Coverage maintained |

### 4.2 Validation Criteria

**Pure RDF Compliance**:
- [ ] No Python if/else for parameter interpretation
- [ ] All execution logic in SPARQL templates
- [ ] Templates stored in ontology, not code
- [ ] Verbs execute templates directly

**Correctness**:
- [ ] All 43 YAWL patterns still work
- [ ] Test suite passes (0 regressions)
- [ ] Token state mutations identical to current
- [ ] MI patterns generate correct instances

**Performance**:
- [ ] Template execution ≤ current if/else speed
- [ ] No additional SPARQL roundtrips
- [ ] Template caching implemented

---

## 5. Benefits

### 5.1 Architectural Purity

| Aspect | Before | After |
|--------|--------|-------|
| **Execution** | Python if/else | SPARQL templates |
| **Extensibility** | Edit Python code | Add ontology triples |
| **Compliance** | Violates "RDF-only" claim | Pure RDF execution |
| **Provenance** | Python stack traces | SPARQL query logs |

### 5.2 Operational Advantages

1. **Configuration as Code**: Templates in version-controlled TTL files
2. **Hot Reload**: Update templates without code changes
3. **Auditability**: SPARQL logs show exact execution path
4. **Testability**: Query templates independently in SPARQL playgrounds
5. **Composability**: Templates can reference other templates

---

## 6. Open Questions

### 6.1 Iterator Semantics

**Problem**: SPARQL doesn't have native iteration over runtime lists.

**Current Approach**: `%ITERATOR%` placeholders require Python for-loop wrapper.

**Options**:
1. **Keep minimal Python**: Iterator wrapper for MI patterns (acceptable tradeoff)
2. **SPARQL 1.1 property paths**: Limited iteration via regex
3. **RDF Lists**: Convert Python lists to rdf:List before querying

**Recommendation**: Option 1 - iterator wrapper is acceptable if it's the ONLY Python logic.

### 6.2 Predicate Evaluation

**Problem**: `_evaluate_predicate()` interprets XPath/SPARQL ASK conditions in Python.

**Current Approach**: `%PREDICATE_EVAL%` placeholder injects boolean result.

**Pure RDF Alternative**: Store predicates as SPARQL ASK in ontology, evaluate server-side.

**Recommendation**: Migrate `_evaluate_predicate()` to SPARQL ASK templates (separate task).

---

## 7. Success Metrics

### 7.1 Code Deletion

| Metric | Target |
|--------|--------|
| Lines deleted from knowledge_engine.py | 180+ lines (lines 397-577) |
| Python if/else statements removed | 15+ conditionals |
| SPARQL templates added to ontology | 10+ templates |

### 7.2 Compliance

- [ ] 100% of parameter interpretation in SPARQL
- [ ] 0% Python if/else for verb execution
- [ ] All tests pass (0 regressions)

---

## 8. Conclusion

This architecture eliminates the contradiction between KGCL's "RDF-only" claim and its Python if/else implementation. By storing SPARQL execution templates alongside parameter values in the ontology, verbs execute pure RDF logic.

**Key Insight**: Parameters shouldn't be VALUES alone - they should be (value, template) PAIRS. The ontology becomes a QUERY LIBRARY, not just a data store.

**Next Steps**:
1. Review this architecture
2. Approve ontology schema extensions
3. Implement Phase 1 (ontology extension)
4. Validate with unit tests

---

**Author**: SPARQL-Template-Architect-2
**Review Status**: Pending
**Implementation Status**: Design Complete
