# Removing Mocking Violations - Action Plan

## Overview

This document outlines the systematic plan to remove all 60 mocking violations detected in the test suite and migrate to factory_boy factories for Chicago School TDD compliance.

## Current Status

**Total Violations:** 60 mocking violations detected
- 22 `unittest.mock` imports
- 20 `MagicMock()`/`Mock()` calls
- 18 `patch()` calls
- 20 custom `Mock*` classes

## Migration Strategy

### Phase 1: High-Impact Files (Priority Order)

#### 1. `tests/codegen/test_dspy_config.py` (20 violations)
**Status:** Highest priority - most violations

**Actions:**
- Remove `from unittest.mock import MagicMock, patch`
- Replace all `MagicMock()` calls with real dspy configuration objects
- Replace `patch("kgcl.codegen.dspy_config.dspy")` with real dspy instances
- Use real `dspy.settings.lm` instead of mocked language models

**Estimated Effort:** 2-3 hours
**Dependencies:** May need to create dspy configuration factories if dspy objects are domain objects

#### 2. `tests/hybrid/temporal/test_temporal_orchestrator.py` (6 violations)
**Status:** High priority - domain object mocking

**Actions:**
- Remove `from unittest.mock import MagicMock, Mock`
- Replace `MockPhysicsResult` with real physics result objects
- Replace `MockTickOutcome` with real tick outcome objects
- Replace `MockHybridOrchestrator` with real `HybridOrchestrator` instances
- Replace `Mock()` return with real objects

**Estimated Effort:** 1-2 hours
**Dependencies:** May need to create factories for physics results and tick outcomes

#### 3. `tests/hybrid/temporal/test_event_capture.py` (4 violations)
**Status:** High priority - domain object mocking

**Actions:**
- Replace `MockEngine` with real `HybridOrchestrator` or `HybridEngine`
- Replace `MockRule` with real rule objects (if rules are domain objects)
- Replace `MockStore` with real PyOxigraph stores

**Estimated Effort:** 1 hour
**Dependencies:** None - can use real stores and engines

#### 4. YAWL Client Tests (Multiple files, ~10 violations)
**Status:** Medium priority - infrastructure mocking (may be acceptable)

**Files:**
- `tests/yawl_ui/clients/test_engine_client.py`
- `tests/yawl_ui/clients/test_worklet_client.py`
- `tests/yawl_ui/clients/test_resource_client.py`
- `tests/yawl_ui/clients/test_docstore_client.py`
- `tests/yawl/clients/test_interface_b_client.py`

**Actions:**
- Evaluate if `MockResponse` is infrastructure (HTTP responses) or domain object
- If infrastructure: Add `# pragma: allowlist mock` comments with justification
- If domain: Replace with real response objects or factories

**Estimated Effort:** 2-3 hours
**Dependencies:** Decision on whether HTTP responses are infrastructure

#### 5. YAWL Test Files (4 violations)
**Status:** Low priority - test utilities

**Files:**
- `tests/yawl/test_ytask_methods.py` (2 `MockHandler` classes)
- `tests/yawl/test_yvariable_methods.py` (2 `MockHandler` classes)

**Actions:**
- Replace `MockHandler` with real handler implementations
- Or create handler factories if handlers are domain objects

**Estimated Effort:** 1 hour
**Dependencies:** Understanding handler interface

### Phase 2: Create Missing Factories

If needed, create additional factories for:

1. **DSPY Configuration Objects** (if domain objects)
   - `DspyConfigFactory`
   - `LanguageModelFactory`

2. **Physics/Tick Objects** (if domain objects)
   - `PhysicsResultFactory`
   - `TickOutcomeFactory`

3. **Rule Objects** (if domain objects)
   - `RuleFactory`

4. **Handler Objects** (if domain objects)
   - `HandlerFactory`

### Phase 3: Infrastructure Mocking Policy

**Decision Required:** Which mocks are acceptable?

**Infrastructure (Acceptable with pragma):**
- HTTP client responses (`MockResponse` for httpx/requests)
- File system operations
- Database connections
- External service clients

**Domain Objects (Never acceptable):**
- `Hook`, `HookReceipt`, `Condition`
- `YCase`, `YWorkItem`, `YTask`
- `Receipt`, `ChainAnchor`
- Any business logic objects

**Action:** Document policy in `.cursorrules` and add pragma comments where infrastructure mocking is needed.

## Step-by-Step Migration Process

### For Each File:

1. **Analyze the Mock**
   ```python
   # Is this infrastructure or domain?
   # Infrastructure: HTTP, files, DB, external services → Add pragma
   # Domain: Business logic → Replace with factory
   ```

2. **If Domain Object:**
   ```python
   # Before:
   from unittest.mock import MagicMock
   hook = MagicMock()
   hook.name = "test-hook"
   
   # After:
   from tests.factories import HookFactory
   hook = HookFactory(name="test-hook")
   ```

3. **If Infrastructure:**
   ```python
   # Before:
   from unittest.mock import Mock
   response = Mock()
   
   # After:
   from unittest.mock import Mock  # pragma: allowlist mock
   # Justification: HTTP response is infrastructure, not domain
   response = Mock()
   ```

4. **Update Test Logic**
   - Remove mock assertions (`assert_called_once`, etc.)
   - Add real behavior assertions
   - Verify actual object state

5. **Run Tests**
   ```bash
   uv run poe test tests/path/to/test_file.py
   ```

6. **Verify No Violations**
   ```bash
   uv run python scripts/detect_implementation_lies.py tests/path/to/test_file.py
   ```

## Verification Checklist

After migration, verify:

- [ ] No `unittest.mock` imports (except with pragma)
- [ ] No `MagicMock()`, `Mock()`, `patch()` calls (except with pragma)
- [ ] No `Mock*` class definitions (except with pragma)
- [ ] All tests pass with real objects
- [ ] Test execution time is acceptable
- [ ] Test coverage maintained or improved

## Testing the Migration

### Run Full Test Suite
```bash
uv run poe test
```

### Check for Remaining Violations
```bash
uv run python scripts/detect_implementation_lies.py tests/ --warnings-as-errors
```

### Verify Specific File
```bash
uv run python scripts/detect_implementation_lies.py tests/codegen/test_dspy_config.py
```

## Timeline Estimate

- **Phase 1 (High Priority):** 6-8 hours
- **Phase 2 (Missing Factories):** 2-4 hours (if needed)
- **Phase 3 (Policy & Documentation):** 1-2 hours
- **Total:** 9-14 hours

## Success Criteria

1. ✅ Zero mocking violations in test files (except infrastructure with pragma)
2. ✅ All tests pass with real objects
3. ✅ Test execution time < 5 seconds (unit tests)
4. ✅ Documentation updated with policy
5. ✅ All developers aware of Chicago TDD mocking policy

## Resources

- [Migration Guide](migrate-from-mocks-to-factories.md)
- [Factory Documentation](../../tests/factories/__init__.py)
- [Chicago TDD Checklist](chicago-tdd-checklist.md)
- [Implementation Lies Detector](../../scripts/detect_implementation_lies.py)

