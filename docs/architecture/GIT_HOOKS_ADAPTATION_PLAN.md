# Git Hooks Adaptation Plan - Rust → Python/KGCL

**Date**: 2025-11-28
**Status**: PLANNING ONLY - NO IMPLEMENTATION YET
**Philosophy**: Restrictive > Permissive (Zero Tolerance Quality)

---

## Reference Hook Analysis

### 1. ggen (Rust) - Fast Tier Philosophy

**Key Patterns:**
- **Tiered validation**: Fast (pre-commit <5s) vs Heavy (pre-push 30-120s)
- **Andon signals**: Red (stop), Yellow (warning), Green (clear)
- **Standardization**: Uses `cargo make` for ALL operations
- **Auto-fix**: Format issues auto-corrected, not just flagged
- **Value-based**: Each check has documented defect detection % value

**Rust Commands:**
```bash
cargo make check      # Fast validation
cargo fmt --all       # Format check
```

**Python Translation Needed:**
- `cargo make check` → `uv run poe ???` (what's the equivalent?)
- `cargo fmt` → `uv run poe format`
- How do we measure "62% defect detection value" for Python checks?

**GAPS IN KNOWLEDGE:**
- [ ] What's Python equivalent of Rust's "cargo check"? (compilation check)
- [ ] Should we run `mypy` in pre-commit (fast) or pre-push (heavy)?
- [ ] What's our target time for pre-commit? (<5s like ggen or <10s current?)

---

### 2. knhk (Rust) - Branch-Aware Strictness

**Key Patterns:**
- **Main branch rules**: ZERO TODO/FUTURE/unimplemented allowed
- **Feature branch rules**: Relaxed (TODO/FUTURE allowed for WIP)
- **Smart exemptions**: Test files can use unwrap()/expect()
- **Andon integration**: Compiler errors = RED signal, blocks commit
- **Staged-file-only**: Only validate files being committed (speed)

**Rust Anti-Patterns Blocked:**
```rust
.unwrap()           // Panic on None/Err - FORBIDDEN in production
.expect("msg")      // Panic with message - FORBIDDEN in production
unimplemented!()    // Placeholder - FORBIDDEN on main branch
TODO/FUTURE         // Comments - FORBIDDEN on main branch
```

**Python Translation Needed:**
```python
# What are Python's equivalents to Rust anti-patterns?
assert x is not None  # Should this be forbidden? (Rust unwrap equivalent?)
raise NotImplementedError  # Obvious equivalent to unimplemented!()
# TODO: fix later  # Same as Rust
pass  # Empty function body - is this a lie?
...   # Ellipsis stub - is this a lie?
```

**QUESTIONS:**
- [ ] Should `assert` be forbidden in production code? (crashes like Rust unwrap)
- [ ] What about `cast()` from typing? (unchecked type assertion)
- [ ] Should we allow `NotImplementedError` on feature branches only?
- [ ] What about docstring stubs: `"""TODO: Add docstring"""`?

**Branch Detection:**
```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "main" ]; then
  # STRICT MODE
else
  # RELAXED MODE
fi
```

**ADAPTATION PLAN:**
1. Detect main vs feature branch in hooks
2. Define Python anti-pattern list (see below)
3. Block anti-patterns on main ONLY
4. Allow on feature branches for WIP

---

### 3. chicago-tdd-tools (Rust) - FMEA-Based

**Key Patterns:**
- **FMEA tracking**: Each check has RPN (Risk Priority Number)
- **Clear guidance**: Every error shows "How to fix"
- **Minimal checks**: Only 2 checks (unwrap/expect, docs)
- **References docs**: Points to SPR_GUIDE.md for patterns
- **Allow bypass**: `SKIP_UNWRAP_CHECK=1` for emergencies (DISCOURAGED)

**FMEA Example:**
```
# Before: RPN 180 (Severity: 9, Occurrence: 5, Detection: 4)
# After: RPN 36 (Severity: 9, Occurrence: 1, Detection: 4)
# Mitigation: Pre-commit hook prevents unwrap/expect
```

**Error Message Quality:**
```
❌ ERROR: Cannot commit unwrap/expect calls in production code

Found 3 unwrap() and 2 expect() calls in:
  src/foo.rs: 3 unwrap(), 0 expect()
  src/bar.rs: 0 unwrap(), 2 expect()

🔧 How to fix:
  1. Use '?' operator for error propagation: result?
  2. Use 'if let' or 'match' for Option/Result handling
  3. Use assert_ok!()/assert_err!() in tests
  4. If intentional, add #[allow(clippy::unwrap_used)] with comment

📚 See: docs/process/SPR_GUIDE.md for error handling patterns
```

**Python Translation:**
- What's KGCL's FMEA? Do we track RPN for defects?
- Where's our equivalent to SPR_GUIDE.md? (Error handling patterns)
- What's our "How to fix" guidance for each check?

**GAPS:**
- [ ] No FMEA document exists for KGCL
- [ ] No error handling pattern guide exists
- [ ] No RPN tracking for defect types
- [ ] Error messages are terse, not educational

---

## Python Anti-Pattern Catalog (DRAFT - NEEDS VALIDATION)

### Category 1: Production Code Crashes (Rust unwrap equivalent)

**Forbidden in production code (src/):**
```python
assert condition          # Crashes on False (like Rust unwrap)
x[0]                      # IndexError crash (unchecked)
dict["key"]               # KeyError crash (unchecked)
int(x)                    # ValueError crash (unchecked conversion)
```

**Allowed alternatives:**
```python
if not condition: raise ValueError("reason")  # Explicit error
x[0] if x else default     # Safe access
dict.get("key", default)   # Safe access
try: int(x) except ValueError: ...  # Explicit handling
```

**QUESTION:** Is this too strict? Should we allow `assert` in internal functions?

### Category 2: Implementation Lies (Already Blocked)

**Forbidden everywhere (current behavior):**
```python
# TODO: implement this
# FIXME: broken
# HACK: workaround
# WIP: in progress
pass  # Empty function body
...   # Ellipsis placeholder
raise NotImplementedError  # Placeholder
```

**Current detection:** Working, keep as-is.

### Category 3: Type Lies (Mypy Violations)

**Forbidden everywhere:**
```python
# type: ignore           # Blanket suppression
# type: ignore[error]    # Specific suppression without comment
Any                      # Unconstrained type
cast(X, y)               # Unchecked type assertion
```

**Allowed with justification:**
```python
# type: ignore[import]  # External library lacks stubs - tracked in #123
```

**QUESTION:** Should we require issue tracking for all type suppressions?

### Category 4: Test Theater (Domain-Specific)

**Forbidden in test files:**
```python
assert True              # Meaningless assertion
assert result            # What does this prove?
# Covered by current "detect-lies" check
```

**Allowed:**
```python
assert len(tokens) == 3  # Specific assertion
assert "error" in result # Specific check
```

---

## Poe Task Restructuring Plan

### Current KGCL poe Tasks (from pyproject.toml)

**ASSUMPTION:** These exist, need to verify:
```toml
[tool.poe.tasks]
format = "ruff format src/ tests/"
lint = "ruff check --fix src/ tests/"
type-check = "mypy src/ tests/"
test = "pytest tests/ -v"
verify = ["format", "lint", "type-check", "test"]
detect-lies = "python scripts/detect_implementation_lies.py"
```

**GAPS TO CHECK:**
- [ ] Does `verify` actually exist and run all checks?
- [ ] Is there a `format-check` (no auto-fix) for pre-commit?
- [ ] Is there a `lint-check` (no auto-fix) for pre-commit?
- [ ] What flags does `test` use? (coverage, warnings, etc.)

### Proposed Poe Task Structure (NEEDS REVIEW)

**Fast Tier (Pre-Commit <10s):**
```toml
[tool.poe.tasks]
format-check = "ruff format --check src/ tests/"  # No auto-fix
lint-fast = "ruff check --no-fix src/ tests/"     # No auto-fix
detect-lies = "python scripts/detect_implementation_lies.py"
pre-commit = ["format-check", "lint-fast", "detect-lies"]
```

**Heavy Tier (Pre-Push 30-120s):**
```toml
[tool.poe.tasks]
type-check = "mypy --strict src/ tests/"
test-strict = "pytest tests/ -v --tb=short -W error"  # Warnings as errors
lint-full = "ruff check --no-fix src/ tests/"
verify = ["type-check", "test-strict", "lint-full", "detect-lies"]
```

**QUESTIONS:**
- [ ] Should pre-commit auto-fix format issues like ggen?
- [ ] Should we add `--staged-only` flag to check only staged files?
- [ ] What about coverage requirements in pre-push?

---

## Hook Adaptation Checklist

### Pre-Commit Hook Adaptations

**From ggen:**
- [ ] Add Andon signal colors (Red/Yellow/Green)
- [ ] Add timeout for each check (format: 2s, lint: 5s)
- [ ] Add auto-fix for format issues
- [ ] Add value metrics (% defect detection)
- [ ] Use poe tasks, not direct commands

**From knhk:**
- [ ] Add branch detection (main vs feature)
- [ ] Block TODO/FIXME/NotImplementedError on main ONLY
- [ ] Add staged-file-only validation
- [ ] Add smart exemptions (tests can use assert)

**From chicago-tdd-tools:**
- [ ] Add FMEA RPN tracking
- [ ] Improve error messages with "How to fix"
- [ ] Add references to pattern docs
- [ ] Add emergency bypass flag

**CURRENT BLOCKERS:**
1. No FMEA document exists - can't add RPN tracking
2. No pattern guide exists - can't reference it in errors
3. Unclear if poe tasks are complete - need to audit pyproject.toml
4. Unclear Python anti-pattern list - need validation

### Pre-Push Hook Adaptations

**From ggen:**
- [ ] Add full test suite with coverage requirement
- [ ] Add performance benchmarks (if any exist)
- [ ] Add memory leak detection (if applicable)

**From knhk:**
- [ ] Run Andon signal checks (test failures = RED stop)
- [ ] Add PYTHONWARNINGS=error (treat warnings as errors)
- [ ] Block if any tests fail
- [ ] Block if coverage <80%

**From chicago-tdd-tools:**
- [ ] Validate documentation changes
- [ ] Run comprehensive lie detection

**QUESTIONS:**
- [ ] Do we have performance benchmarks to run?
- [ ] Do we have memory leak tests?
- [ ] What's our coverage requirement? (80% stated in CLAUDE.md)

---

## Implementation Lies to Prevent (Be Honest)

### Things I Don't Know

1. **What's in pyproject.toml?** - Haven't read it, need to audit
2. **What's the actual poe task list?** - Don't know if `verify` exists
3. **Is there an FMEA document?** - Seems like no
4. **Is there a pattern guide?** - No SPR_GUIDE.md equivalent found
5. **What's our Python anti-pattern list?** - Not defined, need validation
6. **Do we have performance benchmarks?** - Don't know
7. **What's our coverage measurement tool?** - Assume pytest-cov but not verified

### Things I Might Lie About

1. **"This will catch all defects"** - NO, it will catch SOME patterns
2. **"This is equivalent to Rust unwrap"** - MAYBE, need validation
3. **"Tests will run in <30s"** - DON'T KNOW, depends on test suite size
4. **"This follows Lean Six Sigma"** - ONLY IF we measure defect rates
5. **"Branch detection is simple"** - YES, but merges/rebases complicate it

---

## Next Steps (PLANNING PHASE)

### Phase 1: Audit Current State
1. Read `/Users/sac/dev/kgcl/pyproject.toml` - verify poe tasks
2. Check if FMEA document exists
3. Check if pattern guide exists (like SPR_GUIDE.md)
4. Verify coverage measurement setup
5. List all current pre-commit/pre-push checks

### Phase 2: Define Standards
1. Create Python anti-pattern catalog (with user validation)
2. Create FMEA document with RPN for each defect type
3. Create pattern guide (error handling, testing, types)
4. Define branch-aware rules (main vs feature)

### Phase 3: Design Hooks
1. Design pre-commit hook with Andon signals
2. Design pre-push hook with strict validation
3. Design poe task structure (fast vs heavy tier)
4. Design error messages with "How to fix" guidance

### Phase 4: Implementation (NOT YET)
- Only proceed after Phases 1-3 are validated by user
- No coding until plan is approved
- No assumptions about what "should" exist

---

## Questions for User (HONEST GAPS)

1. **Poe tasks**: Should I read pyproject.toml to see what exists?
2. **FMEA**: Should we create one, or does it exist somewhere?
3. **Pattern guide**: Should we create one (like SPR_GUIDE.md for Rust)?
4. **Python anti-patterns**: Is the draft list above correct? Too strict? Too lenient?
5. **Branch rules**: Do you want strict-on-main, relaxed-on-feature like knhk?
6. **Auto-fix**: Should pre-commit auto-fix format issues like ggen?
7. **Performance**: Do we have benchmarks to run in pre-push?
8. **Coverage**: What's our minimum coverage requirement? (80% per CLAUDE.md)

---

## Anti-Lie Commitments

**I will NOT:**
- Claim hooks are "production-ready" without testing
- Claim checks catch "all defects" - only measurable patterns
- Implement before getting user validation on plan
- Make up Python anti-patterns without verification
- Assume poe tasks exist without reading pyproject.toml
- Skip Phase 1 audit to "save time"

**I WILL:**
- Be explicit about what I don't know
- Ask for validation before implementing
- Test hooks on actual codebase before claiming they work
- Measure defect detection rates if implementing FMEA
- Document assumptions clearly
- Admit when Rust patterns don't translate cleanly to Python
