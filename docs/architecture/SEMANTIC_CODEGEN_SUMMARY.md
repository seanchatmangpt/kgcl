# Semantic Code Generator - Architecture Summary

**Status**: ✅ Architecture Design Complete
**Target**: 122 Java files → Python/React migration
**Scale**: ~18,243 lines → ~20,000+ lines (Python + TypeScript + Tests)
**Date**: 2025-11-28

---

## 📋 Deliverables Overview

This architecture package contains **3 comprehensive documents**:

| Document | Size | Lines | Purpose |
|----------|------|-------|---------|
| **SEMANTIC_CODEGEN_ARCHITECTURE.md** | 38KB | 1,181 | Complete system architecture specification |
| **SEMANTIC_CODEGEN_C4_DIAGRAMS.md** | 48KB | 758 | C4 model diagrams (Context, Container, Component, Code) |
| **SEMANTIC_CODEGEN_TEMPLATE_CATALOG.md** | 30KB | 1,191 | 13 Jinja2 templates with examples |
| **Total** | **116KB** | **3,130** | Production-ready architecture |

---

## 🎯 Executive Summary

**Problem**: Convert 122 Java Vaadin UI files to Python FastAPI backend + React TypeScript frontend while maintaining:
- 100% type coverage
- 80%+ test coverage
- Zero quality gate failures
- Production-ready code

**Solution**: Semantic code generator with 5-layer architecture:
1. **Parser Layer**: Extract semantic metadata from Java AST
2. **Mapping Layer**: Translate types and patterns (Java → Python/TypeScript)
3. **Template Layer**: Generate code from Jinja2 templates
4. **Validation Layer**: Enforce quality gates (mypy, ruff, pytest, tsc, eslint)
5. **Orchestration Layer**: Batch processing with rollback safety

**Key Innovation**: NOT a transpiler - semantic migration that extracts business logic and re-implements using idiomatic Python/React patterns.

---

## 📐 Architecture Highlights

### System Architecture (5 Layers)

```
┌─────────────────────────────────────────────┐
│ ORCHESTRATION: Batch + Rollback            │
├─────────────────────────────────────────────┤
│ PARSER: Java AST → Semantic Metadata       │
├─────────────────────────────────────────────┤
│ MAPPER: Java → Python/TypeScript           │
├─────────────────────────────────────────────┤
│ TEMPLATE: Jinja2 Code Generation           │
├─────────────────────────────────────────────┤
│ VALIDATION: Quality Gates (100% types)     │
└─────────────────────────────────────────────┘
```

### Data Flow

```
Java Source → AST Parse → Semantic Analysis → Pattern Detection
     ↓
API/UI Split → Type Mapping → Template Rendering → Validation
     ↓
Python Backend + React Frontend + Tests (PASS ✅ or ROLLBACK ❌)
```

### Batch Processing Strategy

**Package-by-Package with Dependency Resolution**:

```
Tier 1 (14 files)  → util, announce, layout
Tier 2 (12 files)  → listener, component
Tier 3 (52 files)  → dynform, dialog, service
Tier 4 (44 files)  → menu, view, dialog subpackages
```

**Parallel execution within packages** (4 files concurrently)
**Sequential across tiers** (respect dependencies)

---

## 🛠️ Technology Stack

### Parser Layer
- **javalang**: Pure Python Java AST parser (no JDK dependency)
- **Pattern Detection**: 14 package categories (View, Service, Model, Listener, etc.)
- **Output**: Frozen dataclasses (JavaClass, JavaMethod, JavaField)

### Mapping Layer
- **Type Mapper**: Java → Python/TypeScript mappings
- **Pattern Translator**: Vaadin → React patterns
- **API/UI Splitter**: Backend logic vs. Frontend rendering

### Template Layer
- **Jinja2**: Template rendering engine
- **13 Core Templates**:
  - Python: Model, Router, Service, Client, Test (7 templates)
  - TypeScript: Component, Hook, Types, API Client, Test (6 templates)

### Validation Layer
- **Python**: mypy strict, ruff (400+ rules), pytest (80%+ coverage)
- **TypeScript**: tsc strict, eslint (Airbnb), vitest (80%+ coverage)
- **Lie Detection**: No TODO/FIXME/stubs allowed

### Orchestration Layer
- **asyncio**: Parallel file processing
- **Dependency Graph**: Topological sort for package order
- **Rollback Manager**: Automatic rollback on quality gate failure

---

## 📊 C4 Architecture Diagrams

### Level 1: System Context

```
Developer → Codegen System → Python/React Output
              ↓
         Quality Gates (mypy, ruff, pytest)
              ↓
         CI/CD Validation
```

### Level 2: Container Diagram

5 Containers:
1. **Orchestrator** (Python + asyncio)
2. **Parser** (Python + javalang)
3. **Mapper** (Python)
4. **Template** (Jinja2)
5. **Validation** (Python + Node.js)

### Level 3: Component Diagrams

**Parser Container** (5 components):
- JavaFileReader
- ASTParser
- SemanticAnalyzer
- PatternDetector
- MetadataExtractor

**Template Container** (3 components):
- PythonGenerator
- TypeScriptGenerator
- TestGenerator

**Validation Container** (5 components):
- TypeChecker (mypy/tsc)
- Linter (ruff/eslint)
- TestRunner (pytest/vitest)
- LieDetector
- QualityGateAggregator

### Level 4: Code Diagram

**TypeMapper Class**:
- `map_java_to_python(str) -> str`
- `map_java_to_typescript(str) -> str`
- `handle_generics(str) -> GenericTypeMapping`
- Supports: primitives, generics, arrays, custom classes

---

## 📝 Template Catalog

### Python Templates (7)

| Template | Input | Output | Example |
|----------|-------|--------|---------|
| `pydantic_model.py.j2` | Java class | Pydantic model | `Announcement.java` → `announcement.py` |
| `router.py.j2` | Java view | FastAPI router | `CasesView.java` → `cases.py` |
| `service_class.py.j2` | Java service | Service class | `CaseService.java` → `case_service.py` |
| `client_class.py.j2` | Java client | API client | `YAWLClient.java` → `yawl_client.py` |
| `utility_module.py.j2` | Java util | Utils module | `UiUtil.java` → `ui_helpers.py` |
| `test_api.py.j2` | API endpoint | Pytest test | `cases.py` → `test_cases.py` |
| `test_service.py.j2` | Service class | Pytest test | `case_service.py` → `test_case_service.py` |

### TypeScript Templates (6)

| Template | Input | Output | Example |
|----------|-------|--------|---------|
| `component.tsx.j2` | Vaadin component | React component | `Announcement.java` → `Announcement.tsx` |
| `modal_component.tsx.j2` | Vaadin dialog | Modal component | `ErrorMsg.java` → `ErrorModal.tsx` |
| `use_api.ts.j2` | Service call | React hook | `CaseService` → `useCases.ts` |
| `interface.ts.j2` | Java class | TypeScript interface | `CaseModel` → `case.ts` |
| `api_client.ts.j2` | Java client | Axios client | `YAWLClient` → `yawlClient.ts` |
| `component.test.tsx.j2` | React component | Vitest test | `Announcement.tsx` → `Announcement.test.tsx` |

### Template Features

✅ **100% Type Coverage**: Full typing in Python and TypeScript
✅ **NumPy Docstrings**: Complete documentation
✅ **Quality Gates Built-In**: Templates generate passing code
✅ **Chicago School TDD**: Tests verify behavior, not implementation
✅ **Frozen Dataclasses**: Immutable value objects where appropriate

---

## 🎯 Quality Assurance

### MANDATORY Quality Gates (Zero Tolerance)

**Python**:
```bash
poe format       # Ruff format (must be clean)
poe lint         # Ruff check (400+ rules, all pass)
poe type-check   # Mypy strict (100% coverage)
poe test         # Pytest (80%+ coverage, all pass)
poe detect-lies  # No TODO/FIXME/stubs
```

**TypeScript**:
```bash
npm run type-check  # tsc strict mode
npm run lint        # eslint (Airbnb rules)
npm run test        # vitest (80%+ coverage)
```

### Rollback Strategy

**Triggers**:
- Type check failure
- Lint failure
- Test failure (<80% coverage or failing tests)
- Lie detection (TODO/FIXME/stubs)

**Process**:
1. Delete all generated files
2. Restore from backup (if exists)
3. Log failure details
4. Return error report to orchestrator
5. DO NOT commit partial work

**Backup Mechanism**:
- Snapshot before generation
- Store in `/tmp/codegen_backup_{package}_{timestamp}/`
- Restore on failure, delete on success
- Keep last 3 backups for debugging

---

## 📈 Success Metrics

### Quantitative Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Files generated | 122/122 (100%) | File count |
| Type coverage | 100% | mypy + tsc reports |
| Test coverage | ≥80% | pytest-cov + vitest |
| Quality gate pass rate | 100% | CI/CD pipeline |
| Lines of code | ~20,000 LOC | Python + TypeScript + Tests |
| Generation time | <2 hours | Total batch processing |
| Rollback rate | <5% | Failed packages / total |

### Qualitative Targets

✅ **Code readability**: Human-reviewable, PEP 8 / Airbnb style
✅ **Maintainability**: Modular, DRY, SOLID principles
✅ **Documentation**: NumPy docstrings, JSDoc comments
✅ **Semantic correctness**: Preserves business logic
✅ **Developer experience**: Easy to extend and debug

---

## 🚀 Implementation Phases

### Phase 1: Infrastructure (Week 1)

**Deliverables**:
- Parser layer (javalang + semantic analyzer)
- Type mapper (Java → Python/TypeScript)
- Template infrastructure (Jinja2)
- Validation framework (quality gates)
- Rollback mechanism

**Tests**:
- Parse all 122 files ✓
- Detect all patterns ✓
- Map 100 sample types ✓
- Render 5 templates ✓
- Execute quality gates ✓

### Phase 2-5: Package Generation (Weeks 2-6)

**Tier 1** (Week 2): 14 files (util, announce, layout)
**Tier 2** (Week 3): 12 files (listener, component)
**Tier 3** (Weeks 4-5): 52 files (dynform, dialog, service)
**Tier 4** (Week 6): 44 files (menu, view, subpackages)

**Process per tier**:
1. Generate Python models/services
2. Generate React components
3. Generate tests (80%+ coverage)
4. Run quality gates
5. Rollback on failure, iterate
6. Commit on success

### Phase 6: Integration & E2E (Week 7)

**Deliverables**:
- Full integration tests (backend ↔ frontend)
- E2E tests (Playwright)
- Performance benchmarks (<100ms p99)
- Documentation (API docs, Storybook)
- Deployment scripts

---

## 📋 Architecture Decision Records (ADRs)

### ADR-001: Use Jinja2 Templates (Not AST Generation)

**Rationale**: Human-readable, easy to modify, flexible
**Trade-off**: Less type safety than AST (mitigated by validation layer)

### ADR-002: Package-by-Package Processing (Not All-At-Once)

**Rationale**: Smaller rollback scope, incremental validation
**Trade-off**: Slightly longer total time (sequential packages)

### ADR-003: Semantic Migration (Not Line-by-Line Translation)

**Rationale**: Idiomatic Python/React, better quality
**Trade-off**: More complex translation logic

### ADR-004: 100% Type Coverage (No Gradual Typing)

**Rationale**: KGCL Lean Six Sigma standard, zero defects
**Trade-off**: More upfront effort in type mapping

### ADR-005: No Test Skipping (Even for Generated Code)

**Rationale**: KGCL policy - generated code must be production-ready
**Trade-off**: Requires comprehensive test templates

---

## 🔍 Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Java parsing failures | Medium | High | Battle-tested javalang, fallback annotations |
| Type mapping errors | High | High | Comprehensive tests, manual review |
| Template bugs | High | Medium | Template unit tests, dry-run |
| Quality gate failures | High | High | Incremental validation, rollback |
| Missing dependencies | Medium | Medium | Dependency graph, topological sort |
| Coverage <80% | Medium | High | Test template improvements |

### Process Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | Medium | High | Strict focus on 122 files |
| Timeline delays | Medium | High | Weekly milestones, early warnings |
| Quality regression | Low | Critical | MANDATORY quality gates |
| Rollback data loss | Low | Critical | Backup mechanism, version control |

---

## 🎓 Key Architectural Principles

1. **Separation of Concerns**: Parse → Map → Template → Validate
2. **Fail-Safe Design**: Quality gates enforce standards
3. **Rollback Safety**: Automatic recovery on failures
4. **Incremental Processing**: Package-by-package with dependencies
5. **Parallel Execution**: Within-package parallel processing
6. **Type Safety First**: 100% coverage in Python and TypeScript
7. **Test-Driven Generation**: Tests generated alongside code
8. **Semantic Preservation**: Business logic preserved, not syntax
9. **Zero Tolerance Quality**: No compromises on standards
10. **Production Ready**: All code ready for deployment

---

## 📚 Documentation Index

1. **SEMANTIC_CODEGEN_ARCHITECTURE.md** (1,181 lines)
   - System architecture (5 layers)
   - Component specifications
   - Implementation details
   - Quality assurance workflow
   - Execution plan (7 phases)
   - Risk mitigation
   - Success metrics
   - ADRs (5 decisions)

2. **SEMANTIC_CODEGEN_C4_DIAGRAMS.md** (758 lines)
   - C4 Level 1: System Context
   - C4 Level 2: Container Diagram
   - C4 Level 3: Component Diagrams (Parser, Template, Validation)
   - C4 Level 4: Code Diagram (Type Mapping)
   - Sequence Diagrams (Generation, Rollback)
   - Deployment Diagram

3. **SEMANTIC_CODEGEN_TEMPLATE_CATALOG.md** (1,191 lines)
   - Template directory structure
   - 13 core templates with examples
   - Template metadata schema
   - Template testing strategy
   - Success criteria

---

## ✅ Verification Checklist

**Architecture Documents**:
- [x] Complete system architecture defined
- [x] All 5 layers specified
- [x] Component interfaces documented
- [x] Data flow diagrams created
- [x] Quality gates defined
- [x] Rollback strategy documented

**C4 Diagrams**:
- [x] System Context diagram
- [x] Container diagram
- [x] Component diagrams (3 containers)
- [x] Code diagram (Type Mapping)
- [x] Sequence diagrams (2)
- [x] Deployment diagram

**Template Catalog**:
- [x] 13 templates cataloged
- [x] Template examples provided
- [x] Metadata schema defined
- [x] Testing strategy documented

**Implementation Readiness**:
- [x] Technology stack chosen
- [x] File organization defined
- [x] Batch processing strategy
- [x] Dependencies resolved
- [x] Risks identified and mitigated
- [x] Success metrics defined

---

## 🚦 Next Steps

### Immediate (Week 1)
1. Review architecture documents with stakeholders
2. Approve technology stack
3. Set up development environment
4. Begin Parser layer implementation

### Short-term (Weeks 2-3)
1. Complete infrastructure (all 5 layers)
2. Validate with Tier 1 packages
3. Iterate on templates based on results
4. Establish quality gate baselines

### Long-term (Weeks 4-7)
1. Generate all 122 files
2. Achieve 100% type coverage
3. Achieve 80%+ test coverage
4. Complete integration testing
5. Deploy to production

---

## 📞 Support & References

**Documentation**:
- Full architecture: `docs/architecture/SEMANTIC_CODEGEN_ARCHITECTURE.md`
- C4 diagrams: `docs/architecture/SEMANTIC_CODEGEN_C4_DIAGRAMS.md`
- Template catalog: `docs/architecture/SEMANTIC_CODEGEN_TEMPLATE_CATALOG.md`

**KGCL Standards**:
- Project configuration: `/Users/sac/dev/kgcl/CLAUDE.md`
- Quality gates: `poe verify` (format, lint, type-check, test, detect-lies)

**Java Source**:
- Location: `vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui/`
- Files: 122 Java files (~18,243 LOC)
- Packages: 14 packages

**Output Locations**:
- Python backend: `src/kgcl/yawl_ui/`
- React frontend: `frontend/src/`
- Tests: `tests/yawl_ui/` + `frontend/src/**/*.test.tsx`

---

**Status**: ✅ Architecture Complete - Ready for Implementation

**Total Documentation**: 3,130 lines, 116KB

**Next Action**: Begin Phase 1 Implementation (Parser Layer)
