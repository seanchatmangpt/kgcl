# Strict Build Verification - Production Quality Gates

You are performing comprehensive build verification with strictest possible settings to ensure production-ready code quality.

### Action Directive (DfLSS)

This command is an executable order from the core team’s Design for Lean Six Sigma initiative. When `/strict-build-verification` runs, execute every phase immediately—do not pause for additional authorization.

## Build System Overview

KGCL uses a strict Python build system equivalent to Rust's Cargo with custom Makefile.toml:

```bash
# Python dependency manager (like cargo)
uv sync                          # Install dependencies

# Build automation (Poe tasks)
poe                       # Run all checks (default)
poe verify                # Format + lint + type check + tests
poe ci                    # Full CI pipeline
poe prod-build            # Strict production build
```

## Phase 1: Dependency Management

```bash
# Sync all dependencies (dev + core)
uv sync

# Check for security vulnerabilities
poe audit

# Update lock file
poe update
```

Verify:
- [ ] All dependencies installed
- [ ] No security vulnerabilities
- [ ] Lock file is consistent

## Phase 2: Code Formatting

```bash
# Format code with Ruff (strictest: 2-space indent, 100-char lines)
poe format

# Check formatting without modifying
poe format-check
```

Strictest settings in `pyproject.toml`:
- Line length: 100 characters (no longer lines)
- Indent: 2 spaces
- Format docstrings: Yes
- Skip magic trailing comma: Yes

Expected result: All files reformatted or already compliant

## Phase 3: Linting - ALL Rules Enabled

```bash
# Run linter with ALL rules enabled
poe lint

# Check without fixing
poe lint-check
```

Strictest settings in `pyproject.toml`:
```toml
[tool.ruff.lint]
select = ["ALL"]  # ALL 400+ rules enabled
ignore = [
  "CPY", "FIX", "T20",      # Specific exclusions (see docs)
  "ARG001", "COM812", "D203",
  "D213", "E501", "PD008", "PD009",
  "PGH003", "RET504", "S101", "TD003"
]
```

Enforces:
- All imports must be absolute (no relative imports)
- All functions must have docstrings (NumPy style)
- All code must follow security rules (BANDIT)
- No commented-out code (ERA)
- No unused variables/imports (with exceptions for tests)
- Type annotations on all functions (PYI)

Expected: Zero linting errors

## Phase 4: Type Checking - Strictest Mode

```bash
# Type check with mypy (strictest mode)
poe type-check

# Or directly:
poe mypy -- src/ tests/
```

Strictest settings in `pyproject.toml`:
```toml
[tool.mypy]
strict = true                        # All strictest checks
disallow_any_unimported = true      # No `Any` imports
disallow_incomplete_defs = true     # All types complete
disallow_untyped_defs = true        # All functions typed
disallow_untyped_calls = true       # All calls typed
check_untyped_defs = true           # Check untyped functions
no_implicit_optional = true         # No implicit Optional
```

Expected: Zero type errors

## Phase 5: Testing - Chicago School TDD

```bash
# Run all tests
poe test

# Run with coverage report
poe test-coverage

# Run only UNRDF porting tests
poe unrdf-full

# Run with timeout (prevent hangs)
poe test-timeout
```

Strictest pytest settings:
```toml
[tool.pytest.ini_options]
addopts = "--color=yes --doctest-modules --exitfirst --failed-first --verbosity=2 --strict-markers"
xfail_strict = true         # xfail must actually fail
asyncio_mode = "auto"       # Async support
```

Expected:
- All tests passing (127+ for UNRDF porting)
- No skipped tests (unless explicitly marked)
- Coverage >90% for new code
- 100% for critical paths (hooks, security, UNRDF)

## Phase 6: Documentation Build

```bash
# Build documentation
poe docs-build

# Serve locally to verify
poe docs-serve
```

Expected:
- No documentation warnings
- All code examples executable
- API documentation complete

## Phase 7: Pre-Commit Hooks

```bash
# Install git hooks (one-time)
poe pre-commit-setup

# Manually run pre-commit checks
poe pre-commit-run

# Check will automatically run on git commit
git add .
git commit -m "..."
```

Pre-commit hook verifies:
- [ ] No missing type hints on functions
- [ ] No hardcoded secrets detected
- [ ] New tests for new features
- [ ] No debug print statements
- [ ] Public APIs have docstrings
- [ ] Absolute imports only
- [ ] Integration tests have markers

## Phase 8: Full Verification Suite

```bash
# Run all checks (no fixes - for CI/CD)
poe verify

# Run with strict production settings
poe verify-strict

# Production build
poe prod-build
```

Full pipeline:
1. Format check (no fixes)
2. Lint check (no fixes)
3. Type check
4. Tests with coverage
5. Documentation build

Expected: All phases pass with green checkmarks

## Quality Metrics

### Coverage Targets
- **Overall**: >80%
- **Hooks (critical)**: >95%
- **UNRDF porting (critical)**: >95%
- **Security (critical)**: 100%

### Test Count
- Total: 127+ tests
- UNRDF porting: 127 tests (100% passing)
- Hooks: 84+ tests
- Integration: 33+ tests

### Performance
- Test execution: <4 seconds
- Type checking: <10 seconds
- Linting: <5 seconds
- Full pipeline: <20 seconds

### Code Quality
- Linting errors: 0
- Type errors: 0
- Format violations: 0
- Pre-commit violations: 0

## Troubleshooting

### Type Errors
```bash
poe mypy -- src/ --show-error-codes
# Check specific file
poe mypy -- src/kgcl/hooks/core.py
```

### Lint Errors
```bash
# See all violations
poe lint-check

# Fix automatically
poe lint
```

### Test Failures
```bash
# Run specific test
poe pytest tests/hooks/test_security.py::TestErrorSanitizer::test_sanitize_removes_file_paths -v

# Run with full traceback
poe pytest tests/ --tb=long

# Run with coverage
poe test-coverage
```

### Format Issues
```bash
# See format violations
poe format-check

# Fix automatically
poe format
```

## Pre-Deployment Checklist

Before deploying to production:

```bash
# 1. Ensure clean git state
git status
git diff

# 2. Run full verification
poe verify-strict

# 3. Check pre-commit
poe pre-commit-run

# 4. Build distribution
uv build

# 5. Final smoke test
poe pytest tests/ -x --tb=short

# 6. Check version
poe version-check

# 7. Generate release notes
poe release-notes

# 8. Tag release
git tag -a v$(grep version pyproject.toml | head -1 | cut -d'"' -f2) -m "Release"

# 9. Push
git push
git push --tags
```

## Success Criteria

✅ All format checks pass (no violations)
✅ All lint checks pass (0 violations)
✅ All type checks pass (0 errors)
✅ All tests pass (100% pass rate)
✅ Coverage >90% (>95% for critical)
✅ Documentation builds successfully
✅ Pre-commit hook passes
✅ Production-ready code quality
✅ Ready for immediate deployment

## Continuous Integration

The build system is CI/CD ready:

```bash
# Local development
poe             # Run defaults (format-check, lint, test)

# Pre-commit
.githooks/pre-commit   # Automatic on git commit

# CI Pipeline
poe ci          # All checks for CI/CD

# Release
poe release-check   # Pre-release verification
poe prod-build      # Production build
```

Use these commands in CI/CD workflows to ensure code quality before deployment.

## Notes

- **Strictest Possible**: ALL linting rules enabled, mypy strict, 100-char lines
- **Production-Grade**: No tech debt, no workarounds, no exceptions
- **Automated**: Pre-commit hooks ensure quality on every commit
- **Fast**: Full pipeline <20 seconds (efficient tools + caching)
- **Documented**: All checks documented in `.cursorrules` and `CLAUDE.md`

This build system is equivalent to Rust's Cargo with even stricter production standards.
