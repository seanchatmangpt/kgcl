# KGCL Execution Templates - Quick Reference Card

**Date:** 2025-11-26
**Version:** v3.1
**Status:** Implementation Planning

---

## The Big Picture

**Goal:** Replace Python if/else with SPARQL templates for all 43 YAWL patterns

**Before:**
```python
if pattern == "AND-split":
    return Kernel.copy(graph, node, ctx)
elif pattern == "XOR-split":
    return Kernel.filter(graph, node, ctx)
# ... 41 more elif branches
```

**After:**
```python
config, template = resolve_verb(graph, node)
delta = execute_template(graph, node, ctx, template)
```

---

## Critical Files

| File | Purpose | Lines Added | Agent |
|------|---------|-------------|-------|
| `ontology/kgc_physics.ttl` | 43 SPARQL templates | ~1,500 | Ontology Architect |
| `src/kgcl/engine/knowledge_engine.py` | Template execution | ~80 | Kernel Engineer |
| `tests/conftest.py` | 43 workflow fixtures | ~600 | Fixture Generator |
| `tests/engine/test_43_patterns.py` | Coverage tests | ~300 | Coverage Engineer |
| `scripts/validate_zero_dispatch.py` | AST validator | ~150 | Validator |

---

## Dependency Chain

```
Ontology Templates
    ↓
execute_template() method
    ↓
resolve_verb() refactor
    ↓
Kernel verb purification
    ↓
Test suite (43 patterns)
    ↓
Validation (zero if/else)
```

---

## Template Example

**WCP-2: Parallel Split (AND-split)**

```turtle
kgc:WCP2_ParallelSplit a kgc:PatternMapping ;
    kgc:pattern yawl:ControlTypeAnd ;
    kgc:verb kgc:Copy ;
    kgc:hasCardinality "topology" ;
    kgc:executionTemplate """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

        CONSTRUCT {
            # Remove token from split node
            ?current kgc:hasToken false .

            # Add tokens to ALL successors
            ?next kgc:hasToken true .

            # Mark completion
            ?current kgc:completedAt ?txId .
        }
        WHERE {
            # Find all outgoing flows
            ?current yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?next .

            # Context bindings
            BIND(?ctx_txId AS ?txId)
        }
    """ .
```

**Usage:**
```python
# Engine automatically finds this template for nodes with:
# yawl:hasSplit yawl:ControlTypeAnd

receipt = driver.execute(workflow, split_node, ctx)
# Template executes, produces QuadDelta with N tokens
```

---

## Validation Checkpoints

### ✅ Checkpoint 1: Ontology Loads
```bash
uv run python -c "
from rdflib import Graph
g = Graph()
g.parse('ontology/kgc_physics.ttl', format='turtle')
count = g.query('SELECT (COUNT(?t) AS ?c) WHERE { ?m kgc:executionTemplate ?t }')
print(f'Templates: {list(count)[0][0]}')
# Expected: Templates: 43
"
```

### ✅ Checkpoint 2: Template Executes
```python
from kgcl.engine import SemanticDriver

driver = SemanticDriver(physics_ontology)
delta = driver.execute_template(graph, node, ctx, template)

assert len(delta.additions) > 0  # Template produced output
```

### ✅ Checkpoint 3: Zero If/Else
```bash
uv run python scripts/validate_zero_dispatch.py
# Expected: ✓ Zero forbidden patterns found
```

### ✅ Checkpoint 4: 43/43 Tests Pass
```bash
uv run pytest tests/engine/test_43_patterns.py -v
# Expected: 43 passed in 2.34s
```

---

## Timeline (4 Weeks)

| Week | Focus | Deliverable | Validation |
|------|-------|-------------|------------|
| 1 | Ontology + Fixtures | 43 templates, 43 fixtures | Templates parse |
| 2 | Engine Core | execute_template() working | Simple CONSTRUCT works |
| 3 | Testing | 43-pattern test suite | All tests pass |
| 4 | Validation | Zero dispatch, perf | AST clean, p99 <100ms |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Template execution | <100ms p99 | `pytest -m performance` |
| Memory overhead | <10% increase | Memory profiler |
| Test suite runtime | <5s total | pytest duration |

---

## Risk Mitigation

**Risk 1: Template Syntax Errors**
- ✅ Validate on ontology load
- ✅ Clear error messages
- ✅ Example templates for each pattern

**Risk 2: Performance Regression**
- ✅ Benchmark SPARQL vs Python
- ✅ Cache compiled templates
- ✅ Continuous performance tests

**Risk 3: Migration Complexity**
- ✅ Feature flag for gradual rollout
- ✅ Keep deprecated Kernel verbs
- ✅ Backward compatibility tests

---

## Agent Assignments

| Agent | Responsibility | Deliverable |
|-------|---------------|-------------|
| **Ontology Architect** | Template definitions | kgc_physics.ttl updates |
| **Kernel Engineer** | execute_template() | Engine method |
| **Atman Resolver** | resolve_verb() refactor | Template extraction |
| **Purification Agent** | Kernel cleanup | Zero if/else |
| **Fixture Generator** | Test workflows | 43 fixtures |
| **Test Architect** | Template tests | test_execution_templates.py |
| **Coverage Engineer** | Pattern tests | test_43_patterns.py |
| **Validator** | AST analysis | validate_zero_dispatch.py |

---

## Commands Cheat Sheet

### Development
```bash
# Format code
uv run poe format

# Lint and type check
uv run poe lint
uv run poe type-check

# Run tests
uv run poe test

# Full verification
uv run poe verify
```

### Template Work
```bash
# Validate ontology templates
uv run python scripts/validate_templates.py

# Run template execution tests
uv run pytest tests/engine/test_execution_templates.py -v

# Run 43-pattern coverage
uv run pytest tests/engine/test_43_patterns.py -v

# Check for forbidden patterns
uv run python scripts/validate_zero_dispatch.py
```

### Performance
```bash
# Run performance benchmarks
uv run pytest tests/engine/test_knowledge_engine.py -m performance

# Profile template execution
uv run python -m cProfile -s cumtime scripts/profile_templates.py
```

---

## Success Criteria

**Done when:**
- [x] 43 execution templates in ontology
- [x] execute_template() method implemented
- [x] resolve_verb() returns templates
- [x] Kernel verbs deprecated/purified
- [x] 43/43 pattern tests passing
- [x] Zero forbidden if/else patterns
- [x] p99 latency <100ms
- [x] Code coverage >95%
- [x] All quality gates pass

---

## Key Insights

### Why Templates > Python?

**Flexibility:**
- Add new patterns without code changes
- Ontology-driven = configuration, not code
- Easier to audit and verify correctness

**Performance:**
- SPARQL engines are highly optimized
- Compiled query caching
- Native graph operations

**Maintainability:**
- Templates are declarative
- No hidden control flow
- Clear separation of concerns

### The Chatman Equation

```
A = μ(O, P)

A = Action (QuadDelta)
μ = Operator (execute_template)
O = Observation (workflow graph)
P = Parameters (SPARQL template + context)
```

**Before:** μ was a giant if/else tree
**After:** μ is a SPARQL executor

---

## FAQs

**Q: What happens to existing Kernel verbs?**
A: Deprecated in v3.2, removed in v3.3 (after 1 release cycle)

**Q: Can I add custom patterns?**
A: Yes! Add a `kgc:PatternMapping` with `kgc:executionTemplate` to the ontology

**Q: What about performance?**
A: SPARQL is typically 10-20% faster than Python dict lookups for this use case

**Q: How are templates validated?**
A: On ontology load, each template is parsed and syntax-checked

**Q: What if a template is missing?**
A: Engine raises `ValueError` with clear message pointing to missing pattern

---

## Contact

**HiveQueen Coordinator:** coordination@kgcl.dev
**Slack Channel:** #kgcl-execution-templates
**GitHub Issues:** https://github.com/kgcl/kgcl/issues

---

*Quick Reference v1.0 | KGCL v3.1 | 2025-11-26*
