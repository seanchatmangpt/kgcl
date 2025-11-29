#!/usr/bin/env python3
"""
Implementation Lies Detector - Lean Six Sigma Quality Gate.

This module detects all forms of incomplete, deferred, or placeholder code
that violate Chicago School TDD and Lean Six Sigma zero-defect standards.

The "implementation lies" are patterns that AI coding agents commonly use
to appear to complete work while actually deferring implementation.

Categories of Lies:
1. DEFERRED_WORK - TODO/FIXME/XXX/HACK/WIP comments
2. STUB_PATTERNS - pass, ..., raise NotImplementedError
3. PLACEHOLDER_RETURNS - return None/{}/ []/0/False without logic
4. MOCK_ASSERTIONS - assert True, assert result (meaningless tests)
5. INCOMPLETE_TESTS - tests without assertions or single trivial assert
6. SPECULATIVE_SCAFFOLDING - empty classes, unused imports
7. TEMPORAL_DEFERRAL - # later, # temporary, # for now, # quick fix

Exit codes:
  0 - No lies detected (clean code)
  1 - Lies detected (code has quality issues)
  2 - Error during detection

Usage:
  python scripts/detect_implementation_lies.py src/ tests/
  python scripts/detect_implementation_lies.py --staged  # Check staged files only
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator


class LieCategory(Enum):
    """Categories of implementation lies."""

    DEFERRED_WORK = "deferred_work"
    STUB_PATTERN = "stub_pattern"
    PLACEHOLDER_RETURN = "placeholder_return"
    MOCK_ASSERTION = "mock_assertion"
    INCOMPLETE_TEST = "incomplete_test"
    SPECULATIVE_SCAFFOLDING = "speculative_scaffolding"
    TEMPORAL_DEFERRAL = "temporal_deferral"


@dataclass
class ImplementationLie:
    """Detected implementation lie."""

    file_path: str
    line_number: int
    category: LieCategory
    pattern: str
    code_snippet: str
    severity: str = "ERROR"  # ERROR or WARNING

    def __str__(self) -> str:
        """Format lie for output."""
        return (
            f"{self.file_path}:{self.line_number}: "
            f"[{self.severity}] {self.category.value}: {self.pattern}\n"
            f"    {self.code_snippet.strip()}"
        )


@dataclass
class DetectionResult:
    """Result of lie detection."""

    lies: list[ImplementationLie] = field(default_factory=list)
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any ERROR-level lies were detected."""
        return any(lie.severity == "ERROR" for lie in self.lies)

    @property
    def error_count(self) -> int:
        """Count ERROR-level lies."""
        return sum(1 for lie in self.lies if lie.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        """Count WARNING-level lies."""
        return sum(1 for lie in self.lies if lie.severity == "WARNING")


# =============================================================================
# Pattern Definitions
# =============================================================================

# Category 1: Deferred Work Comments
# NOTE: Patterns require word boundary AFTER keyword to avoid matching "temperature", "template", etc.
# NOTE: TEMP is excluded - too many false positives with "temp file", "temporary", etc.
DEFERRED_WORK_PATTERNS = [
    (r"#.*\bTODO\b", "TODO comment - work deferred"),
    (r"#.*\bFIXME\b", "FIXME comment - known bug deferred"),
    (r"#.*\bXXX\b", "XXX comment - hack/workaround marker"),
    (r"#.*\bHACK\b", "HACK comment - technical debt"),
    (r"#.*\bWIP\b", "WIP comment - incomplete work"),
    (r"#.*\bSTUB\b", "STUB comment - placeholder implementation"),
    (r"#\s*noqa\s*$", "Blanket noqa - suppressing all linting"),
    (r"#\s*type:\s*ignore\s*$", "Blanket type:ignore - suppressing all type checks"),
]

# Category 7: Temporal Deferral Phrases
# NOTE: These patterns are designed to catch work deferral, not legitimate descriptions
# of test data or timing. Patterns use context words to reduce false positives.
TEMPORAL_DEFERRAL_PATTERNS = [
    (r"#.*\bdo later\b", "Deferral: 'do later' - work postponed"),
    (r"#.*\bfix later\b", "Deferral: 'fix later' - bug deferred"),
    (r"#.*\bimplement later\b", "Deferral: 'implement later' - work deferred"),
    (r"#.*\bfor now\b", "Deferral: 'for now' - implies future change"),
    (r"#.*\bquick fix\b", "Deferral: 'quick fix' - not proper solution"),
    (r"#.*\bplaceholder\b", "Deferral: 'placeholder' - not real implementation"),
    (r"#.*\bwork in progress\b", "Deferral: 'work in progress' - incomplete"),
    (r"#.*\bnot yet implemented\b", "Deferral: 'not yet implemented' - missing logic"),
    (r"#.*\bskip for now\b", "Deferral: 'skip for now' - deferred"),
    (r"#.*\bneeds? more work\b", "Deferral: 'needs more work' - incomplete"),
    (r"#.*\bto be done\b", "Deferral: 'to be done' - incomplete"),
    (r"#.*\bincomplete implementation\b", "Deferral: 'incomplete implementation' - not finished"),
    (r"#.*\bneed to refactor\b", "Deferral: 'need to refactor' - quality issue deferred"),
    (r"#.*\bshould refactor\b", "Deferral: 'should refactor' - quality issue deferred"),
]


class ImplementationLiesDetector:
    """Detect implementation lies in Python code."""

    def __init__(self, verbose: bool = False, strict_mode: bool = True) -> None:
        """Initialize detector.

        Args:
            verbose: Enable verbose output
            strict_mode: True = block TODO/FIXME (main branch), False = allow (feature branch)
        """
        self.verbose = verbose
        self.strict_mode = strict_mode
        self._deferred_patterns = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in DEFERRED_WORK_PATTERNS
        ]
        self._temporal_patterns = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in TEMPORAL_DEFERRAL_PATTERNS
        ]

    def detect_in_file(self, file_path: Path) -> list[ImplementationLie]:
        """Detect all lies in a single file."""
        lies: list[ImplementationLie] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
        except Exception as e:
            if self.verbose:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)
            return lies

        # Line-by-line pattern checks
        for i, line in enumerate(lines, start=1):
            lies.extend(self._check_line_patterns(file_path, i, line))

        # AST-based checks
        try:
            tree = ast.parse(content, filename=str(file_path))
            lies.extend(self._check_ast_patterns(file_path, tree, lines))
        except SyntaxError:
            # If file has syntax errors, skip AST analysis
            pass

        return lies

    def _check_line_patterns(
        self, file_path: Path, line_num: int, line: str
    ) -> list[ImplementationLie]:
        """Check line for pattern-based lies."""
        lies = []

        # Skip pragma allowlist
        if "pragma: allowlist" in line.lower():
            return lies

        # Category 1: Deferred work comments (BRANCH-AWARE)
        # On feature branches: TODO/FIXME/WIP allowed (work in progress)
        # On main/master: BLOCKED (zero-defect quality gate)
        if self.strict_mode:  # main/master branch - strict enforcement
            for pattern, message in self._deferred_patterns:
                if pattern.search(line):
                    lies.append(
                        ImplementationLie(
                            file_path=str(file_path),
                            line_number=line_num,
                            category=LieCategory.DEFERRED_WORK,
                            pattern=message,
                            code_snippet=line,
                            severity="ERROR",
                        )
                    )
                    break  # One match per line for this category
        # else: feature branch - TODO/FIXME/WIP allowed for WIP

        # Category 7: Temporal deferral phrases (BRANCH-AWARE)
        if self.strict_mode:  # main/master branch - strict enforcement
            for pattern, message in self._temporal_patterns:
                if pattern.search(line):
                    lies.append(
                        ImplementationLie(
                            file_path=str(file_path),
                            line_number=line_num,
                            category=LieCategory.TEMPORAL_DEFERRAL,
                            pattern=message,
                            code_snippet=line,
                            severity="ERROR",
                        )
                    )
                    break  # One match per line for this category
        # else: feature branch - temporal deferral allowed for WIP

        return lies

    def _check_ast_patterns(
        self, file_path: Path, tree: ast.AST, lines: list[str]
    ) -> list[ImplementationLie]:
        """Check AST for structural lies."""
        lies = []
        is_test_file = "test_" in file_path.name or file_path.name.startswith("test")

        for node in ast.walk(tree):
            # Category 2: Stub patterns in functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lies.extend(
                    self._check_stub_function(file_path, node, lines, is_test_file)
                )

            # Category 5: Incomplete tests
            if is_test_file and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    lies.extend(self._check_incomplete_test(file_path, node, lines))

            # Category 6: Empty classes (speculative scaffolding)
            if isinstance(node, ast.ClassDef):
                lies.extend(self._check_empty_class(file_path, node, lines))

        return lies

    def _check_stub_function(
        self,
        file_path: Path,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
        is_test_file: bool,
    ) -> list[ImplementationLie]:
        """Check function for stub patterns."""
        lies = []

        # Skip dunder methods, property getters, fixtures
        if node.name.startswith("__") and node.name.endswith("__"):
            return lies
        if any(
            isinstance(d, ast.Name) and d.id in ("property", "staticmethod", "classmethod", "pytest")
            for d in node.decorator_list
        ):
            return lies
        if any(
            isinstance(d, ast.Attribute) and d.attr == "fixture"
            for d in node.decorator_list
        ):
            return lies

        body = node.body

        # Check for single-statement stub bodies
        if len(body) == 1:
            stmt = body[0]
            line_content = lines[node.lineno - 1] if node.lineno <= len(lines) else ""

            # pass statement
            if isinstance(stmt, ast.Pass):
                lies.append(
                    ImplementationLie(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        category=LieCategory.STUB_PATTERN,
                        pattern=f"Function '{node.name}' has only 'pass' - stub implementation",
                        code_snippet=line_content,
                        severity="ERROR",
                    )
                )

            # Ellipsis (...)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                if stmt.value.value is ...:
                    lies.append(
                        ImplementationLie(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            category=LieCategory.STUB_PATTERN,
                            pattern=f"Function '{node.name}' has only '...' - stub implementation",
                            code_snippet=line_content,
                            severity="ERROR",
                        )
                    )

            # raise NotImplementedError
            elif isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name):
                        if stmt.exc.func.id == "NotImplementedError":
                            lies.append(
                                ImplementationLie(
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    category=LieCategory.STUB_PATTERN,
                                    pattern=f"Function '{node.name}' raises NotImplementedError - stub",
                                    code_snippet=line_content,
                                    severity="ERROR",
                                )
                            )

        # Check for placeholder returns in non-test functions
        if not is_test_file and not node.name.startswith("test_"):
            lies.extend(self._check_placeholder_return(file_path, node, lines))

        return lies

    def _check_placeholder_return(
        self,
        file_path: Path,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
    ) -> list[ImplementationLie]:
        """Check for suspicious placeholder returns."""
        lies = []

        # Skip property getters, __init__, __str__, etc.
        if node.name.startswith("__"):
            return lies

        # Skip if function has substantial body (more than just return)
        if len(node.body) > 2:
            return lies

        # Check for immediate placeholder returns
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                # return None with no other logic
                if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                    if len(node.body) == 1:
                        line = lines[stmt.lineno - 1] if stmt.lineno <= len(lines) else ""
                        lies.append(
                            ImplementationLie(
                                file_path=str(file_path),
                                line_number=stmt.lineno,
                                category=LieCategory.PLACEHOLDER_RETURN,
                                pattern=f"Function '{node.name}' returns None without logic",
                                code_snippet=line,
                                severity="WARNING",
                            )
                        )

                # return {} or [] immediately
                if isinstance(stmt.value, (ast.Dict, ast.List)):
                    if not stmt.value.keys if isinstance(stmt.value, ast.Dict) else not stmt.value.elts:
                        if len(node.body) == 1:
                            line = lines[stmt.lineno - 1] if stmt.lineno <= len(lines) else ""
                            lies.append(
                                ImplementationLie(
                                    file_path=str(file_path),
                                    line_number=stmt.lineno,
                                    category=LieCategory.PLACEHOLDER_RETURN,
                                    pattern=f"Function '{node.name}' returns empty container without logic",
                                    code_snippet=line,
                                    severity="WARNING",
                                )
                            )

        return lies

    def _check_incomplete_test(
        self,
        file_path: Path,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
    ) -> list[ImplementationLie]:
        """Check test function for completeness."""
        lies = []
        line_content = lines[node.lineno - 1] if node.lineno <= len(lines) else ""

        # Check for assertions
        assertion_count = 0
        meaningful_assertions = 0

        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                assertion_count += 1
                # Check if assertion is meaningful
                if isinstance(child.test, ast.Compare):
                    meaningful_assertions += 1
                elif isinstance(child.test, ast.Call):
                    meaningful_assertions += 1
                elif isinstance(child.test, ast.Constant):
                    # assert True, assert False are not meaningful
                    if child.test.value in (True, False):
                        lies.append(
                            ImplementationLie(
                                file_path=str(file_path),
                                line_number=child.lineno,
                                category=LieCategory.MOCK_ASSERTION,
                                pattern="assert True/False - meaningless assertion",
                                code_snippet=lines[child.lineno - 1]
                                if child.lineno <= len(lines)
                                else "",
                                severity="ERROR",
                            )
                        )
                elif isinstance(child.test, ast.Name):
                    # assert result (just checking truthy, often meaningless)
                    if child.test.id in ("result", "response", "output", "data", "ret", "rv"):
                        lies.append(
                            ImplementationLie(
                                file_path=str(file_path),
                                line_number=child.lineno,
                                category=LieCategory.MOCK_ASSERTION,
                                pattern=f"assert {child.test.id} - likely meaningless truthy check",
                                code_snippet=lines[child.lineno - 1]
                                if child.lineno <= len(lines)
                                else "",
                                severity="WARNING",
                            )
                        )
                    else:
                        meaningful_assertions += 1

        # Check for pytest.raises or similar patterns
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr in ("raises", "warns", "deprecated_call"):
                        meaningful_assertions += 1

        # No assertions at all
        if assertion_count == 0 and meaningful_assertions == 0:
            # Check if body is just pass or docstring
            effective_body = [
                s for s in node.body
                if not isinstance(s, ast.Pass)
                and not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
            ]
            if len(effective_body) == 0:
                lies.append(
                    ImplementationLie(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        category=LieCategory.INCOMPLETE_TEST,
                        pattern=f"Test '{node.name}' has no assertions and no implementation",
                        code_snippet=line_content,
                        severity="ERROR",
                    )
                )

        return lies

    def _check_empty_class(
        self, file_path: Path, node: ast.ClassDef, lines: list[str]
    ) -> list[ImplementationLie]:
        """Check for empty/speculative classes."""
        lies = []

        # Check if class body is just pass or docstring
        effective_body = [
            s for s in node.body
            if not isinstance(s, ast.Pass)
            and not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
        ]

        if len(effective_body) == 0:
            line_content = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
            lies.append(
                ImplementationLie(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    category=LieCategory.SPECULATIVE_SCAFFOLDING,
                    pattern=f"Class '{node.name}' is empty - speculative scaffolding",
                    code_snippet=line_content,
                    severity="WARNING",
                )
            )

        return lies

    def detect_in_directory(self, directory: Path, exclude_patterns: list[str] | None = None) -> DetectionResult:
        """Detect lies in all Python files in directory."""
        result = DetectionResult()
        exclude = exclude_patterns or ["__pycache__", ".git", "vendors", ".mypy_cache"]

        for py_file in self._iter_python_files(directory, exclude):
            result.files_scanned += 1
            lies = self.detect_in_file(py_file)
            result.lies.extend(lies)

        return result

    def detect_in_files(self, files: list[Path]) -> DetectionResult:
        """Detect lies in specific files."""
        result = DetectionResult()

        for file_path in files:
            if file_path.suffix == ".py" and file_path.exists():
                result.files_scanned += 1
                lies = self.detect_in_file(file_path)
                result.lies.extend(lies)

        return result

    def _iter_python_files(
        self, directory: Path, exclude: list[str]
    ) -> Iterator[Path]:
        """Iterate Python files in directory, excluding patterns."""
        for path in directory.rglob("*.py"):
            if any(excl in str(path) for excl in exclude):
                continue
            yield path


def is_main_branch() -> bool:
    """Check if current branch is main/master (strict mode).

    Returns:
        True if on main/master branch, False otherwise (feature branch).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch in ("main", "master")
    except subprocess.CalledProcessError:
        # If not in git repo or error, default to strict mode (safe)
        return True


def get_staged_files() -> list[Path]:
    """Get list of staged Python files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [
            Path(f.strip())
            for f in result.stdout.splitlines()
            if f.strip().endswith(".py")
        ]
        return files
    except subprocess.CalledProcessError:
        return []


def main() -> int:
    """Run implementation lies detection."""
    parser = argparse.ArgumentParser(
        description="Detect implementation lies in Python code"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Paths to scan (files or directories)",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan only staged git files",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Treat warnings as errors (exit 1 on warnings)",
    )

    args = parser.parse_args()

    # Branch-aware validation: strict on main/master, relaxed on feature branches
    strict_mode = is_main_branch()
    branch_mode = "STRICT (main/master)" if strict_mode else "RELAXED (feature branch)"

    detector = ImplementationLiesDetector(verbose=args.verbose, strict_mode=strict_mode)

    if args.staged:
        files = get_staged_files()
        if not files:
            print("No staged Python files to check.")
            return 0
        result = detector.detect_in_files(files)
    elif args.paths:
        result = DetectionResult()
        for path in args.paths:
            if path.is_file():
                result.files_scanned += 1
                result.lies.extend(detector.detect_in_file(path))
            elif path.is_dir():
                dir_result = detector.detect_in_directory(path)
                result.files_scanned += dir_result.files_scanned
                result.lies.extend(dir_result.lies)
    else:
        # Default: scan src/ and tests/
        result = DetectionResult()
        for default_dir in [Path("src"), Path("tests")]:
            if default_dir.exists():
                dir_result = detector.detect_in_directory(default_dir)
                result.files_scanned += dir_result.files_scanned
                result.lies.extend(dir_result.lies)

    # Output results
    print("=" * 70)
    print("IMPLEMENTATION LIES DETECTOR - Lean Six Sigma Quality Gate")
    print("=" * 70)
    print(f"Mode: {branch_mode}")
    print(f"Files scanned: {result.files_scanned}")
    print()

    if result.lies:
        # Group by category
        by_category: dict[LieCategory, list[ImplementationLie]] = {}
        for lie in result.lies:
            by_category.setdefault(lie.category, []).append(lie)

        for category, lies in sorted(by_category.items(), key=lambda x: x[0].value):
            print(f"\n[{category.value.upper()}] ({len(lies)} issues)")
            print("-" * 50)
            for lie in lies:
                print(lie)
                print()

        print("=" * 70)
        print(f"TOTAL: {len(result.lies)} implementation lies detected")
        print(f"  ERRORS:   {result.error_count}")
        print(f"  WARNINGS: {result.warning_count}")
        print("=" * 70)

        if result.has_errors or (args.warnings_as_errors and result.warning_count > 0):
            print("\n❌ ANDON CORD PULLED - Quality gate failed")
            print("\nLean Six Sigma Standards (ZERO TOLERANCE):")
            print("  • No TODO/FIXME/XXX/HACK/WIP comments")
            print("  • No stub implementations (pass, ..., NotImplementedError)")
            print("  • No placeholder returns without logic")
            print("  • No meaningless test assertions (assert True)")
            print("  • No empty classes or speculative scaffolding")
            print("  • No temporal deferral phrases ('later', 'for now', 'temporary')")
            print("\nChicago School TDD requires COMPLETE implementations.")
            print("Fix all issues before committing.")
            return 1
    else:
        print("\n✓ No implementation lies detected")
        print("  Code meets Lean Six Sigma zero-defect standards")
        return 0


if __name__ == "__main__":
    sys.exit(main())
