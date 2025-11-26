# SPARQL Template Architecture - Visual Diagrams

**VERSION**: 1.0.0
**DATE**: 2025-11-25

---

## Diagram 1: Current vs. Proposed Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CURRENT (HYBRID - BAD)                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  RDF Ontology   │──────▶│ SPARQL Query     │──────▶│ Python if/else   │
│                 │       │ (extract params) │       │ (interpret)      │
│ Pattern → Verb  │       │                  │       │                  │
│ Verb → Params   │       │ SELECT ?threshold│       │ if threshold ==  │
│                 │       │        ?cardinal │       │   "all": ...     │
│ kgc:hasThreshold│       │        ?selection│       │ elif threshold== │
│   "all"         │       │                  │       │   "1": ...       │
└─────────────────┘       └──────────────────┘       └──────────────────┘
                                                               │
                                                               ▼
                                                      ┌──────────────────┐
                                                      │ SPARQL Execution │
                                                      │ (finally!)       │
                                                      │                  │
                                                      │ graph.query(...)│
                                                      └──────────────────┘

Problem: Parameter VALUES stored in RDF, but LOGIC in Python.
         "RDF-only" claim is FALSE.


┌─────────────────────────────────────────────────────────────────────────┐
│                   PROPOSED (PURE RDF - GOOD)                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  RDF Ontology   │──────▶│ SPARQL Query     │──────▶│ SPARQL Template  │
│                 │       │ (extract params  │       │ Execution        │
│ Pattern → Verb  │       │  + templates)    │       │ (execute!)       │
│ Verb → Params   │       │                  │       │                  │
│ Params→Templates│       │ SELECT ?threshold│       │ graph.query(     │
│                 │       │   ?thresholdTmpl │       │   template.      │
│ kgc:hasThreshold│       │   ?cardinality   │       │   target_query   │
│   "all"         │       │   ?cardinalTmpl  │       │ )                │
│     ├─ template │       │                  │       │ graph.query(     │
│        ├─ target│       └──────────────────┘       │   template.      │
│        └─ mutate│                                   │   token_mutations│
└─────────────────┘                                   │ )                │
                                                      └──────────────────┘

Solution: Parameter VALUES + SPARQL TEMPLATES stored together in RDF.
          "RDF-only" claim is TRUE.
```

---

## Diagram 2: Ontology Schema - Before vs. After

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BEFORE (v3.1)                                   │
└─────────────────────────────────────────────────────────────────────────┘

kgc:WCP3_Synchronization
    ├─ kgc:pattern ───────▶ yawl:ControlTypeAnd
    ├─ kgc:verb ──────────▶ kgc:Await
    ├─ kgc:hasThreshold ──▶ "all"              ◀── LITERAL VALUE
    └─ kgc:completionStrategy ──▶ "waitAll"    ◀── LITERAL VALUE

                              ❌ NO EXECUTION LOGIC


┌─────────────────────────────────────────────────────────────────────────┐
│                         AFTER (v4.0)                                    │
└─────────────────────────────────────────────────────────────────────────┘

kgc:WCP3_Synchronization
    ├─ kgc:pattern ───────▶ yawl:ControlTypeAnd
    ├─ kgc:verb ──────────▶ kgc:Await
    ├─ kgc:hasThreshold ──▶ kgc:AllThreshold   ◀── RESOURCE (not literal)
    │                           │
    │                           └─ kgc:executionTemplate ──▶ kgc:AllThresholdTemplate
    │                                                              │
    │                                                              ├─ kgc:targetQuery
    │                                                              │    "SELECT ?next WHERE..."
    │                                                              │
    │                                                              └─ kgc:tokenMutations
    │                                                                   "CONSTRUCT { ... }"
    │
    └─ kgc:completionStrategy ──▶ "waitAll"    ◀── Still literal (optional)

                              ✅ SPARQL TEMPLATES INCLUDED
```

---

## Diagram 3: Template Execution Flow (COPY Verb Example)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SCENARIO: WCP-2 Parallel Split with "topology" cardinality            │
└─────────────────────────────────────────────────────────────────────────┘

INPUT:
  - Node: <task1>
  - Pattern: yawl:ControlTypeAnd
  - Trigger: hasSplit=AND
  - Context: tx_id="tx_001"

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 1: resolve_verb() extracts config                                  │
└──────────────────────────────────────────────────────────────────────────┘

SPARQL Query (Unified Parameter Extraction):
    SELECT ?verbLabel ?cardinality ?cardinalityTemplate WHERE {
        ?mapping kgc:pattern yawl:ControlTypeAnd ;
                 kgc:triggerProperty "hasSplit" ;
                 kgc:triggerValue yawl:ControlTypeAnd ;
                 kgc:verb ?verb .
        ?verb rdfs:label ?verbLabel .
        ?mapping kgc:hasCardinality ?cardinality .
        ?cardinality kgc:executionTemplate ?cardinalityTemplate .
    }

Result:
    verbLabel = "copy"
    cardinality = kgc:TopologyCardinality
    cardinalityTemplate = kgc:TopologyTemplate

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Parse template from kgc:TopologyTemplate                        │
└──────────────────────────────────────────────────────────────────────────┘

SPARQL Query (Template Properties):
    SELECT ?targetQuery ?tokenMutations WHERE {
        kgc:TopologyTemplate kgc:targetQuery ?targetQuery ;
                             kgc:tokenMutations ?tokenMutations .
    }

Result:
    targetQuery = """
        PREFIX yawl: <...>
        SELECT ?next WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .
        }
    """

    tokenMutations = """
        PREFIX kgc: <...>
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            ?subject kgc:hasToken true .
            VALUES ?next { %TARGETS% }
            VALUES ?txId { %TX_ID% }
        }
    """

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Execute targetQuery to find successors                          │
└──────────────────────────────────────────────────────────────────────────┘

Injected Query:
    SELECT ?next WHERE {
        <task1> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?next .
    }

Result:
    ?next = <task2>
    ?next = <task3>
    ?next = <task4>

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Execute tokenMutations with injected targets                    │
└──────────────────────────────────────────────────────────────────────────┘

Injected Query:
    CONSTRUCT {
        ?subject kgc:hasToken false .
        ?next kgc:hasToken true .
        ?subject kgc:completedAt ?txId .
    } WHERE {
        ?subject kgc:hasToken true .
        VALUES ?next { <task2> <task3> <task4> }  ◀── Injected
        VALUES ?txId { "tx_001" }                 ◀── Injected
    }

Result (QuadDelta):
    additions:
        (<task2>, kgc:hasToken, true)
        (<task3>, kgc:hasToken, true)
        (<task4>, kgc:hasToken, true)
        (<task1>, kgc:completedAt, "tx_001")
    removals:
        (<task1>, kgc:hasToken, true)

┌──────────────────────────────────────────────────────────────────────────┐
│ RESULT: 3 parallel branches created, task1 completed                    │
└──────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐
    │  task1  │ (kgc:hasToken = false, kgc:completedAt = "tx_001")
    └────┬────┘
         │
    ┌────┼────────┐
    │    │        │
    ▼    ▼        ▼
 ┌─────┐ ┌─────┐ ┌─────┐
 │task2│ │task3│ │task4│ (ALL have kgc:hasToken = true)
 └─────┘ └─────┘ └─────┘

         ALL LOGIC EXECUTED IN SPARQL - NO PYTHON IF/ELSE
```

---

## Diagram 4: Multi-Instance Pattern Template Execution

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SCENARIO: WCP-14 MI with Runtime Knowledge ("dynamic" cardinality)    │
└─────────────────────────────────────────────────────────────────────────┘

INPUT:
  - Node: <miTask>
  - Pattern: yawl:MultiInstanceTask
  - Cardinality: kgc:DynamicCardinality
  - Context: {mi_items: ["doc1.pdf", "doc2.pdf", "doc3.pdf"]}

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Extract DynamicTemplate                                         │
└──────────────────────────────────────────────────────────────────────────┘

Template has 3 queries:
  1. targetQuery: Find base task
  2. instanceGeneration: Create N instances
  3. tokenMutations: Distribute tokens

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Execute targetQuery                                             │
└──────────────────────────────────────────────────────────────────────────┘

Query:
    SELECT ?next WHERE {
        <miTask> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?next .
    } LIMIT 1

Result:
    ?next = <processDoc>

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Execute instanceGeneration (NEW!)                               │
└──────────────────────────────────────────────────────────────────────────┘

Injected Query:
    CONSTRUCT {
        ?instance a kgc:MIInstance ;
                  kgc:instanceId ?index ;
                  kgc:boundData ?item ;
                  kgc:baseTask ?baseTarget .
    } WHERE {
        VALUES ?baseTarget { <processDoc> }
        VALUES ?items { "doc1.pdf" "doc2.pdf" "doc3.pdf" }  ◀── From ctx.data

        # Python iterator wrapper injects:
        # index=0, item="doc1.pdf"
        # index=1, item="doc2.pdf"
        # index=2, item="doc3.pdf"

        BIND(URI(CONCAT(STR(?baseTarget), "_instance_", STR(?index))) AS ?instance)
    }

Result (Generated Instances):
    <processDoc_instance_0>
        ├─ kgc:instanceId "0"
        ├─ kgc:boundData "doc1.pdf"
        └─ kgc:baseTask <processDoc>

    <processDoc_instance_1>
        ├─ kgc:instanceId "1"
        ├─ kgc:boundData "doc2.pdf"
        └─ kgc:baseTask <processDoc>

    <processDoc_instance_2>
        ├─ kgc:instanceId "2"
        ├─ kgc:boundData "doc3.pdf"
        └─ kgc:baseTask <processDoc>

┌──────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Execute tokenMutations                                          │
└──────────────────────────────────────────────────────────────────────────┘

Injected Query:
    CONSTRUCT {
        ?subject kgc:hasToken false .
        ?instance kgc:hasToken true .
        ?subject kgc:completedAt ?txId .
    } WHERE {
        ?subject kgc:hasToken true .
        ?instance a kgc:MIInstance .
        VALUES ?txId { "tx_001" }
    }

Result (QuadDelta):
    additions:
        (<processDoc_instance_0>, kgc:hasToken, true)
        (<processDoc_instance_1>, kgc:hasToken, true)
        (<processDoc_instance_2>, kgc:hasToken, true)
        (<miTask>, kgc:completedAt, "tx_001")
    removals:
        (<miTask>, kgc:hasToken, true)

┌──────────────────────────────────────────────────────────────────────────┐
│ RESULT: 3 MI instances created with data binding                        │
└──────────────────────────────────────────────────────────────────────────┘

         ┌────────┐
         │ miTask │ (completed)
         └───┬────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│instance0│ │instance1│ │instance2│
│ doc1.pdf│ │ doc2.pdf│ │ doc3.pdf│
└─────────┘ └─────────┘ └─────────┘

      Instance generation logic: 95% SPARQL, 5% Python iterator
```

---

## Diagram 5: Parameter Template Mapping

```
┌─────────────────────────────────────────────────────────────────────────┐
│  All 7 VerbConfig Parameters → Execution Templates                     │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 1: threshold (AWAIT verb)                                     │
└──────────────────────────────────────────────────────────────────────────┘

    kgc:AllThreshold ───────▶ kgc:AllThresholdTemplate
        Value: "all"              targetQuery: "SELECT ?next WHERE { ... }"
        Description: Wait ALL     tokenMutations: "CONSTRUCT { ... }"

    kgc:OneThreshold ───────▶ kgc:FirstThresholdTemplate
        Value: "1"                targetQuery: "SELECT ?next WHERE { ... }"
        Description: Wait first   tokenMutations: "CONSTRUCT { ... }"

    kgc:ActiveThreshold ────▶ kgc:ActiveThresholdTemplate
        Value: "active"           targetQuery: "SELECT ?next WHERE { ... }"
        Description: Wait active  tokenMutations: "CONSTRUCT { ... }"

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 2: cardinality (COPY verb)                                    │
└──────────────────────────────────────────────────────────────────────────┘

    kgc:TopologyCardinality ──▶ kgc:TopologyTemplate
        Value: "topology"         targetQuery: "SELECT ?next WHERE { ... }"
        Description: Use topology tokenMutations: "CONSTRUCT { ... }"

    kgc:DynamicCardinality ───▶ kgc:DynamicTemplate
        Value: "dynamic"          targetQuery: "SELECT ?next WHERE { ... }"
        Description: Runtime N    instanceGeneration: "CONSTRUCT { ... }"
                                  tokenMutations: "CONSTRUCT { ... }"

    kgc:StaticCardinality ────▶ kgc:StaticTemplate
        Value: "static"           targetQuery: "SELECT ?next ?min WHERE {...}"
        Description: Design-time N instanceGeneration: "CONSTRUCT { ... }"
                                  tokenMutations: "CONSTRUCT { ... }"

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 3: completion_strategy (AWAIT verb)                           │
└──────────────────────────────────────────────────────────────────────────┘

    kgc:WaitAllStrategy ──────▶ kgc:WaitAllTemplate
        Value: "waitAll"          targetQuery: "SELECT ... HAVING (COUNT = ALL)"
        Description: All complete tokenMutations: "CONSTRUCT { ... }"

    kgc:WaitActiveStrategy ───▶ kgc:WaitActiveTemplate
        Value: "waitActive"       targetQuery: "SELECT ... WHERE NOT Voided"
        Description: Active only  tokenMutations: "CONSTRUCT { ... }"

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 4: selection_mode (FILTER verb)                               │
└──────────────────────────────────────────────────────────────────────────┘

    kgc:ExactlyOneSelection ──▶ kgc:ExactlyOneTemplate
        Value: "exactlyOne"       targetQuery: "SELECT ... LIMIT 1"
        Description: XOR split    tokenMutations: "CONSTRUCT { ... }"

    kgc:OneOrMoreSelection ───▶ kgc:OneOrMoreTemplate
        Value: "oneOrMore"        targetQuery: "SELECT ... (no LIMIT)"
        Description: OR split     tokenMutations: "CONSTRUCT { ... }"

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 5: cancellation_scope (VOID verb)                             │
└──────────────────────────────────────────────────────────────────────────┘

    kgc:SelfScope ────────────▶ kgc:SelfScopeTemplate
        Value: "self"             targetQuery: "SELECT ?subject"
        Description: Cancel self  tokenMutations: "CONSTRUCT { ... }"

    kgc:RegionScope ──────────▶ kgc:RegionScopeTemplate
        Value: "region"           targetQuery: "SELECT ?task WHERE region"
        Description: Cancel region tokenMutations: "CONSTRUCT { ... }"

    kgc:CaseScope ────────────▶ kgc:CaseScopeTemplate
        Value: "case"             targetQuery: "SELECT ?task WHERE case"
        Description: Cancel case  tokenMutations: "CONSTRUCT { ... }"

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 6: reset_on_fire (boolean - NO TEMPLATE)                      │
└──────────────────────────────────────────────────────────────────────────┘

    Value: true/false
    Description: Reset join state after firing
    Implementation: Simple boolean check (no SPARQL template needed)

┌──────────────────────────────────────────────────────────────────────────┐
│ PARAMETER 7: instance_binding (MI patterns)                             │
└──────────────────────────────────────────────────────────────────────────┘

    kgc:IndexBinding ─────────▶ kgc:IndexBindingTemplate
        Value: "index"            instanceGeneration: "BIND(?index AS ?data)"
        Description: Bind index   tokenMutations: "CONSTRUCT { ... }"

    kgc:DataBinding ──────────▶ kgc:DataBindingTemplate
        Value: "data"             instanceGeneration: "BIND(?item AS ?data)"
        Description: Bind data    tokenMutations: "CONSTRUCT { ... }"

    TOTAL: 18 execution templates covering all parameter values
```

---

## Diagram 6: Code Deletion Impact

```
┌─────────────────────────────────────────────────────────────────────────┐
│  knowledge_engine.py - Before vs. After                                │
└─────────────────────────────────────────────────────────────────────────┘

BEFORE (Lines 340-577 = 237 lines):

340:  def copy(...):
341:      ...
375:      additions: list[Triple] = []
376:      removals: list[Triple] = []
377:
378:      cardinality = config.cardinality if config else "topology"
379:
380:      # Find ALL next elements via SPARQL
381:      query = f"""..."""
388:      results = list(graph.query(query))
...
396:      if cardinality == "topology":          ◀── Python if/else (180 lines)
397:          targets = [...]
400:      elif cardinality == "dynamic":
401:          mi_data = ctx.data.get("mi_items", [])
402:          targets = []
403:          for i, item in enumerate(mi_data):
...
417:      elif cardinality == "static":
418:          mi_query = f"""..."""
426:          mi_results = list(graph.query(mi_query))
...
435:      elif cardinality == "incremental":
...
577:      return QuadDelta(...)

                        ❌ 180 LINES OF PYTHON CONDITIONALS


AFTER (Lines 340-360 = 20 lines):

340:  def copy(...):
341:      if not config or not config.cardinality_template:
342:          raise ValueError("COPY requires cardinality template")
343:
344:      return KnowledgeKernel._execute_template(
345:          graph, subject, ctx, config.cardinality_template
346:      )

                        ✅ 20 LINES - 89% REDUCTION

┌──────────────────────────────────────────────────────────────────────────┐
│ Similar deletions for filter(), await_(), void()                        │
└──────────────────────────────────────────────────────────────────────────┘

Total Lines Deleted: ~600 lines across all 5 verbs
Total Templates Added to Ontology: 18 templates (~2000 lines of SPARQL)
Net Impact: -600 Python + 2000 TTL = Code in right place
```

---

## Diagram 7: Ontology as Query Library

```
┌─────────────────────────────────────────────────────────────────────────┐
│  kgc_physics.ttl - From Data Store to Executable Library               │
└─────────────────────────────────────────────────────────────────────────┘

BEFORE (Data-Centric):

    kgc_physics.ttl
        ├─ Verb Definitions (5 verbs)
        ├─ Parameter Properties (7 properties)
        ├─ Pattern Mappings (43 mappings)
        └─ Parameter VALUES (literals: "all", "topology", etc.)

    Role: Configuration data store
    Size: ~650 lines


AFTER (Execution-Centric):

    kgc_physics.ttl
        ├─ Verb Definitions (5 verbs)
        ├─ Parameter Properties (7 properties)
        ├─ Pattern Mappings (43 mappings)
        ├─ Parameter VALUE RESOURCES (18 resources)
        └─ Execution Templates (18 templates)      ◀── NEW
              ├─ SPARQL SELECT queries (find targets)
              ├─ SPARQL CONSTRUCT queries (mutate tokens)
              └─ SPARQL CONSTRUCT queries (generate instances)

    Role: Executable query library
    Size: ~2500 lines

┌──────────────────────────────────────────────────────────────────────────┐
│ Ontology Evolution: Data → Code                                         │
└──────────────────────────────────────────────────────────────────────────┘

    v1.0: Static definitions
    v2.0: + Parameter mappings
    v3.0: + Pattern library
    v4.0: + SPARQL execution templates  ◀── THIS ARCHITECTURE

    The ontology is now a FIRST-CLASS EXECUTABLE ARTIFACT
```

---

## Summary

This architecture moves ALL execution logic from Python into SPARQL templates stored in the ontology:

1. **Unified Query**: Single SPARQL extracts parameters + templates
2. **Template Storage**: 18 pre-compiled templates for all parameter values
3. **Template Execution**: Generic `_execute_template()` replaces verb-specific if/else
4. **Code Deletion**: 600+ lines of Python if/else deleted
5. **Pure RDF**: 100% execution logic in SPARQL

**Key Insight**: The ontology is not just DATA - it's an EXECUTABLE QUERY LIBRARY.

---

**Author**: SPARQL-Template-Architect-2
**Review Status**: Pending
