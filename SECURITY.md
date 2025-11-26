# Security Guidelines for KGCL

## Security Scanning

KGCL enforces Lean Six Sigma quality standards with comprehensive security scanning as part of the build pipeline.

### Bandit Security Scanner

Bandit is a security linter for Python that identifies common security issues in Python code.

#### Installation

Bandit is an optional development dependency. To install:

```bash
uv add --dev bandit
```

#### Usage

Run Bandit security scans on the source code:

```bash
# Scan all source files
uv run bandit -r src/

# Scan with configuration file (if .bandit exists)
uv run bandit -r src/ -c .bandit

# Generate report in JSON format
uv run bandit -r src/ -f json -o reports/bandit.json

# Scan with severity filter (only show HIGH and MEDIUM issues)
uv run bandit -r src/ -ll
```

#### Integration with CI/CD

Add Bandit to your CI pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Bandit security scan
  run: |
    uv add --dev bandit
    uv run bandit -r src/ -ll
```

#### Common Security Issues Detected

Bandit detects issues including:
- Hardcoded passwords and secrets
- SQL injection vulnerabilities
- Use of unsafe functions (eval, exec, pickle)
- Weak cryptographic practices
- Shell injection vulnerabilities
- Insecure random number generation

### Security Best Practices

1. **Never hardcode secrets**: Use environment variables or secret management tools
2. **Validate all inputs**: Especially for user-provided data and file paths
3. **Use parameterized queries**: Prevent SQL injection
4. **Avoid `eval()` and `exec()`**: Use safer alternatives
5. **Use cryptographically secure random**: `secrets` module, not `random`
6. **Keep dependencies updated**: Regularly update to patch vulnerabilities

### Pre-commit Security Checks

Security checks are enforced via pre-commit hooks:

```bash
# Install hooks (includes Bandit checks)
poe pre-commit-setup

# Run pre-commit checks manually
poe pre-commit-run
```

The pre-commit hook includes:
- Hardcoded secrets detection
- Bandit security scanning (if installed)
- Type safety verification
- Dependency vulnerability scanning

### Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email security concerns to: security@example.com (update with real contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Security Audit Commands

```bash
# Run comprehensive security audit
poe audit            # pip-audit for dependency vulnerabilities

# Combined security workflow
uv run bandit -r src/ -ll && poe audit
```

## Compliance

KGCL follows Lean Six Sigma security standards with:
- Zero tolerance for hardcoded secrets
- Mandatory security scanning on all commits
- Continuous monitoring for dependency vulnerabilities
- 99.99966% defect-free delivery target

---

**Last Updated**: 2025-11-25
