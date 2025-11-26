# COMPLETENESS Law Implementation Roadmap

**Goal**: Transform KGCL from "claimed RDF-only" to **proven RDF-only** execution through template-based dispatch.

---

## Quick Start (5 minutes)

```bash
# 1. Validate proposal against current ontology
cd /Users/sac/dev/kgcl
uv run pyshacl --shapes docs/COMPLETENESS_LAW_PROPOSAL.ttl \
               --data ontology/kgc_physics.ttl \
               --ont-graph ontology/invariants.shacl.ttl

# Expected: VIOLATIONS (missing templates) ✓ This proves COMPLETENESS Law works

# 2. View analysis
cat docs/ONTOLOGY_EVOLUTION_ANALYSIS.md

# 3. Review proposed shapes
cat docs/COMPLETENESS_LAW_PROPOSAL.ttl
```

---

## Implementation Phases

### Phase 1: POC - Basic Patterns (4 hours)

**Goal**: Prove RDF-only execution for WCP 1-5 (basic control flow)

#### 1.1 Create Template Library (1.5 hours)

Create `/Users/sac/dev/kgcl/ontology/templates/basic_patterns.ttl`:

```turtle
@prefix kgc: <http://bitflow.ai/ontology/kgc/v3#> .

# Template: Threshold="all" (AND-join)
kgc:Template_Threshold_All a kgc:TemplateDefinition ;
    kgc:definesThresholdValue "all" ;
    kgc:thresholdTemplate """
        ASK {
            FILTER NOT EXISTS {
                ?token kgc:atTask ?predecessor .
                ?predecessor yawl:flowsInto/yawl:nextElementRef $this .
                FILTER(?token kgc:status != "Completed")
            }
        }
    """ .

# Template: Cardinality="topology" (AND-split)
kgc:Template_Cardinality_Topology a kgc:TemplateDefinition ;
    kgc:definesCardinalityValue "topology" ;
    kgc:cardinalityTemplate """
        SELECT (COUNT(?successor) as ?count) WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?successor .
        }
    """ .

# Template: SelectionMode="exactlyOne" (XOR-split)
kgc:Template_Selection_ExactlyOne a kgc:TemplateDefinition ;
    kgc:definesSelectionMode "exactlyOne" ;
    kgc:selectionTemplate """
        CONSTRUCT {
            $this kgc:selectedFlow ?flow .
        } WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:hasPredicate ?pred .
            ?pred yawl:query ?query ;
                  yawl:ordering ?order .
            FILTER(EXISTS { ASK { ?query } })
        }
        ORDER BY ?order
        LIMIT 1
    """ .

# Add templates for: "1" threshold, "waitAll" completion, "self" cancellation, etc.
```

#### 1.2 Update Pattern Mappings (1 hour)

Update `kgc_physics.ttl` to link templates:

```turtle
# WCP-1: Sequence (add execution template)
kgc:WCP1_Sequence
    kgc:executionTemplate """
        DELETE WHERE { ?token kgc:atTask $this } ;
        INSERT DATA {
            _:newToken a kgc:Token ;
                       kgc:atTask ?successor ;
                       kgc:createdAt ?now .
        } WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?successor .
        }
    """ .

# WCP-2: Parallel Split (link cardinality template)
kgc:WCP2_ParallelSplit
    kgc:cardinalityTemplate """
        SELECT (COUNT(?successor) as ?count) WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?successor .
        }
    """ ;
    kgc:executionTemplate """
        DELETE WHERE { ?token kgc:atTask $this } ;
        INSERT DATA {
            ?successor kgc:hasToken _:token .
            _:token a kgc:Token ;
                    kgc:atTask ?successor ;
                    kgc:instanceId ?id ;
                    kgc:createdAt ?now .
        } WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?successor .
            BIND(UUID() AS ?id)
        }
    """ .

# WCP-3: Synchronization (link threshold template)
kgc:WCP3_Synchronization
    kgc:thresholdTemplate """
        ASK {
            FILTER NOT EXISTS {
                ?token kgc:atTask ?predecessor .
                ?predecessor yawl:flowsInto/yawl:nextElementRef $this .
            }
        }
    """ ;
    kgc:executionTemplate """
        INSERT DATA {
            $this kgc:status "Active" .
            _:token a kgc:Token ;
                    kgc:atTask $this ;
                    kgc:createdAt ?now .
        }
    """ .

# WCP-4: Exclusive Choice (link selection template)
kgc:WCP4_ExclusiveChoice
    kgc:selectionTemplate """
        CONSTRUCT { $this kgc:selectedFlow ?flow }
        WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:hasPredicate ?pred .
            ?pred yawl:query ?query ; yawl:ordering ?order .
            FILTER(EXISTS { ASK { ?query } })
        }
        ORDER BY ?order LIMIT 1
    """ ;
    kgc:executionTemplate """
        DELETE WHERE { ?token kgc:atTask $this } ;
        INSERT DATA {
            _:token a kgc:Token ;
                    kgc:atTask ?successor ;
                    kgc:createdAt ?now .
        } WHERE {
            $this kgc:selectedFlow ?flow .
            ?flow yawl:nextElementRef ?successor .
        }
    """ .

# WCP-5: Simple Merge (just transmute)
kgc:WCP5_SimpleMerge
    kgc:executionTemplate """
        DELETE WHERE { ?token kgc:atTask $this } ;
        INSERT DATA {
            _:token a kgc:Token ;
                    kgc:atTask ?successor ;
                    kgc:createdAt ?now .
        } WHERE {
            $this yawl:flowsInto ?flow .
            ?flow yawl:nextElementRef ?successor .
        }
    """ .
```

#### 1.3 Add Verb Dispatch Queries (30 minutes)

Update `kgc_physics.ttl` verbs with `dispatchQuery`:

```turtle
kgc:Transmute
    kgc:dispatchQuery """
        DELETE WHERE { ?token kgc:atTask $source } ;
        INSERT DATA {
            _:token a kgc:Token ;
                    kgc:atTask $target ;
                    kgc:createdAt ?now .
        }
    """ .

kgc:Copy
    kgc:dispatchQuery """
        DELETE WHERE { ?token kgc:atTask $source } ;
        INSERT {
            ?target kgc:hasToken _:token .
            _:token a kgc:Token ;
                    kgc:atTask ?target ;
                    kgc:instanceId ?id ;
                    kgc:createdAt ?now .
        } WHERE {
            $source yawl:flowsInto/yawl:nextElementRef ?target .
            BIND(UUID() AS ?id)
        }
    """ .

kgc:Await
    kgc:dispatchQuery """
        INSERT DATA {
            $this kgc:status "Waiting" .
        } WHERE {
            # Execute threshold template (ASK query)
            # If true, fire
        }
    """ .

kgc:Filter
    kgc:dispatchQuery """
        DELETE WHERE { ?token kgc:atTask $source } ;
        INSERT {
            _:token a kgc:Token ;
                    kgc:atTask ?selected ;
                    kgc:createdAt ?now .
        } WHERE {
            # Execute selection template (CONSTRUCT query)
            # Use constructed flows
        }
    """ .

kgc:Void
    kgc:dispatchQuery """
        DELETE WHERE {
            ?target kgc:hasToken ?token .
            ?token ?p ?o .
        } WHERE {
            # Execute cancellation template
            # Scope determines ?target
        }
    """ .
```

#### 1.4 Integration Testing (1 hour)

Create test workflow:

```turtle
# tests/fixtures/workflows/poc_basic_patterns.ttl
@prefix wf: <http://example.org/workflow/poc#> .

wf:TestWorkflow a yawl:WorkflowSpecification ;
    yawl:hasCondition wf:start, wf:end ;
    yawl:hasTask wf:A, wf:B, wf:C, wf:D, wf:E .

# WCP-1: Sequence (A → B)
wf:A yawl:flowsInto [ yawl:nextElementRef wf:B ] .

# WCP-2: Parallel Split (B → C AND D)
wf:B yawl:hasSplit yawl:ControlTypeAnd ;
     yawl:flowsInto [ yawl:nextElementRef wf:C ], [ yawl:nextElementRef wf:D ] .

# WCP-3: Synchronization (C AND D → E)
wf:E yawl:hasJoin yawl:ControlTypeAnd .
wf:C yawl:flowsInto [ yawl:nextElementRef wf:E ] .
wf:D yawl:flowsInto [ yawl:nextElementRef wf:E ] .
```

Python test (Chicago School TDD):

```python
# tests/test_rdf_dispatch_poc.py
from rdflib import Graph
from kgcl.semantic_driver import SemanticDriver

def test_wcp1_sequence_rdf_only_dispatch():
    """Verify WCP-1 Sequence executes via SPARQL template only."""
    # Arrange
    g = Graph()
    g.parse("tests/fixtures/workflows/poc_basic_patterns.ttl")
    g.parse("ontology/kgc_physics.ttl")
    g.parse("ontology/templates/basic_patterns.ttl")

    driver = SemanticDriver(g)

    # Act: Place token at task A
    driver.place_token("wf:A")
    driver.execute_step()  # Should use kgc:WCP1_Sequence executionTemplate

    # Assert: Token moved to B via SPARQL (no Python if/else)
    assert driver.has_token("wf:B")
    assert not driver.has_token("wf:A")

    # Verify execution receipt
    receipt = driver.get_last_receipt()
    assert receipt.verb_executed == "kgc:Transmute"
    assert "executionTemplate" in receipt.sparql_used
    assert "if threshold ==" not in receipt.code_executed  # NO PYTHON!

def test_wcp2_parallel_split_cardinality_template():
    """Verify WCP-2 AND-split uses cardinalityTemplate to count successors."""
    # Arrange
    g = Graph()
    g.parse("tests/fixtures/workflows/poc_basic_patterns.ttl")
    driver = SemanticDriver(g)

    # Act: Place token at B (AND-split)
    driver.place_token("wf:B")
    driver.execute_step()

    # Assert: Cardinality determined via SPARQL COUNT, not Python len()
    assert driver.has_token("wf:C")
    assert driver.has_token("wf:D")
    receipt = driver.get_last_receipt()
    assert "cardinalityTemplate" in receipt.sparql_used
    assert "SELECT (COUNT(?successor) as ?count)" in receipt.sparql_query

def test_wcp3_synchronization_threshold_template():
    """Verify WCP-3 AND-join uses thresholdTemplate ASK query."""
    # Arrange
    g = Graph()
    g.parse("tests/fixtures/workflows/poc_basic_patterns.ttl")
    driver = SemanticDriver(g)

    # Act: Place tokens at C and D
    driver.place_token("wf:C")
    driver.place_token("wf:D")
    driver.execute_step()

    # Assert: Threshold evaluated via SPARQL ASK, not Python if
    assert driver.has_token("wf:E")
    receipt = driver.get_last_receipt()
    assert "thresholdTemplate" in receipt.sparql_used
    assert "ASK { FILTER NOT EXISTS" in receipt.sparql_query
    assert "if threshold == 'all'" not in receipt.code_executed
```

Run tests:

```bash
uv run pytest tests/test_rdf_dispatch_poc.py -v

# Expected:
# test_wcp1_sequence_rdf_only_dispatch PASSED
# test_wcp2_parallel_split_cardinality_template PASSED
# test_wcp3_synchronization_threshold_template PASSED
```

#### 1.5 SHACL Validation (30 minutes)

```bash
# Merge COMPLETENESS Law into invariants.shacl.ttl
cat docs/COMPLETENESS_LAW_PROPOSAL.ttl >> ontology/invariants.shacl.ttl

# Validate POC templates
uv run pyshacl --shapes ontology/invariants.shacl.ttl \
               --data ontology/kgc_physics.ttl \
               --data ontology/templates/basic_patterns.ttl

# Expected: Conforms = True (all 5 patterns have templates)
```

---

### Phase 2: Advanced Patterns (8 hours)

**Goal**: Extend to WCP 6-43 (all patterns)

#### 2.1 Template Categories

Create template files for each category:

1. **Advanced Branching** (`templates/branching.ttl`):
   - OR-split/join templates
   - Discriminator templates
   - Multi-merge templates

2. **Multiple Instance** (`templates/multi_instance.ttl`):
   - Static/dynamic MI templates
   - Partial join templates
   - Cancelling join templates

3. **Cancellation** (`templates/cancellation.ttl`):
   - Task/case/region cancellation
   - Timeout templates
   - Exception handling templates

4. **Iteration** (`templates/iteration.ttl`):
   - While loop templates
   - Repeat-until templates
   - Arbitrary cycle templates

5. **State-Based** (`templates/state.ttl`):
   - Deferred choice templates
   - Milestone templates
   - Interleaved parallel templates

#### 2.2 Template Authoring Pattern

For each parameter value:

1. **Define template** in category file
2. **Link to pattern mapping** in `kgc_physics.ttl`
3. **Create test** verifying RDF-only execution
4. **Validate with SHACL**

Example workflow:

```bash
# 1. Create template
cat >> ontology/templates/branching.ttl <<EOF
kgc:Template_Threshold_Active a kgc:TemplateDefinition ;
    kgc:definesThresholdValue "active" ;
    kgc:thresholdTemplate """
        ASK {
            FILTER NOT EXISTS {
                ?token kgc:atTask ?predecessor ;
                       kgc:status "Active" .
                ?predecessor yawl:flowsInto/yawl:nextElementRef $this .
            }
        }
    """ .
EOF

# 2. Link to mapping
cat >> ontology/kgc_physics.ttl <<EOF
kgc:WCP7_StructuredSyncMerge
    kgc:thresholdTemplate """
        ASK {
            FILTER NOT EXISTS {
                ?token kgc:atTask ?predecessor ;
                       kgc:status "Active" .
                ?predecessor yawl:flowsInto/yawl:nextElementRef $this .
            }
        }
    """ .
EOF

# 3. Create test
cat >> tests/test_wcp7_or_join.py <<EOF
def test_wcp7_or_join_active_threshold():
    driver.place_token("taskB")  # One branch active
    driver.void_token("taskC")   # Other branch voided
    driver.execute_step()
    assert driver.has_token("taskD")  # Fires when active complete
    receipt = driver.get_last_receipt()
    assert "threshold='active'" in receipt.parameters
    assert "thresholdTemplate" in receipt.sparql_used
EOF

# 4. Validate
uv run pyshacl --shapes ontology/invariants.shacl.ttl \
               --data ontology/kgc_physics.ttl \
               --data ontology/templates/branching.ttl
```

---

### Phase 3: Migration & Cleanup (2 hours)

#### 3.1 Delete Broken YAWL Engine

Once RDF-only execution works:

```bash
# Remove Python if/else code
rm -rf src/kgcl/yawl_engine/

# Update documentation
echo "YAWL engine migrated to RDF-only execution. See ontology/templates/" \
    >> docs/YAWL_IMPLEMENTATION_FAILURE_REPORT.md

# Git commit
git add -A
git commit -m "feat: Migrate to RDF-only dispatch with COMPLETENESS Law

- Add LAW 4 (COMPLETENESS) to invariants.shacl.ttl
- Create template library for all 43 YAWL patterns
- Delete broken Python if/else YAWL engine
- Achieve true RDF-only execution via SPARQL templates

Closes #XXX"
```

#### 3.2 Performance Benchmarking

Verify p99 <100ms target:

```python
# tests/test_performance.py
import pytest
from kgcl.semantic_driver import SemanticDriver

@pytest.mark.benchmark
def test_rdf_dispatch_performance(benchmark):
    """Verify SPARQL template execution meets p99 <100ms target."""
    g = Graph()
    g.parse("tests/fixtures/workflows/complex_workflow.ttl")
    driver = SemanticDriver(g)

    def execute_pattern():
        driver.place_token("task1")
        driver.execute_step()
        driver.reset()

    result = benchmark(execute_pattern)

    # Assert p99 latency
    assert result.stats.max < 0.100, f"p99 latency {result.stats.max}s exceeds 100ms"
```

Run benchmarks:

```bash
uv run pytest tests/test_performance.py --benchmark-only

# Expected:
# Name                                   Min     Max     Mean    StdDev
# test_rdf_dispatch_performance         45ms    95ms    62ms    12ms
```

#### 3.3 Documentation Updates

1. **Update README.md**:
   ```markdown
   ## RDF-Only Execution

   KGCL workflows execute via pure SPARQL dispatch. Every parameter value
   has a corresponding SPARQL template, enforced by SHACL COMPLETENESS Law.

   **Zero Python if/else statements in execution path.**

   See: `docs/ONTOLOGY_EVOLUTION_ANALYSIS.md`
   ```

2. **Update BUILD_SYSTEM_SUMMARY.md**:
   ```markdown
   ### SHACL Validation (MANDATORY)

   Four fundamental laws enforced at compile time:
   1. TYPING: Every node has rdf:type
   2. HERMETICITY: Max 64 ops/batch, known predicates only
   3. CHRONOLOGY: Time flows forward (no paradoxes)
   4. **COMPLETENESS: Every parameter has RDF execution template** ⬅ NEW

   Cannot ship without SHACL conformance.
   ```

3. **Create migration guide**:
   ```markdown
   # Template Authoring Guide

   ## Adding New Patterns

   1. Define parameter values in `kgc_physics.ttl`
   2. Create SPARQL templates in `ontology/templates/`
   3. Link templates to pattern mappings
   4. Validate with SHACL
   5. Test with RDF-only execution

   ## Template Types

   - **Threshold**: SPARQL ASK (returns boolean)
   - **Cardinality**: SPARQL SELECT COUNT (returns integer)
   - **Selection**: SPARQL CONSTRUCT (returns flows)
   - **Completion**: SPARQL ASK (returns boolean)
   - **Cancellation**: SPARQL DELETE WHERE (mutates graph)
   - **Execution**: SPARQL INSERT/DELETE (mutates graph)

   See: `ontology/templates/basic_patterns.ttl` for examples.
   ```

---

## Success Metrics

### ✅ Phase 1 Complete When:
- [ ] WCP 1-5 have complete SPARQL templates
- [ ] All templates validate with SHACL COMPLETENESS Law
- [ ] Tests pass with RDF-only execution (no Python if/else)
- [ ] Performance within bounds (p99 <100ms)

### ✅ Phase 2 Complete When:
- [ ] All 43 patterns have complete templates
- [ ] Template library organized by category
- [ ] 100% SHACL validation coverage
- [ ] Comprehensive test suite (80%+ coverage)

### ✅ Phase 3 Complete When:
- [ ] Broken YAWL engine code deleted
- [ ] Documentation updated
- [ ] Performance benchmarks passing
- [ ] Migration guide published

---

## Timeline Estimate

| Phase | Duration | Effort |
|-------|----------|--------|
| Phase 1: POC (WCP 1-5) | 4 hours | High (new paradigm) |
| Phase 2: All patterns (WCP 6-43) | 8 hours | Medium (repetitive) |
| Phase 3: Migration & cleanup | 2 hours | Low (deletion mostly) |
| **Total** | **14 hours** | **~2 working days** |

---

## Next Immediate Action

```bash
# 1. Review this roadmap
cat docs/COMPLETENESS_LAW_ROADMAP.md

# 2. Start Phase 1.1 (create basic template library)
mkdir -p ontology/templates
touch ontology/templates/basic_patterns.ttl

# 3. Copy template examples from COMPLETENESS_LAW_PROPOSAL.ttl
# 4. Run validation
# 5. Iterate until SHACL passes

# Then proceed to Phase 1.2...
```

---

## Questions for Review

1. **Is 2-day timeline acceptable?** (Can compress to 1 day if focused)
2. **Should we keep Python executor as fallback?** (Recommendation: NO, enforce RDF-only)
3. **Performance targets realistic?** (100ms p99 may need caching/optimization)
4. **Template authoring burden acceptable?** (43+ templates is significant work)
5. **SHACL validation in CI?** (Recommendation: YES, block merges on failures)

---

**Deliverables Ready**:
- ✅ `docs/COMPLETENESS_LAW_PROPOSAL.ttl` (520 lines of SHACL shapes)
- ✅ `docs/ONTOLOGY_EVOLUTION_ANALYSIS.md` (comprehensive analysis)
- ✅ `docs/COMPLETENESS_LAW_ROADMAP.md` (this implementation plan)

**Status**: Ready for Phase 1 implementation
**Agent**: Ontology-Evolution-Agent-3
**Awaiting**: Approval to proceed with POC
