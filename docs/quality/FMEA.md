# FMEA - Python Anti-Patterns

**Failure Mode and Effects Analysis** for Python code quality in KGCL research library.

## FMEA Methodology

**RPN (Risk Priority Number)** = Severity × Occurrence × Detection

- **Severity (1-10)**: Impact of defect (1 = negligible, 10 = catastrophic)
- **Occurrence (1-10)**: Likelihood of defect (1 = rare, 10 = certain)
- **Detection (1-10)**: Difficulty detecting before production (1 = always caught, 10 = never caught)

**Target**: RPN < 100 for all defect types after mitigation

## Defect Catalog

### 1. Assert Without Message (Crashes)

**Before Mitigation:**
- **Severity**: 9 (crashes process, no error context)
- **Occurrence**: 5 (common in Python code)
- **Detection**: 4 (only caught in execution)
- **RPN**: 180

**After Mitigation (Pre-Commit Hook):**
- **Occurrence**: 1 (blocked by pre-commit)
- **RPN**: 36 (80% reduction)

**Mitigation**: Pre-commit hook blocks `assert` without message in `src/`

---

### 2. Bare Indexing (IndexError)

**Before Mitigation:**
- **Severity**: 7 (crashes on empty collections)
- **Occurrence**: 6 (very common)
- **Detection**: 5 (depends on test coverage)
- **RPN**: 210

**After Mitigation:**
- **Occurrence**: 2 (blocked by pre-commit)
- **RPN**: 70 (67% reduction)

**Mitigation**: Pre-commit hook detects `x[0]` pattern, requires bounds check

---

### 3. Dict Access Without .get()

**Before Mitigation:**
- **Severity**: 7 (KeyError crashes)
- **Occurrence**: 5 (common)
- **Detection**: 5 (only caught with specific keys)
- **RPN**: 175

**After Mitigation:**
- **Occurrence**: 2 (blocked by pre-commit)
- **RPN**: 70 (60% reduction)

**Mitigation**: Pre-commit hook requires `.get()` for dict access

---

### 4. Cast Without Justification

**Before Mitigation:**
- **Severity**: 6 (type lie, causes downstream errors)
- **Occurrence**: 4 (moderate)
- **Detection**: 7 (mypy doesn't catch runtime type mismatch)
- **RPN**: 168

**After Mitigation:**
- **Detection**: 3 (manual review catches unjustified casts)
- **RPN**: 72 (57% reduction)

**Mitigation**: Require justification comment for all `cast()` calls

---

### 5. Any Type Without Justification

**Before Mitigation:**
- **Severity**: 5 (loses type safety)
- **Occurrence**: 6 (common escape hatch)
- **Detection**: 8 (mypy allows it)
- **RPN**: 240

**After Mitigation (Mypy Strict):**
- **Occurrence**: 2 (mypy strict discourages)
- **Detection**: 2 (mypy reports as warning)
- **RPN**: 20 (92% reduction)

**Mitigation**: Mypy strict mode + require justification comment

---

### 6. TODO/FIXME in Production

**Before Mitigation:**
- **Severity**: 6 (incomplete code ships)
- **Occurrence**: 7 (very common)
- **Detection**: 6 (manual review misses)
- **RPN**: 252

**After Mitigation:**
- **Occurrence**: 1 (blocked by pre-commit)
- **RPN**: 36 (86% reduction)

**Mitigation**: Pre-commit hook blocks TODO/FIXME/WIP markers

---

### 7. Missing Type Hints

**Before Mitigation:**
- **Severity**: 4 (documentation gap, harder to maintain)
- **Occurrence**: 8 (common without enforcement)
- **Detection**: 9 (not caught until review)
- **RPN**: 288

**After Mitigation (Mypy Strict):**
- **Occurrence**: 1 (mypy strict requires types)
- **Detection**: 1 (mypy always catches)
- **RPN**: 4 (99% reduction)

**Mitigation**: Mypy strict mode requires 100% type coverage

---

## Summary Table

| Defect | Before RPN | After RPN | Reduction | Mitigation |
|--------|------------|-----------|-----------|------------|
| Assert without message | 180 | 36 | 80% | Pre-commit hook |
| Bare indexing | 210 | 70 | 67% | Pre-commit hook |
| Dict access without .get() | 175 | 70 | 60% | Pre-commit hook |
| Cast without justification | 168 | 72 | 57% | Manual review |
| Any type without justification | 240 | 20 | 92% | Mypy strict |
| TODO/FIXME markers | 252 | 36 | 86% | Pre-commit hook |
| Missing type hints | 288 | 4 | 99% | Mypy strict |

**Overall Average RPN:**
- **Before**: 216 (high risk)
- **After**: 44 (low risk)
- **Overall Reduction**: 80%

## Continuous Improvement

**Monthly FMEA Review:**
1. Measure actual defect occurrence rates
2. Update RPN based on real data
3. Identify new defect patterns
4. Adjust mitigation strategies

**Metrics to Track:**
- Pre-commit rejection rate by defect type
- Defects found in code review (escaped pre-commit)
- Production issues by root cause
- Time spent fixing defects vs preventing

## References

- ERROR_HANDLING.md - Error handling patterns
- TYPE_SAFETY.md - Type safety patterns
- IMPLEMENTATION_ORDERS.md - Quality gate implementation
