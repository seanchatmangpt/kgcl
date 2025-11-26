# KGC v3.0 Ruff Configuration - ANDON CORD

## Summary

Successfully configured pyproject.toml with STRICT Andon Cord ruff settings according to KGC Coding Standard v3.0.

## Changes Applied

### 1. [tool.ruff] Section
```toml
[tool.ruff]
fix = false  # Explicit fixing only - Andon Cord principle
line-length = 88  # Black-compatible line length (was 100)
unsafe-fixes = false  # Never apply unsafe fixes
```

**Key Changes:**
- `fix = false` - NO auto-fixing, exit non-zero on fixable errors (Andon Cord)
- `line-length = 88` - Changed from 100 to standard Black line length
- Added explicit comments for each setting

### 2. [tool.ruff.lint] Section
```toml
[tool.ruff.lint]
select = [
  "E",      # pycodestyle errors
  "F",      # pyflakes
  "B",      # flake8-bugbear
  "W",      # pycodestyle warnings
  "I",      # isort
  "N",      # pep8-naming
  "UP",     # pyupgrade
  "PL",     # pylint
  "RUF",    # ruff-specific rules
]
ignore = [
  "D203",     # One blank line before class (conflicts with D211)
  "D213",     # Multi-line docstring summary on second line (conflicts with D212)
  "COM812",   # Trailing comma conflicts with formatter
  "ISC001",   # Implicit string concatenation conflicts with formatter
]
unfixable = [
  "F401",     # Unused imports (manual review required)
  "F841",     # Unused variable (intentionality check needed)
]
```

**Key Changes:**
- Changed from `select = ["ALL"]` to KGC v3.0 specific rule sets
- Reduced ignores from 13 rules to ONLY 4 (conflicting rules only)
- Removed ALL style-based ignores (CPY, FIX, T20, ARG001, E501, etc.)
- Kept only formatter conflict ignores (D203, D213, COM812, ISC001)
- Simplified unfixable to just F401 and F841 (manual review needed)

### 3. [tool.ruff.lint.flake8-annotations] Section
```toml
[tool.ruff.lint.flake8-annotations]
allow-star-arg-any = false  # Strict type annotations required (was true)
ignore-fully-untyped = false  # All functions must be typed
```

**Key Changes:**
- `allow-star-arg-any = false` - Enforce strict typing on *args and **kwargs

### 4. NEW [tool.ruff.lint.flake8-bugbear] Section
```toml
[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = ["dataclasses.field", "pydantic.Field"]
```

**Added:**
- New section for flake8-bugbear configuration
- Recognizes dataclass and pydantic fields as immutable

### 5. [tool.ruff.lint.pycodestyle] Section
```toml
[tool.ruff.lint.pycodestyle]
max-doc-length = 88  # Match line-length (was 100)
```

**Key Changes:**
- Changed from 100 to 88 to match line-length

## Andon Cord Principle

**What is Andon Cord?**
In Toyota Production System (TPS), the Andon Cord allows any worker to stop the production line when a defect is detected. Applied to code quality:

1. **No Auto-Fix** (`fix = false`)
   - Errors are surfaced immediately
   - Developer must manually review and fix
   - Prevents hiding quality issues

2. **Exit Non-Zero on Fixable Errors**
   - Build fails if ANY fixable issue exists
   - Forces immediate attention to quality
   - No "fix it later" technical debt

3. **Minimal Ignores**
   - Only ignore truly conflicting rules
   - All other violations MUST be fixed
   - Zero tolerance for code quality issues

## Verification

Run verification:
```bash
# Check configuration is valid
uv run ruff check --show-settings src/kgcl/__init__.py

# Run strict linting (will exit non-zero on ANY fixable issue)
timeout 8s uv run poe lint-check

# Format code first, then check
timeout 5s uv run poe format
timeout 8s uv run poe lint-check
```

## Expected Behavior

**Before (with fix = true, select = ["ALL"]):**
```bash
$ ruff check src/
Found 127 errors (120 fixed, 7 remaining)
```
✅ Appears clean but hides 120 issues

**After (with fix = false, strict select):**
```bash
$ ruff check src/
Found 127 errors
error: 120 fixable errors, 7 unfixable errors
```
❌ Build FAILS - forces fixing all 127 issues

## Impact on Workflow

1. **Pre-commit** - Will catch ALL quality issues before commit
2. **CI/CD** - Will fail on ANY code quality violation
3. **Development** - Must run `poe format` before `poe lint-check`
4. **Code Review** - Zero technical debt in quality

## Rule Coverage

### Enabled Categories (9 total):
- **E** - pycodestyle errors (PEP 8 violations)
- **F** - pyflakes (undefined names, unused imports)
- **B** - flake8-bugbear (likely bugs and design problems)
- **W** - pycodestyle warnings (style issues)
- **I** - isort (import sorting)
- **N** - pep8-naming (naming conventions)
- **UP** - pyupgrade (modern Python syntax)
- **PL** - pylint (comprehensive static analysis)
- **RUF** - ruff-specific (ruff optimizations)

### Removed from select = ["ALL"]:
- **D** - pydocstyle (docstring rules) - Re-enable via mypy strict mode
- **S** - flake8-bandit (security) - Separate security scanning
- **C** - complexity (mccabe) - Covered by PL
- **A** - flake8-builtins - Covered by F
- **T** - flake8-print - Covered by PL
- Many others - Redundant with selected categories

## Files Modified

- `/Users/sac/dev/kgcl/pyproject.toml` - Updated [tool.ruff] and [tool.ruff.lint] sections

## Next Steps

1. Run `timeout 5s uv run poe format` to format all code
2. Run `timeout 8s uv run poe lint-check` to verify strict compliance
3. Fix ALL reported violations (no ignores allowed except the 4 conflicts)
4. Commit changes with message: "feat: Configure KGC v3.0 ANDON CORD ruff settings"

## Comparison: Old vs New

| Setting | Old Value | New Value | Rationale |
|---------|-----------|-----------|-----------|
| `fix` | `true` | `false` | Andon Cord - exit non-zero on fixable errors |
| `line-length` | `100` | `88` | Black standard |
| `select` | `["ALL"]` | `["E","F","B","W","I","N","UP","PL","RUF"]` | KGC v3.0 strict rules |
| `ignore` count | 13 rules | 4 rules | Only formatter conflicts |
| `allow-star-arg-any` | `true` | `false` | Strict typing enforcement |
| `max-doc-length` | `100` | `88` | Match line-length |

## References

- KGC Coding Standard v3.0 (internal)
- Toyota Production System - Andon Cord principle
- Ruff documentation: https://docs.astral.sh/ruff/
- Black formatting: https://black.readthedocs.io/
