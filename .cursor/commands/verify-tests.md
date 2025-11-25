# Verify Tests Before Completion (KGCL)

## Purpose

Guarantee that every change leaves the KGCL test suite green. This command covers running the correct suites, triaging failures, fixing root causes, and proving the fix with data.

### Action Directive (DfLSS)

Issued under the core team’s Design for Lean Six Sigma initiative: when `/verify-tests` is called, run and repair the suites immediately without waiting for further approval.

## Workflow

```
Run → Diagnose → Fix → Re-run → Record
```

## 1. Run the Right Suites

```bash
poe test                 # full pytest suite
poe unrdf-full           # UNRDF parity (when relevant)
poe pytest tests/cli -vv     # CLI-focused failures
```

Always capture output:

```bash
poe test 2>&1 | tee reports/pytest.log
```

## 2. Diagnose Failures

For each failure:

1. Copy the exact pytest node (e.g., `tests/hooks/test_security.py::TestErrorSanitizer::test_masks_paths`).
2. Re-run just that node with `poe pytest <node> -vv --maxfail=1`.
3. Inspect receipts, LinkML reports, or SPARQL plans referenced in the error.

Determine the failure type:

| Type | Signals | Next Step |
| --- | --- | --- |
| Regression | Assertion changed unexpectedly | Use `/root-cause-analysis` |
| Flake | Passes locally, fails CI randomly | Stabilize timing/resources |
| Environment | Missing dependency or schema | Fix build/CLI wiring |

## 3. Fix

Follow Chicago principles:

- Reproduce the failing scenario first.
- Add/adjust tests before or alongside the fix.
- Prefer design fixes (e.g., sanitized receipts, typed constructors) over ad-hoc patches.

## 4. Re-run & Prove

After applying the fix:

```bash
poe pytest <node> -vv
cargo-make test
cargo-make unrdf-full          # if touched UNRDF
```

All commands must exit 0 twice in a row. For flaky tests, run an additional loop (e.g., `pytest -n auto --count=5`) to confirm stability.

## 5. Record

Document in the PR or commit:

- Failing test node(s)
- Root cause summary
- Fix description
- Tests added/updated

If the issue exposed a missing invariant, link to `/poka-yoke-design` or `/kaizen-improvement` follow-ups.

## Tips

1. Use `pytest -vv --maxfail=1` for faster iterations.
2. Turn on `PYTEST_ADDOPTS="--strict-markers --tb=short"` locally to match CI.
3. For CLI issues, capture the exact command and output for reproducibility.
4. For LinkML failures, store the generated validation report under `reports/`.
5. Never skip or xfail a test without a tracked issue and explicit approval.

## Related Commands

- [Strict Build Verification](./strict-build-verification.md)
- [Root Cause Analysis](./root-cause-analysis.md)
- [Verify UNRDF Porting](./verify-unrdf-porting.md)
- **Test count**: How many tests exist?
- **Failure count**: How many tests fail?
- **Failure rate**: What percentage of tests fail?
- **Failure types**: What types of failures (compilation, test, panic, timeout)?

**Action**: Collect baseline data

```bash
# Count total tests
cargo make test 2>&1 | grep -c "test.*\.\.\."
# Output: 150 tests total

# Count failures
cargo make test 2>&1 | grep -c "FAILED"
# Output: 5 failures

# Calculate failure rate
# 5 failures / 150 tests = 3.3% failure rate

# Categorize failures
# Compilation errors: 2
# Test failures: 2
# Panics: 1
# Timeouts: 0

**Example baseline data**:
```markdown
## Baseline Data

**Total Tests**: 150
**Failures**: 5
**Failure Rate**: 3.3% (5/150)

**By Type**:
- Compilation errors: 2 (40%)
- Test failures: 2 (40%)
- Panics: 1 (20%)
- Timeouts: 0 (0%)
```

---

### Step 2: Analyze Test Results

**Action**: Parse test output to identify all failures and categorize them.

#### 2.1: Extract Failure Information

**Look for these patterns in output**:

**Compilation Errors**:
```
error[E...]: <description>
  --> src/file.rs:line:column
```

**Test Failures**:
```
test test_name ... FAILED
```

**Panics**:
```
thread 'test_name' panicked at '<message>', src/file.rs:line:column
```

**Timeouts**:
```
test test_name ... timeout
```

#### 2.2: Categorize Failures

**Create failure list**:

```markdown
## Test Failures

### Compilation Errors
- [ ] `src/fixture.rs:123` - Error: `expected type, found ...`

### Test Failures
- [ ] `test_fixture_creation` - Error: `Fixture creation failed`
- [ ] `test_builder_pattern` - Error: `assertion failed: expected 10, got 5`

### Panics
- [ ] `test_async_operation` - Panic: `called Result::unwrap() on an Err value`

### Timeouts
- [ ] `test_slow_operation` - Timeout after 60s
```

#### 2.3: Prioritize Fixes

**Priority Order**:
1. **Compilation errors** - Must fix first (blocks everything)
2. **Test failures** - Fix by test importance (critical path first)
3. **Panics** - Fix immediately (indicates bugs)
4. **Timeouts** - Fix or optimize (may indicate performance issues)

---

### Step 3: Fix Test Failures

**Action**: Systematically fix each failure category.

#### 3.1: Fix Compilation Errors

**For each compilation error**:

**Step 3.1.1**: Read error message carefully
- Understand what the compiler is complaining about
- Identify the root cause

**Step 3.1.2**: Fix the error
- Update code to resolve compilation issue
- Ensure type safety
- Fix import statements if needed

**Step 3.1.3**: Verify fix
```bash
cargo make check
```

**Step 3.1.4**: Repeat until all compilation errors fixed

**Common Fixes**:
- Missing imports: Add `use` statements
- Type mismatches: Fix type annotations
- Missing features: Enable feature flags in `Cargo.toml`
- Syntax errors: Fix syntax issues

#### 3.2: Fix Test Failures

**For each test failure**:

**Step 3.2.1**: Read test failure message
- Understand what the test expected vs. what it got
- Identify the root cause

**Step 3.2.2**: Determine if test or implementation is wrong
- Review test logic
- Review implementation logic
- Check if test needs updating or implementation needs fixing

**Step 3.2.3**: Fix the issue
- Update test if test is wrong
- Update implementation if implementation is wrong
- Ensure test follows AAA pattern (see [Core Team Best Practices](../.cursorrules))

**Step 3.2.4**: Verify fix
```bash
cargo make test test_name
```

**Step 3.2.5**: Repeat for each failing test

**Common Fixes**:
- Wrong expected values: Update assertions
- Missing setup: Add Arrange phase
- Feature flags: Enable required features

#### 3.3: Fix Panics

**For each panic**:

**Step 3.3.1**: Identify panic source
- Read stack trace
- Find the exact line causing panic

**Step 3.3.2**: Fix panic source
- Replace `unwrap()`/`expect()` with proper error handling
- Add null checks
- Fix index out of bounds
- Handle edge cases

**Step 3.3.3**: Verify fix
```bash
cargo make test test_name
```

**Step 3.3.4**: Repeat for each panic

**Common Fixes**:
- `unwrap()` on `None`: Use `match` or `?` operator
- Index out of bounds: Add bounds checking
- Division by zero: Add zero checks

**Reference**: See [Expert Testing Patterns](./expert-testing-patterns.md) for panic safety testing

#### 3.4: Fix Timeouts

**For each timeout**:

**Step 3.4.1**: Identify slow operation
- Review test code
- Find the operation taking too long

**Step 3.4.2**: Optimize or mock
- Optimize slow code
- Mock external dependencies
- Increase timeout if legitimate
- Use test fixtures for setup

**Step 3.4.3**: Verify fix
```bash
cargo make test test_name
```

**Step 3.4.4**: Repeat for each timeout

**Common Fixes**:
- Mock external APIs
- Optimize algorithms
- Increase timeout for legitimate slow operations

**Note**: The entire test suite must complete in <1 second. If individual tests are too slow, optimize them.

---

### Step 4: Re-Run Tests

**Action**: Run tests again to verify all fixes worked.

```bash
cargo make test
```

**Expected Result**: All tests pass (exit code 0)

**If this step fails**: 
- Return to Step 2
- Identify remaining failures
- Fix them in Step 3
- Repeat until all tests pass

**If this step succeeds**: Proceed to Step 5

**CRITICAL**: Do not mark work as complete until Step 4 passes completely.

---

### Step 5: Verify Completion

**Action**: Final verification that work is complete.

#### 5.1: Verify All Tests Pass

```bash
cargo make test
```

**Expected**: Exit code 0, all tests pass

#### 5.2: Verify Compilation

```bash
cargo make check
```

**Expected**: Exit code 0, no compilation errors

#### 5.3: Verify No Pending Test Fixes

**Check**: Review todo list for any pending test fixes

**Action**: Remove completed test fixes from todo list

**Expected**: No pending test fixes remain

#### 5.4: Measure Improvement (DMAIC Measurement)

**Action**: Measure improvement against baseline data.

**Measurement**:
- Re-count failures after fixes
- Compare to baseline
- Calculate improvement percentage
- Verify success criteria met

**Action**: Measure improvement

```bash
# Re-count failures after fixes
cargo make test 2>&1 | grep -c "FAILED"
# Output: 0 failures (down from 5)

# Calculate improvement
# Baseline: 5 failures (3.3% failure rate)
# After fixes: 0 failures (0% failure rate)
# Improvement: 100% (5/5 failures fixed)
```

**Example improvement measurement**:
```markdown
## Improvement Measurement

**Baseline**: 5 failures (3.3% failure rate)
**After Fixes**: 0 failures (0% failure rate)
**Improvement**: 100% (5/5 failures fixed)

**By Type**:
- Compilation errors: 2 → 0 (100% improvement)
- Test failures: 2 → 0 (100% improvement)
- Panics: 1 → 0 (100% improvement)

**Success Criteria Met**: ✅
- All tests pass: 150/150 (100%) ✅
- No compilation errors ✅
- No test failures ✅
```

#### 5.5: Mark Work Complete

**Only when**:
- ✅ All tests pass (`cargo make test` exits with code 0)
- ✅ No compilation errors (`cargo make check` succeeds)
- ✅ No test failures
- ✅ No pending test fixes in todo list
- ✅ Improvement measured and verified

**Then**: Mark work as complete

#### 5.6: Establish Controls (DMAIC Control)

**Action**: Set up controls to prevent test failures from returning.

**Controls**:
- **CI/CD**: Run tests automatically on every commit
- **Pre-commit hooks**: Run tests before commits
- **Monitoring**: Track test failure rate over time
- **Alerts**: Set up alerts if failure rate increases

**Action**: Create todo list for controls (10+ items)

```markdown
## Test Verification Control Todos (10+ items)

**CI/CD Controls**:
- [ ] Add CI check: Run all tests on every commit
- [ ] Configure CI to fail if tests fail
- [ ] Add test failure rate tracking to CI
- [ ] Verify CI checks work correctly

**Pre-commit Controls**:
- [ ] Add pre-commit hook: Run tests before commit
- [ ] Configure hook to prevent commit if tests fail
- [ ] Verify pre-commit hooks work correctly
- [ ] Document hook usage

**Monitoring Controls**:
- [ ] Set up test failure rate tracking dashboard
- [ ] Configure alerts if failure rate > 1%
- [ ] Review test failure trends weekly
- [ ] Document failure patterns

**Standards Controls**:
- [ ] Add standard: All tests must pass before commit
- [ ] Add standard: Test failure rate must be < 1%
- [ ] Update team documentation with standards
- [ ] Verify standards are followed
```

**Execution**:
1. Create todos using `todo_write` tool (10+ items minimum)
2. Execute todos one by one (implement controls)
3. Mark todos as completed as controls are implemented
4. Verify each control works before moving to next
5. Continue until all controls implemented

**Principle**: Implement controls to prevent test failures, don't just document them. Todos track progress, controls prevent recurrence.

---

## Advanced: Running Specific Test Suites

### Run Unit Tests Only

```bash
cargo make test
```

**Use when**: Quick feedback during development

### Run Example Tests

```bash
cargo make test-integration
```

**Use when**: Verifying example code works

### Run Single-Threaded Tests

```bash
cargo test --test-threads=1
```

**Use when**: 
- Tests are flaky
- Need deterministic execution
- Debugging race conditions

**Note**: This bypasses `cargo make` but may be necessary for debugging. Prefer `cargo make test` for normal operations.

---

## Failure Pattern Reference

### Compilation Errors

**Pattern**: `error[E...]: <description>`

**Example**:
```
error[E0425]: cannot find function `test_function` in this scope
  --> src/test.rs:10:5
   |
10 |     test_function();
   |     ^^^^^^^^^^^^ not found in this scope
```

**Fix**: Add missing function or import

### Test Failures

**Pattern**: `test test_name ... FAILED`

**Example**:
```
test test_fixture_creation ... FAILED

---- test_fixture_creation stdout ----
thread 'test_fixture_creation' panicked at 'assertion failed: `(left == right)`
  left: `0`,
 right: `1`', src/fixture.rs:123:5
```

**Fix**: Review assertion, fix test or implementation

### Panics

**Pattern**: `thread 'test_name' panicked`

**Example**:
```
thread 'test_builder' panicked at 'called `Result::unwrap()` on an `Err` value: "error"', src/builders.rs:45:23
```

**Fix**: Replace `unwrap()` with proper error handling

### Timeouts

**Pattern**: `test test_name ... timeout`

**Example**:
```
test test_slow_operation ... timeout
```

**Fix**: Optimize code or increase timeout (but remember: entire suite must complete in <1s)

---

## Complete Workflow Example

```bash
# Step 1: Run Tests
cargo make test
# Output: 2 tests failed

# Step 2: Analyze Results
# Found:
# - test_fixture_creation: FAILED - assertion failed
# - test_builder: FAILED - panic on unwrap()

# Step 3: Fix Failures
# Fix test_fixture_creation: Update expected value
# Fix test_builder: Replace unwrap() with proper handling

# Step 4: Re-Run Tests
cargo make test
# All tests pass ✅

# Step 5: Verify Completion
cargo make check  # Compilation OK
cargo make test   # All tests pass
# No pending test fixes in todo list
# Mark work complete ✅
```

## Error Handling

### If Tests Fail Repeatedly

**After 3 attempts**:
- Document issue in todo list
- Create detailed failure report
- Consider if test is correct
- Ask for help if stuck

### If Tests Are Flaky

**Action**:
- Add to todo list: "Fix flaky test: `test_name`"
- Use `cargo test --test-threads=1` for deterministic execution
- Review test isolation
- Check for race conditions

### If Compilation Errors Persist

**Action**:
- Review error messages carefully
- Check feature flags
- Verify dependencies
- Consider if architecture change needed

## Best Practices

1. **Run tests frequently** - Don't wait until the end
2. **Fix immediately** - Address failures as they occur
3. **One fix at a time** - Fix and verify each issue separately
4. **Verify after fixes** - Always re-run tests after fixes
5. **Document failures** - Add to todo list if not immediately fixable
6. **Never skip validation** - All tests must pass before completion
7. **Test performance** - Entire suite must complete in <1 second

## Documentation References

- **[Core Team Best Practices](../.cursorrules)** - Project-specific rules and standards
- **[Expert Testing Patterns](./expert-testing-patterns.md)** - Expert patterns
- **[ACP Command](./acp.md)** - Git workflow integration
- **[Makefile.toml](../../Makefile.toml)** - Build system configuration

## Quick Reference

```bash
# Full workflow
cargo make test                    # Step 1: Run tests
# Analyze failures                 # Step 2: Analyze
# Fix failures                     # Step 3: Fix
cargo make test                    # Step 4: Re-run
cargo make check                   # Step 5: Verify compilation
# Mark complete                    # Step 5: Verify completion
```

