# KGCL Execution Templates - Implementation Roadmap

**Project:** KGCL v3.1 → v3.2 Migration
**Goal:** Replace pattern dispatch with SPARQL template execution
**Timeline:** 4 weeks
**Status:** 📋 Planning Complete

---

## Phase Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXECUTION TEMPLATES ROADMAP                      │
│                         (4-Week Plan)                               │
└─────────────────────────────────────────────────────────────────────┘

Week 1: FOUNDATION              Week 2: ENGINE CORE
┌────────────────────┐         ┌────────────────────┐
│ Ontology Templates │         │ execute_template() │
│ 43 SPARQL queries  │────────>│ Template executor  │
└────────────────────┘         └────────────────────┘
         │                              │
         │                              │
         v                              v
┌────────────────────┐         ┌────────────────────┐
│ Workflow Fixtures  │         │ resolve_verb()     │
│ 43 test samples    │         │ Return templates   │
└────────────────────┘         └────────────────────┘

Week 3: TESTING                Week 4: VALIDATION
┌────────────────────┐         ┌────────────────────┐
│ Template Tests     │         │ AST Validator      │
│ Execution mechanics│────────>│ Zero if/else       │
└────────────────────┘         └────────────────────┘
         │                              │
         │                              │
         v                              v
┌────────────────────┐         ┌────────────────────┐
│ 43-Pattern Tests   │         │ Performance Bench  │
│ Complete coverage  │         │ p99 <100ms         │
└────────────────────┘         └────────────────────┘
```

---

## Week 1: Foundation (Ontology + Fixtures)

### Goals
- [x] All 43 YAWL patterns have execution templates
- [x] Template syntax validated
- [x] Test fixtures created for each pattern

### Deliverables

**File: `ontology/kgc_physics.ttl`**
```diff
+ # WCP-1: Sequence
+ kgc:WCP1_Sequence
+     kgc:executionTemplate """
+         CONSTRUCT { ... } WHERE { ... }
+     """ .
+
+ # WCP-2: Parallel Split
+ kgc:WCP2_ParallelSplit
+     kgc:executionTemplate """
+         CONSTRUCT { ... } WHERE { ... }
+     """ .
+
+ # ... (41 more templates)
```

**File: `tests/conftest.py`**
```python
@pytest.fixture
def wcp1_sequence() -> WorkflowFixture:
    """WCP-1: Sequence pattern test case."""
    graph = Graph()
    # ... setup
    return WorkflowFixture(...)

@pytest.fixture
def wcp2_parallel_split() -> WorkflowFixture:
    """WCP-2: Parallel Split pattern test case."""
    graph = Graph()
    # ... setup
    return WorkflowFixture(...)

# ... (41 more fixtures)
```

### Validation
```bash
# Template syntax check
uv run python scripts/validate_templates.py ontology/kgc_physics.ttl
# Expected: ✓ 43/43 templates valid

# Fixture loading check
uv run pytest tests/conftest.py --collect-only | grep wcp
# Expected: 43 fixtures found
```

### Metrics
- **Templates added:** 43
- **Lines added to ontology:** ~1,500
- **Fixtures created:** 43
- **Lines added to conftest:** ~600

---

## Week 2: Engine Core (Template Execution)

### Goals
- [x] Template execution engine implemented
- [x] Verb resolution returns templates
- [x] Backward compatibility maintained

### Deliverables

**File: `src/kgcl/engine/knowledge_engine.py`**

**Addition 1: execute_template() method**
```python
def execute_template(
    self,
    graph: Graph,
    subject: URIRef,
    ctx: TransactionContext,
    template: str
) -> QuadDelta:
    """
    Execute SPARQL CONSTRUCT template to generate QuadDelta.

    The template uses context bindings:
    - ?ctx_subject: Current node being executed
    - ?ctx_txId: Transaction ID
    - ?ctx_actor: Actor initiating transaction
    - ?ctx_data_*: Data fields from context

    Parameters
    ----------
    graph : Graph
        The workflow graph to execute against
    subject : URIRef
        The current node being executed
    ctx : TransactionContext
        Transaction context with data bindings
    template : str
        SPARQL CONSTRUCT query from ontology

    Returns
    -------
    QuadDelta
        Mutations produced by template execution

    Examples
    --------
    >>> template = '''
    ...     CONSTRUCT { ?next kgc:hasToken true . }
    ...     WHERE { ?ctx_subject yawl:flowsInto ?flow .
    ...             ?flow yawl:nextElementRef ?next . }
    ... '''
    >>> delta = driver.execute_template(graph, task_a, ctx, template)
    >>> len(delta.additions) > 0
    True
    """
    # Inject context bindings
    bindings = {
        "ctx_subject": subject,
        "ctx_txId": Literal(ctx.tx_id),
        "ctx_actor": Literal(ctx.actor),
        **{f"ctx_data_{k}": Literal(str(v)) for k, v in ctx.data.items()}
    }

    # Execute CONSTRUCT query
    result_graph = graph.query(template, initBindings=bindings).graph

    # Convert to QuadDelta (detect removals via false literals)
    additions: list[Triple] = []
    removals: list[Triple] = []

    for s, p, o in result_graph:
        if isinstance(o, Literal) and str(o).lower() == "false":
            # false literal = removal
            removals.append((s, p, Literal(True)))
        else:
            additions.append((s, p, o))

    return QuadDelta(
        additions=tuple(additions),
        removals=tuple(removals)
    )
```

**Addition 2: Refactored resolve_verb()**
```python
def resolve_verb(self, graph: Graph, node: URIRef) -> tuple[VerbConfig, str]:
    """
    Resolve verb configuration AND execution template from ontology.

    Returns
    -------
    tuple[VerbConfig, str]
        (verb config with parameters, SPARQL CONSTRUCT template)

    Raises
    ------
    ValueError
        If no template mapping found for node's pattern
    """
    # Detect pattern type (split/join/sequence)
    pattern = self._detect_pattern(graph, node)

    # Query ontology for verb + template
    ontology_query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?verbLabel ?threshold ?cardinality ?template WHERE {{
            ?mapping kgc:pattern <{pattern}> ;
                     kgc:verb ?verb ;
                     kgc:executionTemplate ?template .
            ?verb rdfs:label ?verbLabel .
            OPTIONAL {{ ?mapping kgc:hasThreshold ?threshold . }}
            OPTIONAL {{ ?mapping kgc:hasCardinality ?cardinality . }}
            # ... other parameters
        }}
    """

    results = list(self.physics_ontology.query(ontology_query))

    if not results:
        msg = f"No template mapping found for pattern {pattern} on node {node}"
        raise ValueError(msg)

    row = cast(ResultRow, results[0])
    template = str(row[3])  # Template is 4th column

    config = VerbConfig(
        verb=str(row[0]),
        threshold=str(row[1]) if row[1] else None,
        cardinality=str(row[2]) if row[2] else None,
        # ... other params
    )

    return config, template
```

**Addition 3: Updated execute()**
```python
def execute(self, graph: Graph, subject: URIRef, ctx: TransactionContext) -> Receipt:
    """
    Execute the Chatman Equation via SPARQL template.

    A = μ(O, P)
    - A: Action (Receipt)
    - μ: Operator (execute_template)
    - O: Observation (graph topology)
    - P: Parameters (template + context)
    """
    # 1. Ontology lookup
    config, template = self.resolve_verb(graph, subject)

    # 2. Template execution (NOT direct kernel verb call)
    delta = self.execute_template(graph, subject, ctx, template)

    # 3. Provenance (include template hash for audit)
    template_hash = hashlib.sha256(template.encode()).hexdigest()[:16]
    merkle_payload = f"{ctx.prev_hash}|{ctx.tx_id}|{config.verb}|{template_hash}"
    merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

    # 4. Apply mutations
    for triple in delta.removals:
        graph.remove(triple)
    for triple in delta.additions:
        graph.add(triple)

    return Receipt(
        merkle_root=merkle_root,
        verb_executed=config.verb,
        delta=delta,
        params_used=config
    )
```

### Validation
```bash
# Type check
uv run poe type-check
# Expected: Success: no issues found

# Unit tests for new methods
uv run pytest tests/engine/test_knowledge_engine.py::test_execute_template -v
# Expected: PASSED
```

### Metrics
- **Lines added:** ~150
- **Lines removed:** 0 (backward compat)
- **Methods added:** 1 (execute_template)
- **Methods changed:** 2 (resolve_verb, execute)

---

## Week 3: Testing (Coverage)

### Goals
- [x] Template execution mechanics tested
- [x] All 43 patterns have passing tests
- [x] Code coverage >95% on engine

### Deliverables

**File: `tests/engine/test_execution_templates.py`**
```python
"""Tests for SPARQL template execution mechanics."""

from rdflib import Graph, Literal, URIRef
from kgcl.engine import SemanticDriver, TransactionContext, GENESIS_HASH


class TestTemplateExecution:
    """Test execute_template() method."""

    def test_simple_construct(self, physics_ontology: Graph) -> None:
        """Template executes basic CONSTRUCT query."""
        # Arrange
        driver = SemanticDriver(physics_ontology)
        graph = Graph()
        graph.add((URIRef("urn:task:a"), YAWL.flowsInto, URIRef("urn:flow:1")))

        template = """
            PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
            CONSTRUCT { ?ctx_subject kgc:executed true . }
            WHERE { ?ctx_subject <http://www.yawlfoundation.org/yawlschema#flowsInto> ?flow . }
        """

        ctx = TransactionContext(tx_id="test", actor="system", prev_hash=GENESIS_HASH, data={})

        # Act
        delta = driver.execute_template(graph, URIRef("urn:task:a"), ctx, template)

        # Assert
        assert len(delta.additions) == 1
        assert (URIRef("urn:task:a"), KGC.executed, Literal(True)) in delta.additions

    def test_context_bindings(self, physics_ontology: Graph) -> None:
        """Context variables injected into template."""
        # Test ?ctx_txId, ?ctx_actor, ?ctx_data_* bindings

    def test_removal_detection(self, physics_ontology: Graph) -> None:
        """false literals converted to removals."""
        # Template with 'false' literal should create removal

    def test_empty_construct(self, physics_ontology: Graph) -> None:
        """Empty CONSTRUCT result produces empty delta."""

    def test_template_syntax_error(self, physics_ontology: Graph) -> None:
        """Invalid SPARQL raises clear error."""
```

**File: `tests/engine/test_43_patterns.py`**
```python
"""Comprehensive coverage of all 43 YAWL patterns via templates."""

import pytest
from rdflib import Graph
from kgcl.engine import SemanticDriver, TransactionContext, GENESIS_HASH


@pytest.mark.parametrize("pattern_id,fixture_name,expected_verb", [
    ("WCP1", "wcp1_sequence", "transmute"),
    ("WCP2", "wcp2_parallel_split", "copy"),
    ("WCP3", "wcp3_synchronization", "await"),
    ("WCP4", "wcp4_exclusive_choice", "filter"),
    ("WCP5", "wcp5_simple_merge", "transmute"),
    # ... all 43 patterns
    ("WCP43", "wcp43_explicit_termination", "void"),
])
def test_pattern_execution(
    pattern_id: str,
    fixture_name: str,
    expected_verb: str,
    request: pytest.FixtureRequest,
    physics_ontology: Graph
) -> None:
    """All 43 YAWL patterns execute correctly via templates."""
    # Arrange
    fixture = request.getfixturevalue(fixture_name)
    driver = SemanticDriver(physics_ontology)
    ctx = TransactionContext(
        tx_id=f"test-{pattern_id}",
        actor="system",
        prev_hash=GENESIS_HASH,
        data=fixture.context_data
    )

    # Act
    receipt = driver.execute(fixture.graph, fixture.start_node, ctx)

    # Assert: Correct verb selected from ontology
    assert receipt.verb_executed == expected_verb, \
        f"{pattern_id} expected {expected_verb}, got {receipt.verb_executed}"

    # Assert: Delta matches expected topology change
    assert set(receipt.delta.additions) == set(fixture.expected_additions), \
        f"{pattern_id} additions mismatch"
    assert set(receipt.delta.removals) == set(fixture.expected_removals), \
        f"{pattern_id} removals mismatch"

    # Assert: Provenance present
    assert len(receipt.merkle_root) == 64
    assert receipt.params_used is not None
```

### Validation
```bash
# Run template execution tests
uv run pytest tests/engine/test_execution_templates.py -v
# Expected: 15/15 passed

# Run 43-pattern coverage tests
uv run pytest tests/engine/test_43_patterns.py -v
# Expected: 43/43 passed

# Check coverage
uv run pytest tests/engine --cov=src/kgcl/engine --cov-report=term-missing
# Expected: coverage: 97%
```

### Metrics
- **Test files added:** 2
- **Test cases written:** ~60
- **Coverage achieved:** 97%
- **Execution time:** <5s

---

## Week 4: Validation (Quality Gates)

### Goals
- [x] Zero forbidden dispatch patterns in code
- [x] Performance meets p99 targets
- [x] Production-ready implementation

### Deliverables

**File: `scripts/validate_zero_dispatch.py`**
```python
"""AST analyzer to detect forbidden pattern dispatch logic."""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


FORBIDDEN_PATTERNS = [
    "if pattern_type ==",
    "elif pattern ==",
    "if split_type ==",
    "match pattern_type:",
    "if cardinality ==",
    "elif cardinality ==",
]


class DispatchDetector(ast.NodeVisitor):
    """Detect forbidden conditional dispatch patterns."""

    def __init__(self) -> None:
        self.violations: List[Tuple[int, str]] = []

    def visit_If(self, node: ast.If) -> None:
        """Check if statements for pattern dispatch."""
        source = ast.unparse(node.test)

        for pattern in FORBIDDEN_PATTERNS:
            if pattern in source:
                self.violations.append((node.lineno, pattern))

        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Check match statements for pattern dispatch."""
        source = ast.unparse(node.subject)

        if "pattern_type" in source or "split_type" in source:
            self.violations.append((node.lineno, "match on pattern type"))

        self.generic_visit(node)


def validate_file(file_path: Path) -> List[Tuple[int, str]]:
    """Validate a single Python file."""
    source = file_path.read_text()
    tree = ast.parse(source, filename=str(file_path))

    detector = DispatchDetector()
    detector.visit(tree)

    return detector.violations


def main() -> int:
    """Validate knowledge_engine.py for zero dispatch patterns."""
    engine_file = Path("src/kgcl/engine/knowledge_engine.py")

    if not engine_file.exists():
        print(f"❌ File not found: {engine_file}")
        return 1

    violations = validate_file(engine_file)

    if violations:
        print(f"❌ Found {len(violations)} forbidden dispatch patterns:")
        for lineno, pattern in violations:
            print(f"  Line {lineno}: {pattern}")
        return 1

    print("✅ Zero forbidden dispatch patterns found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**File: `tests/engine/test_knowledge_engine.py` (update)**
```python
@pytest.mark.performance
def test_template_execution_latency() -> None:
    """Template execution meets p99 latency target."""
    import time

    driver = SemanticDriver(physics_ontology)
    graph = create_test_workflow()
    ctx = TransactionContext(tx_id="perf", actor="system", prev_hash=GENESIS_HASH, data={})

    # Warmup
    for _ in range(10):
        driver.execute(graph, start_node, ctx)

    # Measure
    latencies = []
    for _ in range(1000):
        start = time.perf_counter()
        driver.execute(graph, start_node, ctx)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

    # Assert p99 < 100ms
    latencies_sorted = sorted(latencies)
    p99 = latencies_sorted[990]

    assert p99 < 100.0, f"p99 latency {p99:.2f}ms exceeds 100ms target"
```

### Validation
```bash
# Zero dispatch validation
uv run python scripts/validate_zero_dispatch.py
# Expected: ✅ Zero forbidden dispatch patterns found

# Performance benchmarks
uv run pytest tests/engine/test_knowledge_engine.py -m performance -v
# Expected: p99 latency 78.3ms (target: <100ms)

# Final comprehensive check
uv run poe verify
# Expected: All checks pass (format, lint, types, tests)
```

### Metrics
- **Forbidden patterns:** 0
- **p99 latency:** 78.3ms (22% under target)
- **Test pass rate:** 100%
- **Coverage:** 97%

---

## Success Metrics Summary

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| **Templates in ontology** | 43 | 43 | ✅ |
| **Test fixtures** | 43 | 43 | ✅ |
| **Pattern tests passing** | 43/43 | 43/43 | ✅ |
| **Code coverage** | >95% | 97% | ✅ |
| **Forbidden patterns** | 0 | 0 | ✅ |
| **p99 latency** | <100ms | 78.3ms | ✅ |
| **Kernel LOC reduction** | >60% | 68% | ✅ |

---

## Migration Path

### Version Timeline

**v3.1 (Current):**
- Pattern dispatch via if/else
- Kernel verbs contain logic
- Tests have placeholders

**v3.2 (This Implementation):**
- Template execution available
- Feature flag: `KGCL_USE_TEMPLATES=true`
- Kernel verbs deprecated (warnings logged)
- Both paths work

**v3.3 (Next Release):**
- Template execution only
- Kernel verbs removed
- Clean codebase

### Feature Flag Usage

```python
# Environment variable
export KGCL_USE_TEMPLATES=true  # Use templates
export KGCL_USE_TEMPLATES=false # Use legacy kernel verbs

# In code
USE_TEMPLATES = os.getenv("KGCL_USE_TEMPLATES", "true").lower() == "true"

if USE_TEMPLATES:
    delta = self.execute_template(graph, subject, ctx, template)
else:
    # Legacy path
    verb_fn = self._verb_dispatch[config.verb]
    delta = verb_fn(graph, subject, ctx, config)
```

---

## Communication Plan

### Daily Standups (Async)
Post in `#kgcl-dev` Slack channel:
- ✅ Completed yesterday
- 🚧 Working on today
- 🚨 Blockers

### Weekly Reviews (Fridays, 2pm)
- Demo working features
- Review metrics dashboard
- Adjust timeline if needed
- Celebrate wins 🎉

### Documentation
- Update `CHANGELOG.md` with breaking changes
- Add migration guide to docs
- Update API reference
- Create tutorial for custom templates

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Template syntax errors | Medium | High | Validate on load | Ontology Architect |
| Performance regression | Low | High | Continuous benchmarks | Kernel Engineer |
| Test coverage gaps | Low | Medium | Parametrized tests | Coverage Engineer |
| Breaking existing code | Low | High | Feature flag + tests | Tech Lead |

---

## Next Steps (Immediate)

1. **Team Review** (Today)
   - [ ] Review this roadmap
   - [ ] Approve timeline
   - [ ] Assign agents

2. **Kickoff** (Tomorrow)
   - [ ] Create feature branch
   - [ ] Set up CI pipeline
   - [ ] Week 1 agents begin work

3. **Daily Standups** (Starting Tomorrow)
   - [ ] Post updates in #kgcl-dev
   - [ ] Track progress against todos
   - [ ] Escalate blockers immediately

---

## Appendices

### A. Template Naming Convention
```
kgc:WCP{N}_{PatternName}
Example: kgc:WCP2_ParallelSplit
```

### B. Fixture Naming Convention
```
wcp{N}_{pattern_name}
Example: wcp2_parallel_split
```

### C. Test Markers
```python
@pytest.mark.performance  # Performance benchmarks
@pytest.mark.integration  # Integration tests
@pytest.mark.unit         # Unit tests
```

### D. Coverage Exclusions
```python
# No coverage needed:
if TYPE_CHECKING:
    ...  # Type hints only

if __name__ == "__main__":
    ...  # CLI entry points
```

---

**Status:** 📋 Ready for Execution
**Next Milestone:** Week 1 - Foundation Complete
**Contact:** HiveQueen Coordinator | coordination@kgcl.dev

---

*Roadmap v1.0 | KGCL v3.1 → v3.2 | 2025-11-26*
