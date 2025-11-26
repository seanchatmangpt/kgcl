#!/usr/bin/env python3
"""Bulk add type annotations to Python files using AST.

This script uses Python's AST to safely add type annotations:
1. Adds `-> None` to functions with no return statement
2. Adds `: Any` to untyped function parameters (not self/cls)
3. Adds missing `from typing import Any` imports

Usage:
    python scripts/bulk_add_types.py src/kgcl/
    python scripts/bulk_add_types.py src/kgcl/hooks/loader.py  # single file
    python scripts/bulk_add_types.py src/kgcl/ --dry-run
"""

import ast
import sys
from pathlib import Path


def has_return_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function has a return statement with a value."""
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and child.value is not None:
            return True
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def get_function_info(tree: ast.AST) -> list[dict]:
    """Extract function info: name, line, params needing types, needs return."""
    functions = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Determine return type needed
        has_return = has_return_value(node)
        needs_return_type = node.returns is None
        return_type = "Any" if has_return else "None"

        info = {
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "col_offset": node.col_offset,
            "needs_return": needs_return_type,
            "return_type": return_type,
            "untyped_params": [],
        }

        # Check all parameter types
        all_args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs

        for arg in all_args:
            if arg.annotation is None and arg.arg not in ("self", "cls"):
                info["untyped_params"].append({"name": arg.arg, "lineno": arg.lineno, "col_offset": arg.col_offset})

        # Check *args and **kwargs
        if node.args.vararg and node.args.vararg.annotation is None:
            info["untyped_params"].append(
                {
                    "name": f"*{node.args.vararg.arg}",
                    "lineno": node.args.vararg.lineno,
                    "col_offset": node.args.vararg.col_offset,
                }
            )
        if node.args.kwarg and node.args.kwarg.annotation is None:
            info["untyped_params"].append(
                {
                    "name": f"**{node.args.kwarg.arg}",
                    "lineno": node.args.kwarg.lineno,
                    "col_offset": node.args.kwarg.col_offset,
                }
            )

        if info["needs_return"] or info["untyped_params"]:
            functions.append(info)

    return functions


def add_return_type(lines: list[str], func_lineno: int, return_type: str = "None") -> bool:
    """Add -> <return_type> to a function definition. Returns True if modified."""
    # Find the line(s) with the function signature ending in :
    idx = func_lineno - 1

    # Accumulate lines until we find the closing :
    start_idx = idx
    signature = ""
    while idx < len(lines):
        signature += lines[idx]
        if signature.rstrip().endswith(":"):
            break
        idx += 1

    end_idx = idx

    # Check if already has ->
    if " -> " in signature:
        return False

    # Find the colon position in the last line
    line = lines[end_idx]

    # Verify it's actually a colon
    stripped = line.rstrip()
    if not stripped.endswith(":"):
        return False

    # Insert " -> <return_type>" before the :
    lines[end_idx] = stripped[:-1] + f" -> {return_type}:"
    if line.endswith("\n"):
        lines[end_idx] += "\n"

    return True


def add_param_type(lines: list[str], param_name: str, param_lineno: int) -> bool:
    """Add : Any to a parameter. Returns True if modified."""
    idx = param_lineno - 1
    if idx >= len(lines):
        return False

    line = lines[idx]

    # Handle *args and **kwargs
    search_name = param_name.lstrip("*")
    prefix = param_name[: len(param_name) - len(search_name)]

    # Find the parameter in the line
    # Look for patterns like:
    # - `name,` -> `name: Any,`
    # - `name)` -> `name: Any)`
    # - `name=` -> `name: Any =`
    # - `*name,` -> `*name: Any,`
    # - `**name)` -> `**name: Any)`

    import re

    # Pattern to match the parameter (with optional * or **)
    # Followed by , or ) or = but NOT : (already typed)
    pattern = rf"(\b{re.escape(prefix)}{re.escape(search_name)})(\s*[,)=])"

    def replacer(m):
        name_part = m.group(1)
        suffix = m.group(2).strip()

        if suffix == "=":
            return f"{name_part}: Any ="
        else:
            return f"{name_part}: Any{suffix}"

    # Check if already has type annotation
    check_pattern = rf"\b{re.escape(prefix)}{re.escape(search_name)}\s*:"
    if re.search(check_pattern, line):
        return False

    new_line, count = re.subn(pattern, replacer, line, count=1)

    if count > 0:
        lines[idx] = new_line
        return True

    return False


def ensure_any_import(lines: list[str]) -> bool:
    """Add 'from typing import Any' if not present. Returns True if added."""
    source = "\n".join(lines)

    # Check if Any is already imported
    if "from typing import" in source:
        # Check if Any is in that import
        for i, line in enumerate(lines):
            if line.strip().startswith("from typing import"):
                if "Any" in line:
                    return False
                # Add Any to existing import
                if line.rstrip().endswith(")"):
                    # Multi-line import ending
                    lines[i] = line.rstrip()[:-1] + ", Any)\n"
                else:
                    lines[i] = line.rstrip() + ", Any\n"
                return True

    if "import typing" in source:
        return False  # Can use typing.Any

    # Find where to insert the import
    insert_idx = 0
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) == 1:
                    in_docstring = True
                insert_idx = i + 1
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
                insert_idx = i + 1
            continue

        # Skip comments
        if stripped.startswith("#"):
            insert_idx = i + 1
            continue

        # After __future__ imports
        if stripped.startswith("from __future__"):
            insert_idx = i + 1
            continue

        # Found first real import or code
        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_idx = i
            break
        elif stripped and not stripped.startswith("#"):
            break

    lines.insert(insert_idx, "from typing import Any\n")
    return True


def process_file(filepath: Path, dry_run: bool = False) -> tuple[bool, int]:
    """Process a single file. Returns (changed, num_fixes)."""
    try:
        source = filepath.read_text()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return False, 0

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  Syntax error in {filepath}: {e}")
        return False, 0

    functions = get_function_info(tree)
    if not functions:
        return False, 0

    lines = source.splitlines(keepends=True)
    # Ensure last line has newline for consistency
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    fixes = 0
    needs_any_import = False

    # Process in reverse order to preserve line numbers
    for func in reversed(functions):
        # Add return type
        if func["needs_return"]:
            if add_return_type(lines, func["lineno"]):
                fixes += 1

        # Add parameter types (in reverse order within function)
        for param in reversed(func["untyped_params"]):
            if add_param_type(lines, param["name"], param["lineno"]):
                fixes += 1
                needs_any_import = True

    if fixes == 0:
        return False, 0

    # Add Any import if needed
    if needs_any_import:
        if ensure_any_import(lines):
            fixes += 1

    new_source = "".join(lines)

    if new_source == source:
        return False, 0

    if dry_run:
        print(f"  Would modify: {filepath} ({fixes} fixes)")
    else:
        filepath.write_text(new_source)
        print(f"  Modified: {filepath} ({fixes} fixes)")

    return True, fixes


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.py"))
        # Exclude tests and cache
        files = [f for f in files if "__pycache__" not in str(f) and "/test_" not in str(f) and "/tests/" not in str(f)]

    print(f"Processing {len(files)} files...\n")

    total_modified = 0
    total_fixes = 0

    for filepath in files:
        changed, fixes = process_file(filepath, dry_run)
        if changed:
            total_modified += 1
            total_fixes += fixes

    print(f"\n{'Would modify' if dry_run else 'Modified'}: {total_modified} files")
    print(f"Total fixes: {total_fixes}")

    if not dry_run and total_modified > 0:
        print("\nRun to verify:")
        print("  uv run ruff format src/kgcl/")
        print("  uv run mypy src/kgcl/")


if __name__ == "__main__":
    main()
