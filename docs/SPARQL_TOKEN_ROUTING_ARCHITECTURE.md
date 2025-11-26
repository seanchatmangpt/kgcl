# SPARQL-Based Token Routing Architecture

**Mission**: Eliminate Python list comprehensions and loops from KGCL Kernel verbs by expressing all token routing logic as SPARQL CONSTRUCT queries.

**Principle**: The Kernel verb becomes: "Execute SPARQL, return results as QuadDelta"

---

## Architecture Overview

### Current State (Python-Based Routing)
```python
# ❌ ANTI-PATTERN: Python loops build target lists
targets = [cast(URIRef, cast(ResultRow, r)[0]) for r in results]
for target in targets:
    additions.append((target, KGC.hasToken, Literal(True)))
```

### Target State (SPARQL-Based Routing)
```python
# ✅ PATTERN: SPARQL CONSTRUCT produces QuadDelta directly
query = _build_routing_query(verb, subject, config)
constructed_graph = Graph()
constructed_graph += graph.query(query)
return _graph_to_quaddelta(constructed_graph)
```

---

## Design Patterns

### Pattern 1: SPARQL CONSTRUCT for Token Addition
Replace Python loops with CONSTRUCT clauses that generate triples directly.

**Before (Python)**:
```python
targets = [cast(URIRef, r[0]) for r in results]
for target in targets:
    additions.append((target, KGC.hasToken, Literal(True)))
```

**After (SPARQL)**:
```sparql
CONSTRUCT {
    ?target kgc:hasToken true .
}
WHERE {
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
}
```

### Pattern 2: Conditional CONSTRUCT via BIND + FILTER
Replace Python if-statements with SPARQL FILTER expressions.

**Before (Python)**:
```python
if _evaluate_predicate(str(predicate), ctx.data):
    selected_paths.append(next_element)
```

**After (SPARQL)**:
```sparql
CONSTRUCT {
    ?target kgc:hasToken true .
}
WHERE {
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
    ?flow yawl:predicate ?pred .

    # Bind context data into SPARQL scope
    BIND({data_value} AS ?dataVal)

    # Evaluate predicate as FILTER
    FILTER(CONTAINS(STR(?pred), STR(?dataVal)))
}
```

### Pattern 3: Counting via SPARQL Aggregates
Replace Python counter loops with GROUP BY / COUNT.

**Before (Python)**:
```python
completed_sources = 0
for r in results:
    if row[1] is not None:
        completed_sources += 1
```

**After (SPARQL)**:
```sparql
SELECT (COUNT(?source) AS ?completedCount)
WHERE {
    ?flow yawl:nextElementRef <{subject}> .
    ?source kgc:completedAt ?completed .
}
```

---

## Verb 1: TRANSMUTE (Already Minimal)

**Current Implementation**: Already minimal Python wrapper around SPARQL SELECT.

**No Change Required**: Transmute is a simple point-to-point token move. The current implementation is optimal.

```python
def transmute(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?next WHERE {{
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?next .
    }}
    LIMIT 1
    """
    results = list(graph.query(query))

    if results:
        next_node = cast(URIRef, cast(ResultRow, results[0])[0])
        return QuadDelta(
            removals=((subject, KGC.hasToken, Literal(True)),),
            additions=(
                (next_node, KGC.hasToken, Literal(True)),
                (subject, KGC.completedAt, Literal(ctx.tx_id)),
            ),
        )
    return QuadDelta(additions=(), removals=())
```

---

## Verb 2: COPY (Token Cloning + Cardinality)

### Requirements
- Remove token from source
- Clone token to N targets (N determined by cardinality parameter)
- Support cardinality modes: topology, dynamic, static, incremental, integer

### SPARQL Design

#### Mode 1: Topology (WCP-2: AND-Split)
**Behavior**: Clone to ALL successors.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    # Remove token from source
    <{subject}> kgc:tokenRemoved true .

    # Add token to all targets
    ?target kgc:hasToken true .

    # Mark source as completed
    <{subject}> kgc:completedAt "{tx_id}" .
}
WHERE {
    # Find all outgoing flows
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
}
```

**Python Wrapper**:
```python
@staticmethod
def copy_topology(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:tokenRemoved true .
        ?target kgc:hasToken true .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
    }}
    WHERE {{
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?target .
    }}
    """

    constructed = Graph()
    constructed += graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

#### Mode 2: Static Cardinality (WCP-13: N Fixed Instances)
**Behavior**: Clone to N instances (N from yawl:minimum/maximum).

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:tokenRemoved true .

    # Generate N instance URIs using CONCAT
    ?instance kgc:hasToken true .
    ?instance kgc:instanceId ?idx .

    <{subject}> kgc:completedAt "{tx_id}" .
}
WHERE {
    # Get base target
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?baseTarget .

    # Get cardinality N
    <{subject}> yawl:minimum ?n .

    # Generate sequence 0..N-1
    # NOTE: RDFLib SPARQL doesn't support GENERATE_SERIES,
    # so we need a VALUES clause with pre-computed indices
    VALUES ?idx { 0 1 2 3 4 5 6 7 8 9 }
    FILTER(?idx < ?n)

    # Generate instance URI
    BIND(IRI(CONCAT(STR(?baseTarget), "_instance_", STR(?idx))) AS ?instance)
}
```

**Challenge**: SPARQL 1.1 doesn't have sequence generation. We need to:
1. Pre-compute the N value in Python
2. Inject a VALUES clause with 0..N-1
3. Let SPARQL generate instance URIs

**Python Wrapper**:
```python
@staticmethod
def copy_static(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    # First, get N from graph
    n_query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?n WHERE {{
        <{subject}> yawl:minimum ?n .
    }}
    LIMIT 1
    """
    n_results = list(graph.query(n_query))
    if not n_results:
        return QuadDelta(additions=(), removals=())

    n = int(str(cast(ResultRow, n_results[0])[0]))

    # Generate VALUES clause for sequence
    values_clause = " ".join(str(i) for i in range(n))

    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:tokenRemoved true .
        ?instance kgc:hasToken true .
        ?instance kgc:instanceId ?idx .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
    }}
    WHERE {{
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?baseTarget .

        VALUES ?idx {{ {values_clause} }}

        BIND(IRI(CONCAT(STR(?baseTarget), "_instance_", STR(?idx))) AS ?instance)
    }}
    """

    constructed = Graph()
    constructed += graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

#### Mode 3: Dynamic Cardinality (WCP-14: Runtime Data)
**Behavior**: Clone to N instances where N = len(ctx.data["mi_items"]).

**Challenge**: Context data is external to the RDF graph. We need to materialize it as temporary triples.

**Approach**: Two-phase execution:
1. **Phase 1 (Python)**: Inject context data as temporary triples
2. **Phase 2 (SPARQL)**: CONSTRUCT references injected data

```python
@staticmethod
def copy_dynamic(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    mi_items = ctx.data.get("mi_items", [])
    if not mi_items:
        # Fallback to topology
        return KGCKernel.copy_topology(graph, subject, ctx)

    # Create temporary graph with materialized context data
    temp_graph = Graph()
    temp_graph += graph  # Copy original graph

    # Materialize context data as triples
    ctx_node = URIRef(f"{subject}_ctx_{ctx.tx_id}")
    for i, item in enumerate(mi_items):
        item_node = URIRef(f"{ctx_node}/item_{i}")
        temp_graph.add((ctx_node, KGC.hasItem, item_node))
        temp_graph.add((item_node, KGC.index, Literal(i)))
        temp_graph.add((item_node, KGC.value, Literal(str(item))))

    # Now run SPARQL CONSTRUCT against temp graph
    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:tokenRemoved true .
        ?instance kgc:hasToken true .
        ?instance kgc:instanceId ?idx .
        ?instance kgc:boundData ?val .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
    }}
    WHERE {{
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?baseTarget .

        # Query materialized context data
        <{ctx_node}> kgc:hasItem ?item .
        ?item kgc:index ?idx .
        ?item kgc:value ?val .

        # Generate instance URI
        BIND(IRI(CONCAT(STR(?baseTarget), "_instance_", STR(?idx))) AS ?instance)
    }}
    """

    constructed = Graph()
    constructed += temp_graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

#### Mode 4: Incremental (WCP-15: One Instance at a Time)
**Behavior**: Create single instance, count existing instances.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:tokenRemoved true .
    ?newInstance kgc:hasToken true .
    ?newInstance kgc:instanceId ?nextIdx .
    ?newInstance kgc:parentTask <{subject}> .
    <{subject}> kgc:completedAt "{tx_id}" .
}
WHERE {
    # Get base target
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?baseTarget .

    # Count existing instances (using subquery)
    {
        SELECT (COUNT(?inst) AS ?count) WHERE {
            ?inst kgc:parentTask <{subject}> .
        }
    }

    # Next index is count
    BIND(?count AS ?nextIdx)

    # Generate new instance URI
    BIND(IRI(CONCAT(STR(?baseTarget), "_instance_", STR(?nextIdx))) AS ?newInstance)
}
```

**Python Wrapper**:
```python
@staticmethod
def copy_incremental(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:tokenRemoved true .
        ?newInstance kgc:hasToken true .
        ?newInstance kgc:instanceId ?nextIdx .
        ?newInstance kgc:parentTask <{subject}> .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
    }}
    WHERE {{
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?baseTarget .

        {{
            SELECT (COUNT(?inst) AS ?count) WHERE {{
                ?inst kgc:parentTask <{subject}> .
            }}
        }}

        BIND(?count AS ?nextIdx)
        BIND(IRI(CONCAT(STR(?baseTarget), "_instance_", STR(?nextIdx))) AS ?newInstance)
    }}
    """

    constructed = Graph()
    constructed += graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

### Unified Copy Implementation

```python
@staticmethod
def copy(graph: Graph, subject: URIRef, ctx: TransactionContext, config: VerbConfig | None = None) -> QuadDelta:
    """VERB 2: COPY - Token cloning with cardinality-based routing (pure SPARQL)."""
    cardinality = config.get("cardinality", "topology") if config else "topology"

    # Dispatch to cardinality-specific SPARQL query
    if cardinality == "topology":
        return KGCKernel.copy_topology(graph, subject, ctx)
    elif cardinality == "static":
        return KGCKernel.copy_static(graph, subject, ctx)
    elif cardinality == "dynamic":
        return KGCKernel.copy_dynamic(graph, subject, ctx)
    elif cardinality == "incremental":
        return KGCKernel.copy_incremental(graph, subject, ctx)
    elif cardinality.isdigit():
        # Explicit integer cardinality - similar to static
        n = int(cardinality)
        return KGCKernel.copy_static_n(graph, subject, ctx, n)
    else:
        return KGCKernel.copy_topology(graph, subject, ctx)
```

---

## Verb 3: FILTER (Selection + Predicate Evaluation)

### Requirements
- Evaluate predicates on outgoing flows
- Select paths based on selection_mode: exactlyOne (XOR), oneOrMore (OR), deferred, mutex
- Route token to selected paths only

### Challenge: Predicate Evaluation
**Current**: Python `eval()` against `ctx.data`
**Target**: SPARQL FILTER expressions

**Problem**: Predicates like `"data['x'] > 5"` require access to context data.

**Solution**: Materialize context data as temporary triples (same as dynamic cardinality).

### SPARQL Design

#### Mode 1: ExactlyOne (WCP-4: XOR-Split)
**Behavior**: Select FIRST flow where predicate evaluates to true.

```python
@staticmethod
def filter_exactly_one(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    # Materialize context data as temporary triples
    temp_graph = Graph()
    temp_graph += graph

    ctx_node = URIRef(f"{subject}_ctx_{ctx.tx_id}")
    for key, value in ctx.data.items():
        temp_graph.add((ctx_node, URIRef(f"{KGC}{key}"), Literal(value)))

    # SPARQL query with predicate evaluation
    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:tokenRemoved true .
        ?selected kgc:hasToken true .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
    }}
    WHERE {{
        # Get all outgoing flows ordered by priority
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?target .
        ?flow yawl:ordering ?order .

        OPTIONAL {{ ?flow yawl:predicate ?pred . }}
        OPTIONAL {{ ?flow yawl:isDefaultFlow ?isDefault . }}

        # Evaluate predicate (simplified - checks if context key matches)
        OPTIONAL {{
            <{ctx_node}> ?ctxKey ?ctxVal .
            FILTER(CONTAINS(STR(?pred), STR(?ctxKey)) && CONTAINS(STR(?pred), STR(?ctxVal)))
            BIND(?target AS ?matched)
        }}

        # Select first match OR default flow
        {{
            # First matching predicate
            {{ SELECT (MIN(?order) AS ?minOrder) WHERE {{
                <{subject}> yawl:flowsInto ?f .
                ?f yawl:ordering ?order .
                # ... (same predicate check)
            }} }}
            FILTER(?order = ?minOrder && BOUND(?matched))
            BIND(?target AS ?selected)
        }}
        UNION
        {{
            # Default flow if no matches
            FILTER(?isDefault = true)
            FILTER NOT EXISTS {{
                # No matching flows exist
                <{subject}> yawl:flowsInto ?f2 .
                # ... (predicate check)
            }}
            BIND(?target AS ?selected)
        }}
    }}
    LIMIT 1
    """

    constructed = Graph()
    constructed += temp_graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

**Limitation**: Full Python expression evaluation (e.g., `data['x'] > 5`) is not possible in SPARQL 1.1.

**Pragmatic Solution**:
1. **Phase 1 (Python)**: Pre-evaluate predicates to boolean flags
2. **Phase 2 (SPARQL)**: Query flows with true predicates

```python
@staticmethod
def filter_exactly_one_pragmatic(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    # Step 1: Pre-evaluate predicates in Python (temporarily)
    # Query flows with predicates
    eval_query = f"""
    PREFIX yawl: <{YAWL}>
    SELECT ?flow ?target ?pred ?order ?isDefault WHERE {{
        <{subject}> yawl:flowsInto ?flow .
        ?flow yawl:nextElementRef ?target .
        ?flow yawl:ordering ?order .
        OPTIONAL {{ ?flow yawl:predicate ?pred . }}
        OPTIONAL {{ ?flow yawl:isDefaultFlow ?isDefault . }}
    }}
    ORDER BY ?order
    """
    results = list(graph.query(eval_query))

    # Evaluate predicates to find matches
    matched_flow = None
    default_flow = None

    for row in results:
        flow, target, pred, order, is_default = row

        # Track default
        if is_default and str(is_default).lower() == "true":
            default_flow = target
            continue

        # Evaluate predicate
        if pred is None:
            matched_flow = target
            break
        elif _evaluate_predicate(str(pred), ctx.data):
            matched_flow = target
            break

    # Fallback to default
    if not matched_flow and default_flow:
        matched_flow = default_flow

    if not matched_flow:
        return QuadDelta(additions=(), removals=())

    # Step 2: Use SPARQL to generate QuadDelta for selected flow
    route_query = f"""
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:tokenRemoved true .
        <{matched_flow}> kgc:hasToken true .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
    }}
    WHERE {{
        # Just construct the triples directly
        BIND(1 AS ?dummy)
    }}
    """

    constructed = Graph()
    constructed += graph.query(route_query)
    return _graph_to_quaddelta(constructed, subject)
```

**Better Solution**: Define predicate evaluation IN RDF using SPARQL 1.1 Property Paths.

```turtle
# In kgc_physics.ttl, define predicate logic as RDF patterns
:flow1 yawl:predicate [
    a kgc:ComparisonPredicate ;
    kgc:leftOperand "x" ;
    kgc:operator ">" ;
    kgc:rightOperand "5"^^xsd:integer
] .
```

Then SPARQL can query structured predicates:
```sparql
?flow yawl:predicate ?pred .
?pred kgc:leftOperand ?left ;
      kgc:operator ?op ;
      kgc:rightOperand ?right .

<{ctx_node}> ?leftKey ?leftVal .
FILTER(STR(?leftKey) = ?left)
FILTER((STR(?op) = ">" && ?leftVal > ?right) ||
       (STR(?op) = "=" && ?leftVal = ?right))
```

#### Mode 2: OneOrMore (WCP-6: OR-Split)
**Behavior**: Select ALL flows where predicate evaluates to true.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:tokenRemoved true .
    ?target kgc:hasToken true .
    <{subject}> kgc:completedAt "{tx_id}" .
}
WHERE {
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .

    OPTIONAL { ?flow yawl:predicate ?pred . }

    # Evaluate predicate (using structured RDF predicates)
    OPTIONAL {
        ?pred kgc:leftOperand ?left ;
              kgc:operator ?op ;
              kgc:rightOperand ?right .
        <{ctx_node}> ?ctxProp ?ctxVal .
        FILTER(STR(?ctxProp) = CONCAT(STR(kgc:), ?left))
        FILTER((STR(?op) = ">" && ?ctxVal > ?right))
    }

    # Include flows with no predicate OR matching predicate
    FILTER(!BOUND(?pred) || BOUND(?ctxVal))
}
```

#### Mode 3: Deferred (WCP-16)
**Behavior**: Don't route, mark as awaiting selection.

```sparql
CONSTRUCT {
    <{subject}> kgc:awaitingSelection true .
}
WHERE {
    BIND(1 AS ?dummy)
}
```

#### Mode 4: Mutex (WCP-17)
**Behavior**: Check if sibling is executing, select first if available.

```sparql
CONSTRUCT {
    <{subject}> kgc:tokenRemoved true .
    ?target kgc:hasToken true .
    <{subject}> kgc:completedAt "{tx_id}" .
}
WHERE {
    # Check no sibling has token
    FILTER NOT EXISTS {
        ?sibling kgc:hasToken true .
        ?sibling kgc:mutexGroup <{subject}> .
    }

    # Select first available flow
    <{subject}> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
    ?flow yawl:ordering ?order .

    { SELECT (MIN(?order) AS ?minOrder) WHERE {
        <{subject}> yawl:flowsInto ?f .
        ?f yawl:ordering ?order .
    }}
    FILTER(?order = ?minOrder)
}
LIMIT 1
```

---

## Verb 4: AWAIT (Join Synchronization)

### Requirements
- Count completed/voided/active source tasks
- Compare against threshold (all, 1, N, active, dynamic)
- Add token to current node if threshold met

### SPARQL Design

#### Mode 1: All (WCP-3: AND-Join)
**Behavior**: Wait for ALL incoming flows to complete.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:hasToken true .
    <{subject}> kgc:completedAt "{tx_id}" .
    <{subject}> kgc:thresholdAchieved ?completedCount .
}
WHERE {
    # Count total incoming flows
    {
        SELECT (COUNT(?source) AS ?totalCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
        }
    }

    # Count completed flows
    {
        SELECT (COUNT(?source) AS ?completedCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
            ?source kgc:completedAt ?completed .
        }
    }

    # Check all completed
    FILTER(?completedCount >= ?totalCount)

    # Prevent double-fire
    FILTER NOT EXISTS { <{subject}> kgc:hasToken true . }
}
```

**Python Wrapper**:
```python
@staticmethod
def await_all(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:hasToken true .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
        <{subject}> kgc:thresholdAchieved ?completedCount .
    }}
    WHERE {{
        {{
            SELECT (COUNT(?source) AS ?totalCount) WHERE {{
                ?flow yawl:nextElementRef <{subject}> .
                ?source yawl:flowsInto ?flow .
            }}
        }}

        {{
            SELECT (COUNT(?source) AS ?completedCount) WHERE {{
                ?flow yawl:nextElementRef <{subject}> .
                ?source yawl:flowsInto ?flow .
                ?source kgc:completedAt ?completed .
            }}
        }}

        FILTER(?completedCount >= ?totalCount)
        FILTER NOT EXISTS {{ <{subject}> kgc:hasToken true . }}
    }}
    """

    constructed = Graph()
    constructed += graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

#### Mode 2: First (WCP-9: Discriminator)
**Behavior**: Fire on FIRST completed flow.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:hasToken true .
    <{subject}> kgc:completedAt "{tx_id}" .
    <{subject}> kgc:thresholdAchieved "1" .
}
WHERE {
    # Check at least one source completed
    {
        SELECT (COUNT(?source) AS ?completedCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
            ?source kgc:completedAt ?completed .
        }
    }

    FILTER(?completedCount >= 1)
    FILTER NOT EXISTS { <{subject}> kgc:hasToken true . }
}
```

#### Mode 3: Active (WCP-7: OR-Join)
**Behavior**: Wait for all NON-VOIDED flows.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:hasToken true .
    <{subject}> kgc:completedAt "{tx_id}" .
    <{subject}> kgc:thresholdAchieved ?completedCount .
}
WHERE {
    # Count total sources
    {
        SELECT (COUNT(?source) AS ?totalCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
        }
    }

    # Count voided sources
    {
        SELECT (COUNT(?source) AS ?voidedCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
            ?source kgc:voidedAt ?voided .
        }
    }

    # Count completed sources
    {
        SELECT (COUNT(?source) AS ?completedCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
            ?source kgc:completedAt ?completed .
        }
    }

    # Check completed >= (total - voided)
    BIND(?totalCount - ?voidedCount AS ?activeCount)
    FILTER(?completedCount >= ?activeCount)
    FILTER NOT EXISTS { <{subject}> kgc:hasToken true . }
}
```

#### Mode 4: N-of-M (Static Threshold)
**Behavior**: Fire when N out of M flows complete.

```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:hasToken true .
    <{subject}> kgc:completedAt "{tx_id}" .
    <{subject}> kgc:thresholdAchieved ?completedCount .
}
WHERE {
    # Get threshold from node
    <{subject}> kgc:threshold ?n .

    # Count completed sources
    {
        SELECT (COUNT(?source) AS ?completedCount) WHERE {
            ?flow yawl:nextElementRef <{subject}> .
            ?source yawl:flowsInto ?flow .
            ?source kgc:completedAt ?completed .
        }
    }

    FILTER(?completedCount >= ?n)
    FILTER NOT EXISTS { <{subject}> kgc:hasToken true . }
}
```

#### Mode 5: Dynamic Threshold
**Behavior**: Threshold from context data (materialized as triple).

```python
@staticmethod
def await_dynamic(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
    # Materialize threshold from context
    threshold_n = int(ctx.data.get("join_threshold", 1))

    temp_graph = Graph()
    temp_graph += graph
    temp_graph.add((subject, KGC.runtimeThreshold, Literal(threshold_n)))

    query = f"""
    PREFIX yawl: <{YAWL}>
    PREFIX kgc: <{KGC}>

    CONSTRUCT {{
        <{subject}> kgc:hasToken true .
        <{subject}> kgc:completedAt "{ctx.tx_id}" .
        <{subject}> kgc:thresholdAchieved ?completedCount .
    }}
    WHERE {{
        <{subject}> kgc:runtimeThreshold ?threshold .

        {{
            SELECT (COUNT(?source) AS ?completedCount) WHERE {{
                ?flow yawl:nextElementRef <{subject}> .
                ?source yawl:flowsInto ?flow .
                ?source kgc:completedAt ?completed .
            }}
        }}

        FILTER(?completedCount >= ?threshold)
        FILTER NOT EXISTS {{ <{subject}> kgc:hasToken true . }}
    }}
    """

    constructed = Graph()
    constructed += temp_graph.query(query)
    return _graph_to_quaddelta(constructed, subject)
```

---

## Verb 5: VOID (Cancellation)

**Minimal SPARQL** - Already simple, just mark as voided.

```sparql
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <{subject}> kgc:tokenRemoved true .
    <{subject}> kgc:voidedAt "{tx_id}" .
}
WHERE {
    BIND(1 AS ?dummy)
}
```

---

## Helper: Graph to QuadDelta Conversion

```python
def _graph_to_quaddelta(constructed: Graph, subject: URIRef) -> QuadDelta:
    """Convert CONSTRUCT result graph to QuadDelta."""
    additions: list[tuple[URIRef, URIRef, Literal | URIRef]] = []
    removals: list[tuple[URIRef, URIRef, Literal]] = []

    for s, p, o in constructed:
        # Skip kgc:tokenRemoved marker triple
        if p == KGC.tokenRemoved:
            removals.append((s, KGC.hasToken, Literal(True)))
            continue

        additions.append((s, p, o))

    return QuadDelta(additions=tuple(additions), removals=tuple(removals))
```

---

## Examples: WCP Patterns as Pure SPARQL

### Example 1: WCP-2 (AND-Split) via Copy + Topology

**Python**:
```python
delta = KGCKernel.copy(graph, task_A, ctx, {"cardinality": "topology"})
```

**Resulting SPARQL**:
```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <task_A> kgc:tokenRemoved true .
    <task_B1> kgc:hasToken true .
    <task_B2> kgc:hasToken true .
    <task_B3> kgc:hasToken true .
    <task_A> kgc:completedAt "tx_123" .
}
WHERE {
    <task_A> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
}
```

**QuadDelta Result**:
```python
QuadDelta(
    removals=(
        (task_A, KGC.hasToken, Literal(True)),
    ),
    additions=(
        (task_B1, KGC.hasToken, Literal(True)),
        (task_B2, KGC.hasToken, Literal(True)),
        (task_B3, KGC.hasToken, Literal(True)),
        (task_A, KGC.completedAt, Literal("tx_123")),
    ),
)
```

### Example 2: WCP-4 (XOR-Split) via Filter + ExactlyOne

**Python**:
```python
ctx = TransactionContext(tx_id="tx_456", data={"priority": "high"})
delta = KGCKernel.filter(graph, decision, ctx, {"selectionMode": "exactlyOne"})
```

**Resulting SPARQL** (with structured predicates):
```sparql
PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>

CONSTRUCT {
    <decision> kgc:tokenRemoved true .
    <task_urgent> kgc:hasToken true .
    <decision> kgc:completedAt "tx_456" .
}
WHERE {
    <decision> yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?target .
    ?flow yawl:ordering ?order .

    # Structured predicate evaluation
    OPTIONAL {
        ?flow yawl:predicate ?pred .
        ?pred kgc:leftOperand "priority" ;
              kgc:operator "=" ;
              kgc:rightOperand "high" .

        <ctx_decision_tx_456> kgc:priority ?ctxPriority .
        FILTER(?ctxPriority = "high")
        BIND(?target AS ?matched)
    }

    # Select first match
    { SELECT (MIN(?order) AS ?minOrder) WHERE {
        <decision> yawl:flowsInto ?f .
        ?f yawl:ordering ?order .
    }}
    FILTER(?order = ?minOrder && BOUND(?matched))
}
LIMIT 1
```

**QuadDelta Result**:
```python
QuadDelta(
    removals=(
        (decision, KGC.hasToken, Literal(True)),
    ),
    additions=(
        (task_urgent, KGC.hasToken, Literal(True)),
        (decision, KGC.completedAt, Literal("tx_456")),
    ),
)
```

---

## Implementation Roadmap

### Phase 1: Stateless Verbs (Transmute, Copy Topology, Void)
- ✅ Already minimal SPARQL
- Refactor to use `_graph_to_quaddelta` helper

### Phase 2: Cardinality Extensions (Copy)
- Implement `copy_static`, `copy_incremental`
- Add VALUES-based sequence generation
- Test WCP-13, WCP-15

### Phase 3: Predicate Evaluation (Filter)
- Define structured predicate vocabulary in RDF
- Implement SPARQL predicate matching
- Test WCP-4, WCP-6

### Phase 4: Join Counting (Await)
- Implement `await_all`, `await_first`, `await_active`
- Add threshold subquery patterns
- Test WCP-3, WCP-7, WCP-9

### Phase 5: Context Materialization
- Build `materialize_context()` helper
- Implement dynamic cardinality/threshold
- Test WCP-14

### Phase 6: Cleanup
- Remove Python list comprehensions
- Remove Python loops in verb implementations
- Verify all routing is SPARQL CONSTRUCT

---

## Benefits

### 1. **Pure Declarative Logic**
All token routing decisions expressed as SPARQL queries, not imperative Python loops.

### 2. **Ontology-Driven**
Routing logic can be modified by changing RDF triples, not Python code.

### 3. **Auditable**
SPARQL queries are logged and can be replayed for provenance.

### 4. **Parallelizable**
SPARQL engines can optimize graph queries better than Python loops.

### 5. **Testable**
Each SPARQL query can be tested independently against RDF fixtures.

---

## Constraints

### 1. **SPARQL 1.1 Limitations**
- No sequence generation (need VALUES workaround)
- No arbitrary Python expression evaluation (need structured predicates)

### 2. **Context Data Materialization**
- Requires temporary triple injection for runtime data
- Adds overhead for dynamic cardinality/threshold

### 3. **Predicate Evaluation**
- Full Python `eval()` not possible in SPARQL
- Requires defining structured predicate vocabulary (kgc:ComparisonPredicate)

---

## Conclusion

This architecture eliminates Python loops from the KGCL Kernel by:
1. **SPARQL CONSTRUCT** generates token routing triples directly
2. **Parameters modify queries** (cardinality/threshold/selectionMode)
3. **Helper converts** CONSTRUCT results to QuadDelta
4. **Python role**: Query builder, not router

**Next Steps**:
1. Implement `_graph_to_quaddelta` helper
2. Refactor Copy verb with cardinality-specific queries
3. Define structured predicate vocabulary
4. Implement Filter verb with predicate matching
5. Implement Await verb with threshold subqueries
6. Remove Python loops and comprehensions
7. Add comprehensive SPARQL routing tests
