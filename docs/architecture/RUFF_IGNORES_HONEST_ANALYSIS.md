# Ruff Ignores - Honest Analysis

**Date**: 2025-11-28
**Admission**: I was wrong in Order 4. Not all ignores are laziness.

---

## My Mistake

**What I said**: "Delete all ignores except 4 formatter conflicts"

**What I should have said**: "Keep legitimate ignores, fix actual quality issues"

**The truth**: Many ignores are for:
- Formatter conflicts (must keep)
- Style preferences (up for debate)
- Research code patterns (legitimate)
- Only SOME are actual quality issues (should fix)

---

## Categorized Analysis of Current 42 Ignores

### Category 1: MUST KEEP (Formatter Conflicts)

```toml
"D203",     # Conflicts with D211 - formatter decides
"D213",     # Conflicts with D212 - formatter decides
"COM812",   # Trailing comma - formatter handles
"ISC001",   # String concat - formatter handles
```

**Verdict**: ✅ KEEP ALL 4 - These are unavoidable formatter conflicts

---

### Category 2: MUST KEEP (Legitimate Patterns)

```toml
"F403",     # Star import in __init__.py re-exports
"F401",     # Unused import in __init__.py re-exports
"E402",     # Module import not at top - needed for conditional imports
"B017",     # assertRaises(Exception) - legitimate test pattern
"RUF059",   # Unused self - protocol/ABC pattern
"PLC0415",  # Late imports - sometimes needed for circular deps
"PLW0603",  # Global statement - module initialization
```

**Verdict**: ✅ KEEP ALL 7 - These are legitimate Python patterns

---

### Category 3: RESEARCH CODE (Complexity Metrics)

```toml
"PLR0912",  # Too many branches
"PLR0913",  # Too many arguments
"PLR0915",  # Too many statements
"PLR0911",  # Too many return statements
"PLR2004",  # Magic values in comparisons
"PLR1714",  # Consider merging comparisons
"PLW2901",  # Outer loop variable overwritten
```

**Verdict**: 🟡 UP FOR DEBATE

**User's call**: Research code != production code
- Production: These would be code smells
- Research: Algorithm clarity > artificial limits

**Question for user**: Keep these for research flexibility?

---

### Category 4: STYLE PREFERENCES (Subjective)

```toml
"N802",     # Function name lowercase - external lib compat
"N806",     # Variable lowercase - external lib compat
"N817",     # CamelCase imported as acronym
"N818",     # Exception name Error suffix
"N811",     # Constant imported as non-constant
"E731",     # Lambda assignment
"B904",     # Raise from within except (no from)
"B905",     # zip without strict - Python <3.10 compat
"RUF015",   # Prefer next()
"RUF043",   # Slice copy
"RUF022",   # __all__ sorting
"UP028",    # Yield in for loop
"W505",     # Doc line too long
"E501",     # Line too long (already 120 chars)
```

**Verdict**: 🟡 UP FOR DEBATE

**User's call**: These are style, not quality
- Some needed for external lib compatibility (N802, N806)
- Some are readability preferences (E501, W505)
- Some are Python idiom preferences (E731, UP028)

**Question for user**: Worth changing code for these style nits?

---

### Category 5: QUALITY ISSUES (Should Fix)

```toml
"F841",     # Unused variable
"F821",     # Undefined name
"F811",     # Redefinition
"B007",     # Unused loop variable (caught by F841)
"RUF012",   # Mutable class attrs
"UP035",    # Deprecated typing imports
```

**Verdict**: ❌ SHOULD FIX THESE

**Why**: These are actual quality issues
- `F841` unused vars → Delete them or prefix `_unused`
- `F821` undefined names → Fix imports or conditionals
- `F811` redefinition → This is a bug, not a style choice
- `RUF012` mutable class attrs → Use `field(default_factory=...)`
- `UP035` deprecated imports → Use modern typing syntax

**Effort**: 1-2 hours to fix across codebase

---

### Category 6: FALSE POSITIVES (Technical Debt)

```toml
"RUF003",   # Ambiguous characters - false positives in comments
"RUF002",   # Ambiguous characters - false positives
"RUF001",   # Ambiguous characters - false positives
"RUF100",   # Unused noqa - cleanup after ignoring rules
```

**Verdict**: 🟡 UP FOR DEBATE

**Options**:
1. Keep ignores (accept false positives)
2. Fix the few real violations, remove ignores
3. Use per-file `# noqa` for specific false positives

---

## Revised Recommendations

### Instead of "Delete all to <5"

**Do this:**

1. **KEEP** (11 ignores):
   - Formatter conflicts: D203, D213, COM812, ISC001
   - Legitimate patterns: F403, F401, E402, B017, RUF059, PLC0415, PLW0603

2. **FIX CODE** (6 ignores - 1-2 hrs):
   - F841: Delete unused vars or prefix `_`
   - F821: Fix undefined names
   - F811: Fix redefinitions (likely bugs)
   - RUF012: Use `field(default_factory=...)`
   - UP035: Update to modern typing
   - B007: Covered by F841 fix

3. **USER DECIDES** (21 ignores):
   - Complexity metrics (7): Keep for research code?
   - Style preferences (14): Worth enforcing?

4. **INVESTIGATE** (4 ignores):
   - Ambiguous chars: How many real violations vs false positives?

---

## Updated Order 4

**OLD ORDER** (too aggressive):
> Delete all ignores except 4. Fix code.

**NEW ORDER** (honest):
> 1. Fix 6 actual quality issues (F841, F821, F811, RUF012, UP035, B007)
> 2. Keep 11 legitimate ignores (formatter + patterns)
> 3. User decides on 21 style/complexity ignores
> 4. Investigate 4 ambiguous char ignores

**Time**: 1-2 hours for fixes, not 4 hours

---

## Questions for User

### Question 1: Complexity Metrics (7 ignores)

Keep these for research code flexibility?
- PLR0912 (too many branches)
- PLR0913 (too many arguments)
- PLR0915 (too many statements)
- PLR0911 (too many returns)
- PLR2004 (magic values)
- PLR1714 (merge comparisons)
- PLW2901 (loop var overwrite)

**Your call**: Research algorithms vs artificial complexity limits

### Question 2: Style Preferences (14 ignores)

Worth changing code for these style nits?
- Naming conventions (N802, N806, N817, N818, N811)
- Lambda/comprehension style (E731, UP028, RUF015, RUF043)
- Exception handling style (B904, B905)
- Documentation style (W505, E501, RUF022)

**Your call**: Style consistency vs code churn

### Question 3: Should I Fix the 6 Quality Issues?

**These I recommend fixing** (actual bugs/debt):
- F841 (unused vars)
- F821 (undefined names)
- F811 (redefinitions)
- RUF012 (mutable class attrs)
- UP035 (deprecated typing)

**Estimated**: 1-2 hours

Do you want me to:
- A) Fix these 6 now
- B) Create issue to track them
- C) Keep ignoring them

---

## My Apology

I was wrong to prescribe "delete all ignores to <5" without understanding:
1. Formatter conflicts (must keep)
2. Legitimate Python patterns (must keep)
3. Research code needs (different from production)
4. Style vs quality (not all ignores are equal)

**The real issue**: Only 6 ignores are actual quality problems (unused vars, undefined names, etc.)

**Everything else**: Legitimate patterns or style preferences

Thank you for calling this out.
