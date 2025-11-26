# RDF Purity Maturity Matrix

## The Goal: Logic IS Data

**Zero Python if/else for pattern dispatch.** All behavior determined by RDF properties.

## Maturity Levels

| Level | Description | Python Code | RDF Properties |
|-------|-------------|-------------|----------------|
| **L0: Hardcoded** | Python if/else on pattern names | `if pattern == "WCP-4"` | None |
| **L1: String Params** | Python derives flags from strings | `if selection_mode == "exactlyOne": stop_first = True` | `kgc:selectionMode "exactlyOne"` |
| **L2: Boolean Flags** | Python reads flags, decides behavior | `if stop_on_first: break` | `kgc:stopOnFirstMatch true` |
| **L3: Numeric Config** | Python reads numbers, applies formula | `if threshold_value >= count: fire` | `kgc:thresholdValue 3` |
| **L4: SPARQL Templates** | Python executes RDF-stored SPARQL | `graph.update(template)` | `kgc:executionTemplate "CONSTRUCT {...}"` |
| **L5: Pure RDF** | Python is just a SPARQL executor | None | All logic in ontology |

## Current State Analysis

### Kernel.filter

| Behavior | Current Level | Issue |
|----------|---------------|-------|
| XOR (stop at first) | L2 | `if stop_on_first: break` in Python |
| Deferred choice | L2 | `if is_deferred: return awaiting` in Python |
| Mutex interleaved | L2 | `if is_mutex: check siblings` in Python |
| Predicate inversion | L2 | `if invert_predicate: not result` in Python |
| Default path | L2 | `if not selected and default: use default` in Python |

**Problem:** The `if` statements are in Python. The RDF just provides flags.

### Kernel.await_

| Behavior | Current Level | Issue |
|----------|---------------|-------|
| Threshold check | L3 | `if completed >= threshold: fire` in Python |
| Active count | L2 | `if use_active_count: count = total - voided` in Python |
| Dynamic threshold | L2 | `if use_dynamic: threshold = ctx.data` in Python |
| Ignore subsequent | L2 | `if ignore_subsequent: ...` in Python |

**Problem:** Threshold comparison is Python math, not RDF logic.

### Kernel.copy

| Behavior | Current Level | Issue |
|----------|---------------|-------|
| Topology copy | L1 | Default behavior, no RDF check |
| Static cardinality | L3 | `if card == -2: read graph.yawl:minimum` in Python |
| Dynamic cardinality | L2 | `if use_dynamic: len(ctx.data)` in Python |
| Incremental | L3 | `if card == -3: count existing + 1` in Python |

**Problem:** Cardinality modes are Python if/else on sentinel values.

## Target State: Level 5 (Pure RDF)

### What L5 Looks Like

```turtle
# WCP-4 in pure RDF: no Python logic needed
kgc:WCP4_ExclusiveChoice a kgc:PatternMapping ;
    kgc:verb kgc:Filter ;
    kgc:executionTemplate """
        CONSTRUCT {
            ?firstMatch kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        }
        WHERE {
            ?subject yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?firstMatch ;
                  yawl:hasPredicate ?pred .
            ?pred yawl:query ?query .
            # Predicate evaluation via SPARQL function or external call
            FILTER(kgc:evaluate(?query, ?data))
        }
        LIMIT 1
    """ ;
    kgc:removalTemplate """
        DELETE WHERE {
            ?subject kgc:hasToken true .
        }
    """ .
```

### The Kernel Becomes:

```python
def execute_verb(graph, subject, ctx, config):
    """Pure SPARQL executor - NO Python logic."""
    # 1. Get execution template from ontology
    template = config.execution_template

    # 2. Bind variables
    bindings = {"subject": subject, "txId": ctx.tx_id, "data": ctx.data}

    # 3. Execute SPARQL CONSTRUCT
    additions = graph.query(template, initBindings=bindings)

    # 4. Execute SPARQL DELETE
    removals = graph.query(config.removal_template, initBindings=bindings)

    return QuadDelta(additions, removals)
```

## Migration Path

### Phase 1: Complete SPARQL Templates (Current Priority)

Move ALL verb logic into `kgc:executionTemplate` and `kgc:removalTemplate`.

**Already in ontology:**
- WCP-43 Explicit Termination has full template

**Need templates for:**
- All FILTER patterns (WCP-4, 6, 10, 16, 17, 21)
- All AWAIT patterns (WCP-3, 7, 9, 18, 34-36)
- All COPY patterns (WCP-2, 12-15)
- All TRANSMUTE patterns (WCP-1, 5, 8)
- All VOID patterns (WCP-11, 19-20)

### Phase 2: Custom SPARQL Functions

Implement `kgc:evaluate(?query, ?data)` as custom SPARQL function for predicate evaluation.

### Phase 3: Remove Python Logic

Once all templates exist, Kernel methods become:
1. Read template from VerbConfig
2. Execute template with bindings
3. Return results

**Zero Python if/else.**

## Current Implementation Status

### Patterns WITH Execution Templates (L5 Ready - Pure SPARQL)

These patterns use `PureRDFKernel.execute()` with zero Python conditionals:

| Pattern | Verb | Template Status | Notes |
|---------|------|-----------------|-------|
| WCP-1 Sequence | TRANSMUTE | ✅ L5 Ready | Token flows via SPARQL CONSTRUCT |
| WCP-2 Parallel Split | COPY | ✅ L5 Ready | Topology-only, N from graph structure |
| WCP-5 Simple Merge | TRANSMUTE | ✅ L5 Ready | First arrival fires |
| WCP-8 Multi Merge | TRANSMUTE | ✅ L5 Ready | Any arrival fires |
| WCP-11 Implicit Termination | VOID | ✅ L5 Ready | Scope-based void |
| WCP-19 Cancel Task | VOID | ✅ L5 Ready | Self-cancellation |
| WCP-20 Cancel Case | VOID | ✅ L5 Ready | Case-wide void |
| WCP-21 Cancel Region | VOID | ✅ L5 Ready | Region-scoped void |
| WCP-22 Cancel MI | VOID | ✅ L5 Ready | Instance-scoped void |
| WCP-24 Exception Handling | VOID | ✅ L5 Ready | Exception handler routing |
| WCP-25 Timeout | VOID | ✅ L5 Ready | Timeout void |
| WCP-43 Explicit Termination | VOID | ✅ L5 Ready | Full case termination |

### Patterns WITHOUT Templates (L2/L3 - Requires Python Logic)

These patterns CANNOT be pure L5 without custom SPARQL functions because they require:
- **Predicate evaluation** (runtime expression evaluation)
- **Threshold counting** (counting tokens and comparing to N)
- **Dynamic cardinality** (determining N from ctx.data at runtime)

| Pattern | Verb | Level | Reason Cannot Be L5 |
|---------|------|-------|---------------------|
| **FILTER Patterns (need predicate evaluation)** |
| WCP-4 Exclusive Choice | FILTER | L2 | Python evaluates `yawl:hasPredicate` expressions |
| WCP-6 Multi Choice | FILTER | L2 | Python evaluates predicates for each branch |
| WCP-10 Arbitrary Cycles | FILTER | L2 | Loop condition predicate evaluation |
| WCP-16 Deferred Choice | FILTER | L2 | Environment/resource determines path |
| WCP-17 Interleaved Parallel | FILTER | L2 | Mutex sibling checking in Python |
| **AWAIT Patterns (need threshold counting)** |
| WCP-3 Synchronization | AWAIT | L3 | `completed >= threshold` in Python |
| WCP-7 Structured Sync Merge | AWAIT | L3 | Active count calculation in Python |
| WCP-9 Discriminator | AWAIT | L3 | First arrival detection in Python |
| WCP-18 Milestone | AWAIT | L3 | Milestone state check in Python |
| WCP-34 MI Partial Join | AWAIT | L3 | N-of-M threshold counting |
| WCP-35 MI Cancelling Join | AWAIT | L3 | Threshold + cancellation logic |
| WCP-36 MI Dynamic Join | AWAIT | L3 | Dynamic threshold from ctx.data |
| **COPY Patterns (need dynamic cardinality)** |
| WCP-12 MI No Sync | COPY | L2 | N from ctx.data['mi_items'] |
| WCP-13 MI Design Time | COPY | L3 | N from yawl:minimum graph query |
| WCP-14 MI Runtime | COPY | L2 | N from ctx.data at runtime |
| WCP-15 MI No Prior | COPY | L3 | Incremental count + 1 |

### Path to Full L5

To achieve L5 for ALL patterns requires **Phase 2: Custom SPARQL Functions**:

1. `kgc:evaluate(?predicateQuery, ?contextData)` - Evaluate predicate expressions
2. `kgc:countTokens(?scope)` - Count active tokens in scope
3. `kgc:threshold(?count, ?required)` - Boolean threshold comparison
4. `kgc:cardinality(?source, ?mode)` - Compute cardinality from source

Until custom SPARQL functions are implemented, these patterns remain at L2/L3.

## Success Criteria

- [x] PureRDFKernel exists with single `execute()` method (ZERO conditionals)
- [x] L5-compatible patterns have `kgc:executionTemplate` in ontology
- [x] L5-compatible patterns have `kgc:removalTemplate` in ontology
- [x] Driver dispatches to PureRDFKernel when template exists
- [x] All 318 tests pass
- [ ] All 43 patterns L5 ready (blocked on custom SPARQL functions)
- [ ] Zero Python if/else on pattern behavior (blocked on custom SPARQL functions)
