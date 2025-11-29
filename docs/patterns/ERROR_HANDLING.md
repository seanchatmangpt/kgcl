# Error Handling Patterns

**Philosophy**: Research library, not production system. SHACL validates at ingress; internal code trusts data.

## Python Anti-Patterns (Crash Risks)

### ❌ FORBIDDEN in Production Code (`src/`)

These patterns crash like Rust's `unwrap()` - blocked by pre-commit:

```python
# 1. Assert without message (crashes on False)
assert condition
assert x is not None

# 2. Bare indexing (IndexError if out of bounds)
result = items[0]
value = dict["key"]

# 3. Unchecked type conversions (ValueError on invalid input)
num = int(user_input)
date = datetime.strptime(value, "%Y-%m-%d")

# 4. Unchecked cast (type lie, no runtime check)
from typing import cast
value = cast(ComplexType, data)
```

### ✅ SAFE ALTERNATIVES

```python
# 1. Explicit error with message
if not condition:
    raise ValueError(f"Expected {expected}, got {actual}")

if x is None:
    raise TypeError("x must not be None")

# 2. Safe access with bounds checking
result = items[0] if items else default_value
value = dict.get("key", default_value)

# 3. Explicit error handling
try:
    num = int(user_input)
except ValueError as e:
    raise ValueError(f"Invalid number: {user_input}") from e

# 4. Cast with justification comment
from typing import cast
# SHACL validates ComplexType at ingress - safe to cast here
value = cast(ComplexType, data)
```

## When Bare Assert is Allowed

**Tests only** (`tests/` directory):

```python
# ✅ Allowed in tests - specific assertions
assert len(tokens) == 3
assert "error" in result.message
assert isinstance(output, WorkflowCase)

# ❌ NEVER - meaningless assertions
assert True
assert result  # What does this prove?
```

## SHACL-Validated Data

Since this is a research library with SHACL validation at ingress:

```python
# ✅ Safe - data validated by SHACL at ingress
def process_validated_case(case: WorkflowCase) -> Result:
    # No defensive null checks needed - SHACL guarantees structure
    case_id = case.id  # SHACL ensures id exists
    spec = case.specification  # SHACL ensures spec exists
    return execute_workflow(case_id, spec)
```

**Key principle**: Validate once (SHACL at ingress), trust internally.

## Error Categories

| Pattern | Severity | Detection | Mitigation |
|---------|----------|-----------|------------|
| `assert x` | Critical | Pre-commit blocks | Use `if not x: raise ValueError()` |
| `x[0]` | High | Pre-commit blocks | Use `x[0] if x else default` |
| `dict["key"]` | High | Pre-commit blocks | Use `dict.get("key", default)` |
| `cast()` without comment | Medium | Manual review | Add justification comment |

## References

- FMEA.md - Risk analysis and RPN tracking
- TYPE_SAFETY.md - Type safety patterns
- SHACL validation - See `docs/architecture/SHACL_INGRESS.md`
