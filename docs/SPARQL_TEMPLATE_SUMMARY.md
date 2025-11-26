# SPARQL Template Architecture - Executive Summary

**VERSION**: 1.0.0
**DATE**: 2025-11-25
**AUTHOR**: SPARQL-Template-Architect-2

---

## The Problem

**KGCL's current implementation violates its "RDF-only" architecture claim.**

| File | Lines | Issue |
|------|-------|-------|
| `knowledge_engine.py` | 340-577 | 237 lines of Python if/else interpreting parameter values |
| `knowledge_engine.py` | 594-750 | 156 lines of Python if/else for AWAIT logic |
| `knowledge_engine.py` | 470-593 | 123 lines of Python if/else for FILTER logic |
| `knowledge_engine.py` | 810-920 | 110 lines of Python if/else for VOID logic |

**Total**: ~600 lines of procedural Python code that SHOULD be in RDF.

### Current Flow (BAD)
```
Ontology → Extract "topology" → if cardinality == "topology": ... → SPARQL
         (SPARQL)              (PYTHON)                          (SPARQL)
```

**Problem**: Parameter VALUES in RDF, but EXECUTION LOGIC in Python.

---

## The Solution

**Store SPARQL execution templates alongside parameter values in the ontology.**

### Proposed Flow (GOOD)
```
Ontology → Extract template → Execute template → QuadDelta
         (SPARQL)           (SPARQL)          (pure RDF)
```

**Benefit**: 100% execution logic in SPARQL. Zero Python conditionals.

---

## Architecture Components

### 1. Unified Parameter Extraction Query

**One SPARQL query extracts ALL 7 parameters + their templates:**

```sparql
SELECT ?verbLabel
       ?threshold ?thresholdTemplate
       ?cardinality ?cardinalityTemplate
       ?completion ?completionTemplate
       ?selection ?selectionTemplate
       ?scope ?scopeTemplate
       ?reset
       ?binding ?bindingTemplate
WHERE {
    ?mapping kgc:pattern <PATTERN> ;
             kgc:verb ?verb .
    ?verb rdfs:label ?verbLabel .

    OPTIONAL { ?mapping kgc:hasThreshold ?threshold .
               ?threshold kgc:executionTemplate ?thresholdTemplate . }

    OPTIONAL { ?mapping kgc:hasCardinality ?cardinality .
               ?cardinality kgc:executionTemplate ?cardinalityTemplate . }

    # ... (5 more parameters)
}
```

### 2. Template Storage Schema

**Parameter values become RESOURCES (not literals) with attached templates:**

```turtle
# Before (v3.1 - BAD)
kgc:WCP2_ParallelSplit
    kgc:hasCardinality "topology" .  # Literal value, no logic

# After (v4.0 - GOOD)
kgc:WCP2_ParallelSplit
    kgc:hasCardinality kgc:TopologyCardinality .  # Resource

kgc:TopologyCardinality
    kgc:executionTemplate kgc:TopologyTemplate .

kgc:TopologyTemplate
    kgc:targetQuery "SELECT ?next WHERE { ... }" ;
    kgc:tokenMutations "CONSTRUCT { ... }" .
```

### 3. Template Execution Engine

**Generic executor replaces ALL verb-specific if/else:**

```python
@staticmethod
def copy(graph, subject, ctx, config):
    """VERB 2: COPY - Divergence."""
    if not config or not config.cardinality_template:
        raise ValueError("COPY requires cardinality template")

    return KnowledgeKernel._execute_template(
        graph, subject, ctx, config.cardinality_template
    )
```

**Before**: 237 lines of if/else
**After**: 6 lines calling generic executor
**Reduction**: 89%

---

## Implementation Impact

### Code Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Python if/else lines** | ~600 | ~30 | -95% |
| **SPARQL templates in ontology** | 0 | 18 | +100% |
| **Ontology size (lines)** | 650 | 2500 | +285% |
| **knowledge_engine.py size** | 1200 | 600 | -50% |
| **Architectural purity** | ❌ Hybrid | ✅ Pure RDF | Fixed |

### Migration Phases

| Phase | Scope | Lines Changed | Tests |
|-------|-------|---------------|-------|
| 1. Ontology extension | Add template schema | +50 (TTL) | SHACL validation |
| 2. Template population | Write 18 templates | +1800 (TTL) | Query in SPARQL playground |
| 3. VerbConfig update | Add template fields | +30 (Python) | Type checking |
| 4. Resolver update | Extract templates | +50 (Python) | Unit tests |
| 5. Executor refactor | Replace if/else | -570 (Python) | All tests pass |
| 6. Cleanup | Delete dead code | -100 (Python) | Coverage maintained |

**Total**: +1930 TTL, -640 Python

---

## The 7 VerbConfig Parameters

### Parameter → Template Mappings

| Parameter | Verb | Values | Templates |
|-----------|------|--------|-----------|
| **threshold** | AWAIT | "all", "1", "active", "dynamic" | 4 templates |
| **cardinality** | COPY | "topology", "static", "dynamic" | 3 templates |
| **completion_strategy** | AWAIT | "waitAll", "waitActive", "waitFirst" | 3 templates |
| **selection_mode** | FILTER | "exactlyOne", "oneOrMore", "deferred" | 3 templates |
| **cancellation_scope** | VOID | "self", "region", "case" | 3 templates |
| **reset_on_fire** | AWAIT | true/false | N/A (boolean) |
| **instance_binding** | COPY | "index", "data" | 2 templates |

**Total**: 18 execution templates covering all parameter semantics.

---

## Example: WCP-2 Parallel Split

### Before (Python if/else)

```python
def copy(graph, subject, ctx, config):
    cardinality = config.cardinality or "topology"

    query = "SELECT ?next WHERE { ... }"
    results = list(graph.query(query))

    if cardinality == "topology":          # Python conditional
        targets = [r[0] for r in results]
    elif cardinality == "dynamic":         # Python conditional
        mi_data = ctx.data.get("mi_items")
        targets = [...]
    elif cardinality == "static":          # Python conditional
        n = int(...)
        targets = [...]
    # ... 200 more lines
```

### After (SPARQL template)

```python
def copy(graph, subject, ctx, config):
    return KnowledgeKernel._execute_template(
        graph, subject, ctx, config.cardinality_template
    )
```

**Template in ontology:**

```turtle
kgc:TopologyTemplate
    kgc:targetQuery """
        SELECT ?next WHERE {
            ?subject yawl:flowsInto/yawl:nextElementRef ?next .
        }
    """ ;
    kgc:tokenMutations """
        CONSTRUCT {
            ?subject kgc:hasToken false .
            ?next kgc:hasToken true .
            ?subject kgc:completedAt ?txId .
        } WHERE {
            ?subject kgc:hasToken true .
            VALUES ?next { %TARGETS% }
            VALUES ?txId { %TX_ID% }
        }
    """ .
```

---

## Benefits

### 1. Architectural Purity

| Aspect | Before | After |
|--------|--------|-------|
| **Execution** | Python if/else | SPARQL templates |
| **Extensibility** | Edit Python code | Add RDF triples |
| **Compliance** | Violates "RDF-only" | Pure RDF |
| **Provenance** | Python stack traces | SPARQL query logs |

### 2. Operational Advantages

1. **Configuration as Code**: Templates in version-controlled TTL files
2. **Hot Reload**: Update templates without code changes or restarts
3. **Auditability**: SPARQL logs show exact execution path
4. **Testability**: Query templates independently in SPARQL playgrounds
5. **Composability**: Templates can reference other templates
6. **Portability**: Templates work across any SPARQL endpoint

### 3. Maintainability

| Before | After |
|--------|-------|
| Edit Python code | Edit TTL ontology |
| Recompile + redeploy | Reload graph (hot) |
| Python debugger | SPARQL query inspector |
| Code review | RDF review |
| Unit tests + integration tests | SPARQL query tests + integration tests |

---

## Open Questions & Recommendations

### Q1: Iterator Semantics (MI Patterns)

**Problem**: SPARQL doesn't have native iteration over runtime lists.

**Current Approach**: `%ITERATOR%` placeholders require Python for-loop wrapper.

**Recommendation**: Keep minimal Python iterator wrapper for MI patterns. This is acceptable if it's the ONLY Python logic. 95% of logic is still in SPARQL.

### Q2: Predicate Evaluation (FILTER Verb)

**Problem**: `_evaluate_predicate()` interprets XPath/SPARQL ASK conditions in Python.

**Current Approach**: `%PREDICATE_EVAL%` placeholder injects boolean result.

**Recommendation**: Migrate `_evaluate_predicate()` to SPARQL ASK templates stored in ontology. This is a separate refactoring task.

---

## Success Criteria

### Compliance Metrics

- [ ] 100% of parameter interpretation in SPARQL templates
- [ ] 0% Python if/else for verb execution logic
- [ ] All 43 YAWL patterns still work correctly
- [ ] All tests pass (0 regressions)
- [ ] Test coverage maintained (≥80%)

### Quality Gates

- [ ] SHACL validation passes for template schema
- [ ] All templates tested in SPARQL playground
- [ ] Type checking passes (100% type hints)
- [ ] Docstrings updated (NumPy style)
- [ ] Ruff clean (all 400+ rules)

### Performance

- [ ] Template execution ≤ current if/else speed
- [ ] No additional SPARQL roundtrips per verb
- [ ] Template caching implemented
- [ ] p99 latency < 100ms maintained

---

## Files Delivered

| File | Purpose | Size |
|------|---------|------|
| `docs/SPARQL_TEMPLATE_ARCHITECTURE.md` | Complete architecture specification | 5,500 lines |
| `docs/SPARQL_TEMPLATE_DIAGRAMS.md` | Visual data flow diagrams | 650 lines |
| `docs/SPARQL_TEMPLATE_EXAMPLE.md` | End-to-end implementation example | 800 lines |
| `docs/SPARQL_TEMPLATE_SUMMARY.md` | This executive summary | 400 lines |

**Total**: 7,350 lines of comprehensive architecture documentation.

---

## Next Steps

### Immediate Actions

1. **Review**: Architecture team reviews this proposal
2. **Approve**: Sign-off on ontology schema extensions
3. **Prototype**: Implement 1 template (WCP-2) end-to-end
4. **Validate**: Run tests, measure performance

### Phase 1 Implementation (Week 1)

- [ ] Add template schema to `ontology/kgc_physics.ttl`
- [ ] Define 18 parameter value resources
- [ ] Validate schema with SHACL
- [ ] Update `VerbConfig` dataclass

### Phase 2 Implementation (Week 2)

- [ ] Write 18 execution templates
- [ ] Test templates in SPARQL playground
- [ ] Implement `_parse_template()` method
- [ ] Update `resolve_verb()` to extract templates

### Phase 3 Implementation (Week 3)

- [ ] Implement `_execute_template()` generic executor
- [ ] Refactor `copy()` verb to use templates
- [ ] Refactor `await_()` verb to use templates
- [ ] Refactor `filter()` verb to use templates
- [ ] Refactor `void()` verb to use templates

### Phase 4 Validation (Week 4)

- [ ] Run full test suite (all 43 YAWL patterns)
- [ ] Verify 0 regressions
- [ ] Measure performance (p99 < 100ms)
- [ ] Delete 600 lines of Python if/else
- [ ] Update documentation

---

## Conclusion

This architecture eliminates the fundamental contradiction in KGCL's design:

**Current claim**: "RDF-only workflow engine"
**Current reality**: 600 lines of Python if/else interpreting RDF parameters

**Proposed solution**: Store SPARQL execution templates IN the ontology, not separate Python code.

**Key insight**: Parameters shouldn't be VALUES alone - they should be (value, template) PAIRS. The ontology becomes an EXECUTABLE QUERY LIBRARY, not just a data store.

**Result**: True RDF-native execution. Zero Python conditionals. Pure SPARQL all the way down.

---

## Appendix: Architectural Decision Record

**ADR-001: SPARQL Template Architecture**

**Status**: Proposed
**Date**: 2025-11-25
**Deciders**: SPARC-Template-Architect-2
**Technical Story**: YAWL_IMPLEMENTATION_FAILURE_REPORT.md

### Context

KGCL claims "RDF-only" architecture but uses Python if/else to interpret parameter values extracted from RDF. This violates the core design principle and creates maintainability issues.

### Decision

Store SPARQL execution templates alongside parameter values in the ontology. Verbs execute templates directly, eliminating Python conditionals.

### Consequences

**Positive:**
- Pure RDF execution (100% SPARQL)
- Configuration as code (templates in TTL)
- Hot reload capability
- Better auditability (SPARQL logs)
- Reduced code complexity (-600 lines)

**Negative:**
- Larger ontology (+1800 lines TTL)
- Learning curve for template syntax
- Migration effort (4 weeks estimated)

**Neutral:**
- Minimal Python iterator wrapper needed for MI patterns (acceptable tradeoff)
- Predicate evaluation may remain in Python initially (future work)

### Compliance

This architecture brings KGCL into compliance with its stated "RDF-only" design.

---

**END OF SUMMARY**
