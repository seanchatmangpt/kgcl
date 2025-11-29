# Code Validation System

## Overview

The code validation system ensures all generated code meets KGCL's strict quality standards before being committed to the repository. This is critical for maintaining code quality and preventing defects in generated code.

## Validation Layers

The validator enforces five critical quality checks:

### 1. Syntax Validation
- Uses `ast.parse()` to ensure valid Python syntax
- Fails fast if code cannot be parsed
- Provides line numbers and error context

### 2. Type Checking
- Runs `mypy --strict` on all generated files
- Requires 100% type coverage (no `Any` types)
- All functions must have parameter and return type hints

### 3. Lint Checking
- Runs `ruff check` with all 400+ rules enabled
- Enforces code style and best practices
- Auto-fix available for many issues

### 4. Import Validation
- Checks all imports are resolvable
- Detects and rejects relative imports
- Prevents circular dependencies

### 5. Test Validation
- Runs generated tests with `pytest`
- Requires 80%+ code coverage
- All tests must pass

## Usage

### Command Line

```bash
# Validate single file
poe validate-code path/to/file.py

# Validate directory
poe validate-code src/kgcl/yawl_ui/

# Strict mode (warnings as errors)
poe validate-code-strict path/to/file.py

# Auto-fix issues
poe validate-code-autofix path/to/file.py
```

### Python API

```python
from pathlib import Path
from scripts.codegen.validator import CodeValidator, auto_fix_issues

# Create validator
validator = CodeValidator(strict=False)

# Validate single file
result = validator.validate_python(Path("generated.py"))
if not result.passed:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")

# Validate entire directory
results = validator.validate_all(Path("src/kgcl/yawl_ui"))
for file_path, result in results.items():
    if not result.passed:
        print(f"Failed: {file_path}")

# Auto-fix issues
fixed_result = auto_fix_issues(Path("generated.py"))
```

### Generating Reports

```python
from scripts.codegen.validator import generate_validation_report

results = validator.validate_all(Path("src/kgcl/yawl_ui"))
report = generate_validation_report(results)
print(report)
```

Example output:
```
================================================================================
CODE VALIDATION REPORT
================================================================================
Total Files: 25
Passed: 23 ✓
Failed: 2 ✗

FAILED FILES:
--------------------------------------------------------------------------------

❌ src/kgcl/yawl_ui/models.py
  ERRORS:
    - Type error at line 45: Missing return type annotation
    - Import not resolvable: fake_module

❌ src/kgcl/yawl_ui/handlers.py
  WARNINGS:
    - Line 78: Unused import 'sys'

================================================================================
✗ VALIDATION FAILED - FIX ERRORS BEFORE COMMITTING
================================================================================
```

## Integration with Code Generation

### Recommended Workflow

1. **Generate Code**: Run code generator
2. **Validate Immediately**: Run validator on generated files
3. **Auto-Fix**: Apply auto-fixes where possible
4. **Re-Validate**: Verify all issues resolved
5. **Manual Review**: Address any unfixable issues
6. **Commit**: Only commit after ALL validations pass

### Example Generator Integration

```python
from pathlib import Path
from scripts.codegen.validator import CodeValidator, auto_fix_issues, generate_validation_report

def generate_and_validate():
    # 1. Generate code
    output_dir = Path("src/kgcl/yawl_ui")
    generate_code(output_dir)

    # 2. Validate generated code
    validator = CodeValidator(strict=True)
    results = validator.validate_all(output_dir)

    # 3. Auto-fix issues
    for file_path, result in results.items():
        if not result.passed:
            print(f"Auto-fixing {file_path}...")
            results[file_path] = auto_fix_issues(file_path)

    # 4. Re-validate
    results = validator.validate_all(output_dir)

    # 5. Generate report
    report = generate_validation_report(results)
    print(report)

    # 6. Fail if validation failed
    all_passed = all(r.passed for r in results.values())
    if not all_passed:
        raise RuntimeError("Generated code validation failed")

    return results
```

## Validation Metrics

Each validation result includes metrics:

```python
result = validator.validate_python(Path("file.py"))

# Access metrics
print(result.metrics)
# {
#     "syntax_valid": True,
#     "types_valid": True,
#     "lint_valid": True,
#     "imports_valid": False
# }
```

## Auto-Fix Capabilities

The auto-fix system can automatically resolve:

1. **Code Formatting**: Fixes indentation, spacing, line length
2. **Import Sorting**: Organizes imports according to conventions
3. **Unused Imports**: Removes unused import statements
4. **Trailing Whitespace**: Removes trailing whitespace
5. **Quote Consistency**: Normalizes quote styles

Auto-fix cannot resolve:
- Type annotation issues
- Logic errors
- Missing imports
- Syntax errors

## Strict vs Non-Strict Mode

### Non-Strict Mode (Default)
- Warnings do NOT fail validation
- Suitable for development
- Allows gradual improvement

### Strict Mode
- Warnings FAIL validation
- Required for production
- Zero tolerance for code issues

```python
# Non-strict validator
validator = CodeValidator(strict=False)

# Strict validator (recommended for CI/CD)
validator = CodeValidator(strict=True)
```

## CI/CD Integration

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Validate all Python files in staging area
poe validate-code-strict src/

if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Fix errors before committing."
    exit 1
fi
```

### GitHub Actions

```yaml
name: Validate Generated Code

on:
  pull_request:
    paths:
      - 'src/kgcl/yawl_ui/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Validate generated code
        run: |
          poe validate-code-strict src/kgcl/yawl_ui/
```

## Performance Considerations

### Validation Speed

| Check | Typical Time | Notes |
|-------|-------------|-------|
| Syntax | <1s per file | Very fast (AST parsing) |
| Types | 2-5s per file | Slowest check (mypy) |
| Lint | 1-2s per file | Fast with caching |
| Imports | <1s per file | Fast (module specs) |

### Optimization Tips

1. **Parallel Validation**: Validate multiple files concurrently
2. **Incremental Validation**: Only validate changed files
3. **Cache Results**: Cache validation results by file hash
4. **Skip Tests**: Use `--skip-tests` flag for faster validation

## Troubleshooting

### Common Issues

**Issue**: "Import not resolvable" for valid import
**Solution**: Ensure module is installed: `uv sync`

**Issue**: Type errors in generated code
**Solution**: Ensure generator produces fully-typed code

**Issue**: Validation timeout
**Solution**: Increase timeout or validate in smaller batches

### Debug Mode

```bash
# Run validator with verbose output
uv run python scripts/codegen/validator.py --verbose path/to/file.py
```

## Best Practices

1. **Validate Early**: Run validator immediately after code generation
2. **Auto-Fix First**: Always attempt auto-fix before manual intervention
3. **Strict in CI**: Use strict mode in CI/CD pipelines
4. **Track Metrics**: Monitor validation metrics over time
5. **Zero Tolerance**: Never commit code with validation errors

## Examples

### Validate YAWL UI Code

```bash
# After generating YAWL UI code
poe codegen-yawl-ui

# Validate generated code
poe validate-code-autofix src/kgcl/yawl_ui/

# Check results
poe validate-code-strict src/kgcl/yawl_ui/
```

### Validate in Test Suite

```python
import pytest
from pathlib import Path
from scripts.codegen.validator import CodeValidator

def test_generated_code_quality():
    """Ensure generated code meets quality standards."""
    validator = CodeValidator(strict=True)
    results = validator.validate_all(Path("src/kgcl/yawl_ui"))

    # All files must pass
    failures = {path: result for path, result in results.items() if not result.passed}
    assert len(failures) == 0, f"Validation failed: {failures}"
```

## Future Enhancements

Planned improvements:
- [ ] Parallel validation for faster processing
- [ ] Caching of validation results
- [ ] Custom rule configuration
- [ ] HTML validation reports
- [ ] Integration with IDE plugins
- [ ] Security scanning (Bandit integration)
- [ ] Complexity analysis
- [ ] Dependency graph validation
