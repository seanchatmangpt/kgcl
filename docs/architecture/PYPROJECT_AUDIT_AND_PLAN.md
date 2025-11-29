# pyproject.toml Audit & Adaptation Plan

**Date**: 2025-11-28
**Status**: AUDIT COMPLETE - PLANNING PHASE
**Philosophy**: Restrictive > Permissive (Zero Tolerance)

---

## Executive Summary

**Current State**: Poe tasks exist but are **TOO PERMISSIVE**
**Mypy Config**: **LYING ABOUT STRICTNESS** (`strict = false` + 17 disabled error codes)
**Git Hooks**: Call ruff/mypy directly instead of using `uv run poe` tasks
**Anti-Patterns**: NOT BLOCKED (no check for `assert`, `cast()`, `NotImplementedError`, etc.)

**CRITICAL ISSUES:**
1. 🔴 Mypy is not strict despite claims in CLAUDE.md
2. 🔴 Hooks don't use poe tasks (violates standardization)
3. 🔴 Python anti-patterns not blocked
4. 🟡 No branch-aware validation (main vs feature)
5. 🟡 No Andon signal language in hooks
6. 🟡 No staged-file-only validation (slow)

---

## Current Poe Tasks (What EXISTS)

### ✅ Fast Tier (Good)
```toml
format-check     # ruff format --check src tests
lint-check       # ruff check src tests (no --fix)
detect-lies      # python scripts/detect_implementation_lies.py
```

### ✅ Heavy Tier (Good)
```toml
type-check       # mypy src/kgcl tests
test-coverage    # pytest --cov=src --cov-report=html
verify           # Sequences: format-check, lint-check, type-check, test-timeout
verify-strict    # Adds coverage + docs build
```

### ❌ Missing Tasks
```toml
pre-commit-fast     # MISSING - fast tier for pre-commit hook
pre-push-heavy      # MISSING - heavy tier for pre-push hook
antipattern-check   # MISSING - block assert/cast/NotImplementedError
```

---

## Mypy Configuration Audit

### Current Settings (pyproject.toml lines 120-168)

```toml
[tool.mypy]
strict = false  # 🔴 LYING - Claims strict but it's disabled

# GOOD: Function definitions must be typed
disallow_untyped_defs = true
disallow_incomplete_defs = true

# BAD: 17+ error codes DISABLED
disable_error_code = [
    "union-attr",       # Optional access
    "index",            # Indexing
    "arg-type",         # Argument types
    "call-arg",         # Call arguments
    "assignment",       # Assignments
    "attr-defined",     # Attribute access
    "operator",         # Operators
    "import-not-found", # Missing imports
    "import-untyped",   # Untyped imports
    "annotation-unchecked",
    "dict-item",
    "return-value",     # Return value types
    "misc",
    "var-annotated",
    "name-defined",
    "call-overload",
    "no-redef",
]
```

**ASSESSMENT**: This is **NOT STRICT**. It's permissive with documentation debt.

**Comment claims** (line 122-123):
> RESEARCH LIBRARY SETTINGS - Require typing on function defs and returns
> Tests excluded, SHACL validates at ingress

**Reality**: Disabling 17 error codes is NOT "research library settings", it's **accumulating technical debt**.

### Comparison to Reference Repos

**ggen (Rust)**: Uses `cargo check` (equivalent to mypy strict)
- NO error suppressions
- Compiler errors = RED Andon signal
- Zero tolerance

**knhk (Rust)**: Uses `cargo clippy` with `-D warnings`
- Warnings treated as errors
- Zero tolerance

**chicago-tdd-tools (Rust)**: Minimal config
- No suppressions
- Clean builds required

**KGCL (Python)**: 17 disabled error codes
- Comments justify as "research library"
- **This is a lie** - disabling errors doesn't make it "research quality"

---

## Git Hooks Audit

### Current Pre-Commit Hook (`scripts/git_hooks/pre-commit`)

**Lines 74-80:**
```bash
# ❌ WRONG - Direct ruff call
if timeout 5s uv run ruff format --check $STAGED_PY_FILES >/dev/null 2>&1; then
```

**Should be:**
```bash
# ✅ CORRECT - Use poe task
if timeout 5s uv run poe format-check; then
```

**Lines 86-93:**
```bash
# ❌ WRONG - Direct ruff call
LINT_OUTPUT="$(timeout 8s uv run ruff check --no-fix $STAGED_PY_FILES 2>&1 || true)"
```

**Should be:**
```bash
# ✅ CORRECT - Use poe task
LINT_OUTPUT="$(timeout 8s uv run poe lint-check 2>&1 || true)"
```

### Current Pre-Push Hook (`scripts/git_hooks/pre-push`)

**Lines 83-92:**
```bash
# ❌ WRONG - Direct ruff call
LINT_OUTPUT="$(timeout 30s uv run ruff check --no-fix src/ tests/ 2>&1 || true)"
```

**Should be:**
```bash
# ✅ CORRECT - Use poe task
LINT_OUTPUT="$(timeout 30s uv run poe lint-check 2>&1 || true)"
```

---

## Python Anti-Pattern Catalog (NEEDS IMPLEMENTATION)

### Category 1: Production Code Crashes (Not Currently Blocked)

**Should be FORBIDDEN in `src/` (not `tests/`):**

```python
# Crash-inducing patterns (like Rust unwrap)
assert condition               # Crashes on False
x[0]                          # IndexError if empty
dict["key"]                   # KeyError if missing
int(x)                        # ValueError if invalid
list.pop()                    # IndexError if empty
next(iterator)                # StopIteration if exhausted
```

**Allowed alternatives:**
```python
if not condition: raise ValueError("reason")  # Explicit
x[0] if x else default
dict.get("key", default)
try: int(x) except ValueError: ...
```

**QUESTION FOR USER:**
- Should we block ALL `assert` in src/? (too strict?)
- Or only `assert` without message? (`assert x` vs `assert x, "reason"`)

### Category 2: Type Lies (Not Currently Blocked)

```python
# Type suppression without justification
x: Any                        # Unconstrained type
cast(Type, value)             # Unchecked assertion
# type: ignore                # Blanket suppression
# type: ignore[error]         # No comment justifying
```

**Allowed with justification:**
```python
# type: ignore[import]  # External lib lacks stubs - tracked in #123
cast(Foo, x)  # Safe: x is validated by SHACL at ingress
```

**QUESTION FOR USER:**
- Should we require issue links for all type suppressions?
- Should we block `Any` entirely? (too strict?)

### Category 3: Implementation Lies (ALREADY BLOCKED)

**Current `detect-lies` script already blocks:**
```python
# TODO: implement
# FIXME: broken
# WIP: in progress
pass  # in function body
...   # ellipsis stub
raise NotImplementedError
```

**Status**: ✅ Working, keep as-is

### Category 4: Branch-Aware Rules (Not Implemented)

**Should be FORBIDDEN on `main` branch ONLY:**
```python
raise NotImplementedError  # Placeholder
# TODO: fix later
# FIXME: broken
```

**Allowed on feature branches** (for WIP)

**QUESTION FOR USER:**
- Do you want branch-aware rules like knhk?
- Strict on main, relaxed on feature branches?

---

## Ruff Configuration Audit

### Current Settings (Lines 255-298)

**Lines ignored (partial list):**
```toml
ignore = [
  "PLR0912",  # Too many branches - caught by unit tests
  "PLR0913",  # Too many arguments - caught by unit tests
  "PLR0915",  # Too many statements - caught by unit tests
  "E501",     # Line too long - readability preference
  "F401",     # Unused import - acceptable for re-exports
  "F841",     # Unused variable - caught by tests
  "F821",     # Undefined name - conditional imports
  # ... 20+ more
]
```

**ASSESSMENT**: Too many ignores with weak justifications

**Comments claim**: "caught by tests" or "style preference"

**Reality**: These should be fixed, not ignored

**QUESTION FOR USER:**
- Should we reduce ignore list to ONLY formatter conflicts?
- Current: 30+ ignores
- Lean Six Sigma standard: <5 ignores (only unavoidable conflicts)

---

## Required Changes (Prioritized)

### Priority 1: Fix Mypy Strictness (CRITICAL)

**Current:**
```toml
strict = false
disable_error_code = [17+ codes]
```

**Required:**
```toml
strict = true
# NO disable_error_code (or VERY minimal)
```

**Implementation:**
1. Set `strict = true`
2. Remove ALL `disable_error_code` entries
3. Fix resulting errors (100+ expected)
4. Only re-add TRULY unavoidable suppressions with clear justification

**Estimated effort**: 4-8 hours of fixing type errors

**User decision needed:**
- Do you want me to create this as a separate PR?
- Or fix in phases (one module at a time)?
- Or is current mypy config intentional for "research library"?

### Priority 2: Add Missing Poe Tasks

**Add to pyproject.toml:**

```toml
[tool.poe.tasks.pre-commit-fast]
help = "Fast pre-commit checks (<10s target)"
sequence = [
  "format-check",
  "lint-check",
  "detect-lies-staged"
]

[tool.poe.tasks.pre-push-heavy]
help = "Heavy pre-push validation (30-120s)"
sequence = [
  "type-check",
  "test-coverage",
  "detect-lies-strict",
  "antipattern-check"  # NEW - needs implementation
]

[tool.poe.tasks.antipattern-check]
help = "Block Python anti-patterns (assert, cast, etc.)"
cmd = "python scripts/detect_python_antipatterns.py src/"

[tool.poe.tasks.antipattern-check-staged]
help = "Check anti-patterns in staged files only"
cmd = "python scripts/detect_python_antipatterns.py --staged"
```

### Priority 3: Create `scripts/detect_python_antipatterns.py`

**Must block:**
1. `assert` in src/ without message
2. `cast()` without justification comment
3. Indexing without bounds check (`x[0]`, `dict["key"]`)
4. `Any` type without justification
5. `# type: ignore` without issue link

**Must support:**
- `--staged` flag for pre-commit (fast)
- `--warnings-as-errors` flag for pre-push
- Branch detection (strict on main only)

**Estimated effort**: 2-4 hours

### Priority 4: Update Git Hooks to Use Poe

**Replace in `scripts/git_hooks/pre-commit`:**
```bash
# OLD
timeout 5s uv run ruff format --check $STAGED_PY_FILES

# NEW
timeout 10s uv run poe pre-commit-fast
```

**Replace in `scripts/git_hooks/pre-push`:**
```bash
# OLD
timeout 30s uv run ruff check --no-fix src/ tests/

# NEW
timeout 120s uv run poe pre-push-heavy
```

### Priority 5: Add Andon Signal Language

**Update hooks to output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KGCL Pre-Commit (Fast Tier - Lean Six Sigma)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 1/3: Format check... ✓ PASSED (2.1s)
🔍 2/3: Lint check... ✓ PASSED (4.3s)
🔍 3/3: Anti-patterns... ✗ FAILED (1.2s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 ANDON SIGNAL: Pre-commit FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Found 3 anti-patterns in src/foo.py:
  Line 42: assert x  # Use explicit error handling
  Line 67: cast(int, y)  # Add justification comment
  Line 89: dict["key"]  # Use dict.get() for safety

🔧 How to fix:
  1. Replace assert with explicit ValueError
  2. Add comment justifying cast()
  3. Use dict.get("key", default)

📚 See: docs/patterns/ERROR_HANDLING.md

Total time: 7.6s (target: <10s)
```

### Priority 6: Reduce Ruff Ignores

**Current**: 30+ ignores
**Target**: <5 ignores (only formatter conflicts)

**Keep ONLY:**
```toml
ignore = [
  "D203",    # Conflicts with D211
  "D213",    # Conflicts with D212
  "COM812",  # Conflicts with formatter
  "ISC001",  # Conflicts with formatter
]
```

**Remove ALL others and fix the code instead**

---

## Missing Documentation (Must Create)

### 1. FMEA Document

**File**: `docs/quality/FMEA.md`

**Content needed:**
```markdown
# Failure Mode and Effects Analysis (FMEA)

## Python Anti-Pattern Defects

| Defect | Severity | Occurrence | Detection | RPN | Mitigation |
|--------|----------|------------|-----------|-----|------------|
| assert in production | 9 | 5 | 4 | 180 | Pre-commit hook blocks assert |
| cast() without check | 7 | 4 | 3 | 84 | Require justification comment |
| Missing type hints | 5 | 6 | 2 | 60 | Mypy strict enforcement |
| TODO on main branch | 3 | 7 | 1 | 21 | Branch-aware validation |
```

### 2. Error Handling Pattern Guide

**File**: `docs/patterns/ERROR_HANDLING.md`

**Content needed:**
```markdown
# Error Handling Patterns

## Forbidden Patterns

❌ `assert condition` - Crashes on False
✅ `if not condition: raise ValueError("reason")`

❌ `x[0]` - IndexError if empty
✅ `x[0] if x else default`

❌ `dict["key"]` - KeyError if missing
✅ `dict.get("key", default)`
```

### 3. Type Safety Guide

**File**: `docs/patterns/TYPE_SAFETY.md`

**Content needed:**
```markdown
# Type Safety Patterns

## When to use cast()

✅ ALLOWED:
```python
# Safe: Validated by SHACL at ingress
value = cast(Foo, raw_data)  # SHACL ensures type
```

❌ FORBIDDEN:
```python
# Unsafe: No validation
value = cast(Foo, x)  # Hope it's the right type
```
```

---

## Implementation Plan (Phases)

### Phase 1: Audit Complete ✅
- [x] Read pyproject.toml
- [x] Identify mypy permissiveness
- [x] Identify missing poe tasks
- [x] Identify Python anti-patterns not blocked
- [x] Compare to reference repos

### Phase 2: User Decisions Needed ⏸️

**User must decide:**
1. **Mypy strictness**: Fix now, or keep permissive for "research library"?
2. **Branch-aware rules**: Strict on main, relaxed on feature (like knhk)?
3. **Anti-pattern strictness**: Block ALL `assert` or only without message?
4. **Ruff ignores**: Reduce to <5 or keep current 30+?
5. **Implementation order**: Fix mypy first, or add hooks first?

### Phase 3: Create Scripts (NOT STARTED)

**Only proceed after Phase 2 decisions**

1. Create `scripts/detect_python_antipatterns.py`
   - Block assert/cast/indexing per decisions
   - Support --staged and --warnings-as-errors
   - Branch detection

2. Create `docs/quality/FMEA.md`
   - RPN tracking for each defect type

3. Create `docs/patterns/ERROR_HANDLING.md`
   - Forbidden patterns with alternatives

### Phase 4: Update Configuration (NOT STARTED)

1. Update pyproject.toml with new poe tasks
2. Fix mypy strictness (if decided)
3. Reduce ruff ignores (if decided)

### Phase 5: Update Hooks (NOT STARTED)

1. Rewrite pre-commit to use `uv run poe pre-commit-fast`
2. Rewrite pre-push to use `uv run poe pre-push-heavy`
3. Add Andon signal language
4. Add "How to fix" guidance

### Phase 6: Validation (NOT STARTED)

1. Test hooks on actual codebase
2. Measure defect detection rates
3. Verify SLA targets (<10s pre-commit, <120s pre-push)
4. Document actual RPN improvements in FMEA

---

## Questions for User (BLOCKING PHASE 2)

### Critical Questions

1. **Mypy Strictness**:
   - Q: Should I set `strict = true` and remove all 17 disabled error codes?
   - A: (waiting) _______
   - Impact: 100+ type errors to fix if yes

2. **Branch-Aware Validation**:
   - Q: Should TODO/FIXME/NotImplementedError be allowed on feature branches?
   - A: (waiting) _______
   - Impact: Needs branch detection in hooks

3. **Assert Blocking**:
   - Q: Block ALL `assert` in src/ or only `assert` without message?
   - A: (waiting) _______
   - Options:
     - Block all: `assert x` and `assert x, "msg"` both forbidden
     - Block only without message: `assert x` forbidden, `assert x, "msg"` allowed
     - Block none: Keep current (no blocking)

4. **Ruff Ignores**:
   - Q: Reduce from 30+ ignores to <5 (only formatter conflicts)?
   - A: (waiting) _______
   - Impact: Need to fix code instead of ignoring warnings

5. **Implementation Order**:
   - Q: Which priority first?
     - Option A: Fix mypy strictness first (4-8 hours)
     - Option B: Add hooks/poe tasks first (2-4 hours)
     - Option C: Create anti-pattern checker first (2-4 hours)
   - A: (waiting) _______

### Non-Critical Questions

6. **Staged-File-Only Validation**:
   - Q: Should pre-commit only validate staged files (faster)?
   - A: (waiting) _______
   - Current: Validates all files in src/ and tests/

7. **FMEA Tracking**:
   - Q: Should we track actual defect rates and RPN improvements?
   - A: (waiting) _______
   - Requires: Measuring defects before/after hook implementation

8. **Pattern Guide Creation**:
   - Q: Should I create ERROR_HANDLING.md and TYPE_SAFETY.md guides?
   - A: (waiting) _______
   - Impact: Referenced in hook error messages

---

## Anti-Lie Commitments

**I will NOT:**
- Implement anything before getting user decisions on Phase 2 questions
- Claim mypy is "strict" when it has `strict = false`
- Justify 17 disabled error codes as "research library standards"
- Skip creating FMEA document and claim "Lean Six Sigma quality"
- Implement anti-pattern checker without user approval on strictness level
- Touch code before plan is validated

**I WILL:**
- Wait for user decisions on all 8 questions
- Be honest about effort estimates
- Admit when I don't know Python best practices
- Test hooks before claiming they work
- Measure actual defect rates if implementing FMEA
- Document all assumptions clearly
