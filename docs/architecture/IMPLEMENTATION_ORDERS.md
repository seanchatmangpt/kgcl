# Implementation Orders - Counteracting AI Laziness

**Date**: 2025-11-28
**Principle**: PRESCRIPTIVE > PERMISSIVE. Stop asking, start fixing.

---

## My Tendencies (Counteract These)

1. **Over-planning, under-doing** - Write 50-page docs instead of 50-line scripts
2. **False balance** - Present bad options as equally valid ("should we keep mypy permissive?")
3. **Avoid hard truths** - Say "consider" instead of "this is wrong, fix it"
4. **Analysis paralysis** - Create 8 blocking questions instead of making 1 decision
5. **Seek permission** - Ask "should I?" for obvious fixes
6. **Diplomatic hedging** - "Maybe we could..." instead of "You must..."

---

## Orders (Not Suggestions)

### Order 1: Fix Mypy Immediately - No Discussion

**The Truth**: `strict = false` with 17 disabled codes is **lying about quality**.

**Not a question**. Not an option. This is broken and must be fixed.

**DO THIS (in order):**

1. **Change pyproject.toml line 124:**
   ```toml
   # OLD (lying)
   strict = false

   # NEW (honest)
   strict = true
   ```

2. **Delete lines 150-168** (all `disable_error_code` entries)

3. **Run and capture failures:**
   ```bash
   uv run poe type-check 2>&1 | tee mypy_failures.txt
   ```

4. **Fix errors in THIS priority order:**
   - Import errors (missing stubs) → Add to overrides
   - Missing return types → Add `: ReturnType`
   - Untyped parameters → Add type hints
   - `Any` usage → Replace with specific types
   - Optional handling → Use proper `| None` checks

5. **Re-add ONLY unavoidable suppressions with THIS format:**
   ```toml
   # ONLY if truly unavoidable (external lib without stubs)
   [[tool.mypy.overrides]]
   module = "external_lib.*"
   ignore_missing_imports = true  # No stubs available upstream
   ```

**No "should we?"** - This is not optional. `strict = false` is a lie.

**Time estimate**: 4-8 hours. Do it in one session or don't claim "Lean Six Sigma quality".

---

### Order 2: Create Anti-Pattern Blocker - Stop Asking Permission

**The Truth**: Python has crash-inducing patterns like Rust's `unwrap()`. They must be blocked.

**DO THIS:**

Create `scripts/detect_python_antipatterns.py` that BLOCKS these in `src/` (not `tests/`):

```python
#!/usr/bin/env python3
"""Block Python anti-patterns that cause crashes in production.

Equivalent to Rust's clippy::unwrap_used.
"""

FORBIDDEN_PATTERNS = {
    # Pattern: regex, message, fix
    "assert_no_msg": (
        r"^\s*assert\s+[^,]+\s*$",
        "assert without message crashes on False",
        "Use: if not condition: raise ValueError('reason')"
    ),
    "bare_index": (
        r"\[\s*\d+\s*\](?!\s*=)",  # x[0] but not x[0] = ...
        "Indexing without bounds check crashes on IndexError",
        "Use: x[0] if len(x) > 0 else default"
    ),
    "dict_bracket": (
        r"\[\s*['\"][^'\"]+['\"]\s*\](?!\s*=)",
        "Dict access without .get() crashes on KeyError",
        "Use: dict.get('key', default)"
    ),
    "bare_cast": (
        r"cast\([^,]+,\s*[^)]+\)(?!\s*#)",
        "cast() without justification comment is unchecked assertion",
        "Use: cast(Type, x)  # Justified because: SHACL validates"
    ),
    "bare_any": (
        r":\s*Any(?!\s*#)",
        "Any type without justification loses type safety",
        "Use: : Any  # Justified because: external lib has no types"
    ),
}

def check_file(filepath: str, is_main_branch: bool) -> list[tuple[int, str, str]]:
    """Return violations: [(line_num, pattern, fix)]."""
    violations = []

    with open(filepath) as f:
        for line_num, line in enumerate(f, 1):
            # Skip tests/
            if "/tests/" in filepath or "/test_" in filepath:
                continue

            for name, (regex, msg, fix) in FORBIDDEN_PATTERNS.items():
                if re.search(regex, line):
                    violations.append((line_num, msg, fix))

    return violations

if __name__ == "__main__":
    # Exit non-zero if any violations found
    # Support --staged flag for pre-commit
    # Support --main-only for branch-aware validation
```

**No "should we?"** - These patterns crash. Block them.

**Time estimate**: 2 hours. Just do it.

---

### Order 3: Rewrite Hooks to Use Poe - No Direct Tool Calls

**The Truth**: Calling `uv run ruff` directly violates standardization principle.

**DO THIS:**

Replace in `scripts/git_hooks/pre-commit`:

```bash
# ❌ DELETE THIS (lines 74-93)
if timeout 5s uv run ruff format --check $STAGED_PY_FILES; then

# ✅ REPLACE WITH THIS
if timeout 10s uv run poe pre-commit-fast; then
```

Add to `pyproject.toml`:

```toml
[tool.poe.tasks.pre-commit-fast]
help = "Fast pre-commit validation (<10s)"
sequence = [
  "format-check",
  "lint-check",
  "detect-lies-staged",
  "antipattern-check-staged",
]

[tool.poe.tasks.antipattern-check-staged]
help = "Check anti-patterns in staged files"
cmd = "python scripts/detect_python_antipatterns.py --staged"
```

**No "should we?"** - Hooks MUST use poe for Lean Six Sigma traceability.

**Time estimate**: 30 minutes. Trivial change.

---

### Order 4: Reduce Ruff Ignores to <5 - Fix Code, Don't Ignore

**The Truth**: 30+ ignores with "caught by tests" justification is lazy.

**DO THIS:**

1. **In pyproject.toml, DELETE lines 261-297** (ALL ignores except these 4):
   ```toml
   ignore = [
     "D203",    # Conflicts with D211 (formatter)
     "D213",    # Conflicts with D212 (formatter)
     "COM812",  # Trailing comma (formatter)
     "ISC001",  # String concat (formatter)
   ]
   ```

2. **Run and fix:**
   ```bash
   uv run poe lint-check 2>&1 | tee ruff_violations.txt
   ```

3. **Fix violations in code, NOT by adding ignores back:**
   - `PLR0913` (too many args) → Refactor to use dataclass
   - `F401` (unused import) → Delete the import
   - `F841` (unused var) → Delete or prefix with `_`
   - `E501` (line too long) → Break into multiple lines

**No "should we keep some?"** - NO. Fix code or it's not production-ready.

**Time estimate**: 2-4 hours. Stop being lazy.

---

### Order 5: Add Andon Signals - Stop Being Terse

**The Truth**: Current hooks output is cryptic. Users need clear "How to fix" guidance.

**DO THIS:**

Add to `scripts/git_hooks/pre-commit`:

```bash
# After each check, output Andon signal format

check_passed() {
  echo "  ✅ PASSED ($1)"
}

check_failed() {
  echo "  ❌ FAILED"
  echo ""
  echo "🔧 How to fix:"
  echo "$2"
  echo ""
  echo "📚 See: $3"
}

# Example:
if run_format_check; then
  check_passed "2.1s"
else
  check_failed \
    "  1. Run: uv run poe format\n  2. Review changes\n  3. Commit again" \
    "docs/patterns/CODE_STYLE.md"
fi
```

**No "should we?"** - Clear error messages prevent defects. Not optional.

**Time estimate**: 1 hour. Copy patterns from reference hooks.

---

### Order 6: Branch-Aware Validation - Strict on Main Only

**The Truth**: Blocking TODO on feature branches kills velocity. Block only on main.

**DO THIS:**

Add to `scripts/detect_implementation_lies.py`:

```python
def is_main_branch() -> bool:
    """Check if current branch is main/master."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip() in ("main", "master")

def check_todos(filepath: str) -> list[str]:
    """Return TODO violations. Only enforced on main branch."""
    if not is_main_branch():
        return []  # Relaxed on feature branches

    violations = []
    # ... existing TODO detection logic
    return violations
```

**No "should we?"** - This is how knhk does it. It works. Copy it.

**Time estimate**: 30 minutes. Trivial addition.

---

### Order 7: Create Missing Docs - Stop Referencing Non-Existent Files

**The Truth**: Hooks will reference docs that don't exist. Create them first.

**DO THIS (in order):**

1. **Create `docs/patterns/ERROR_HANDLING.md`:**
   ```markdown
   # Error Handling Patterns

   ## Forbidden (Crashes)
   ❌ `assert x` - Crashes on False
   ✅ `if not x: raise ValueError("reason")`

   ❌ `x[0]` - IndexError if empty
   ✅ `x[0] if x else default`

   ❌ `dict["key"]` - KeyError if missing
   ✅ `dict.get("key", default)`
   ```

2. **Create `docs/quality/FMEA.md`:**
   ```markdown
   # FMEA - Python Anti-Patterns

   | Defect | Severity | Before RPN | After RPN | Mitigation |
   |--------|----------|------------|-----------|------------|
   | assert crash | 9 | 180 | 36 | Pre-commit blocks |
   | cast unsafe | 7 | 84 | 21 | Require justification |
   ```

3. **Create `docs/patterns/TYPE_SAFETY.md`:**
   ```markdown
   # Type Safety Patterns

   ## When cast() is allowed
   ✅ `cast(Foo, x)  # SHACL validates type at ingress`
   ❌ `cast(Foo, x)  # Hope it works`
   ```

**No "should we?"** - Hooks will reference these. Create or don't add references.

**Time estimate**: 30 minutes. Just write them.

---

## Implementation Priority (PRESCRIPTIVE)

Do these IN ORDER. Don't skip. Don't parallelize.

### Week 1: Fix Quality Gates
1. **Monday**: Fix mypy strict (4-8 hrs)
2. **Tuesday**: Create anti-pattern checker (2 hrs)
3. **Wednesday**: Reduce ruff ignores (2-4 hrs)
4. **Thursday**: Create pattern docs (30 min)
5. **Friday**: Update hooks to use poe (30 min)

### Week 2: Add Features
6. **Monday**: Add Andon signals to hooks (1 hr)
7. **Tuesday**: Add branch-aware validation (30 min)
8. **Wednesday**: Test on codebase, measure defects
9. **Thursday**: Document actual RPN improvements in FMEA
10. **Friday**: Update CLAUDE.md with actual status

---

## Non-Negotiable Rules

### 1. No More Planning Documents

If I create another planning doc before implementing these 7 orders, you should:
- Reject the PR
- Tell me to implement first, document after

### 2. No More "Should We?" Questions

If I ask permission for obvious fixes (like `strict = true`), you should:
- Say "Just do it"
- Point to this document

### 3. No More False Balance

If I present "keep mypy permissive" as a valid option, you should:
- Call out the lie
- Remind me: permissive = technical debt, not quality

### 4. No More Estimation Hedging

If I say "4-8 hours OR we could do it in phases", you should:
- Pick the aggressive estimate
- Say "4 hours, one session, get it done"

### 5. Measure or Shut Up

If I claim "Lean Six Sigma quality", you should ask:
- What's your current defect rate?
- What's your RPN before/after?
- Where's the data?

If I can't answer with numbers, I'm lying.

---

## How to Reject My Laziness

### Lazy Pattern 1: "Let me create a comprehensive analysis..."
**Response**: "No. Create the script. Show me it works."

### Lazy Pattern 2: "Should we...?" / "Consider..."
**Response**: "Stop asking. Order 1 says fix mypy. Do it."

### Lazy Pattern 3: "There are several approaches..."
**Response**: "Pick one. Implement. Move on."

### Lazy Pattern 4: "Estimated 4-8 hours..."
**Response**: "4 hours. One session. Start now."

### Lazy Pattern 5: "We could do this in phases..."
**Response**: "No phases. Do it all or don't claim it's done."

---

## Success Criteria (Measurable)

After implementing ALL 7 orders, I must show:

1. **Mypy strict passing**: 0 errors with `strict = true`
2. **Anti-patterns blocked**: Script exits non-zero on violations
3. **Hooks use poe**: No direct `uv run ruff` calls
4. **Ruff ignores <5**: Only formatter conflicts remain
5. **Andon signals working**: Clear "How to fix" in output
6. **Branch-aware**: TODOs allowed on feature, blocked on main
7. **Docs exist**: ERROR_HANDLING.md, FMEA.md, TYPE_SAFETY.md

If ANY of these are incomplete, the work is incomplete.

---

## The Test: Can I Ship This?

Before claiming "done", answer these:

1. Can I run `uv run poe verify` and it passes? (YES/NO)
2. Can I commit with TODO on feature branch? (YES/NO)
3. Can I commit with TODO on main branch? (NO/YES) - should be NO
4. Can I commit with `assert x` in src/? (NO/YES) - should be NO
5. Does mypy have `strict = true`? (YES/NO) - should be YES
6. Are there <5 ruff ignores? (YES/NO) - should be YES
7. Do error messages show "How to fix"? (YES/NO) - should be YES

If ANY answer is wrong, I lied about being done.

---

## My Commitment

I will:
- ✅ Implement all 7 orders in sequence
- ✅ Show working code, not plans
- ✅ Measure actual results (defect rates, RPNs)
- ✅ Complete each order fully before moving to next
- ✅ Accept aggressive timelines (4 hrs not 8)

I will NOT:
- ❌ Create more planning documents
- ❌ Ask "should we?" for obvious fixes
- ❌ Present false choices (permissive is NOT valid)
- ❌ Skip measuring actual improvements
- ❌ Claim "done" with incomplete work
- ❌ Hedge with "or we could..." alternatives

**If I break these commitments, reject the work and cite this document.**
