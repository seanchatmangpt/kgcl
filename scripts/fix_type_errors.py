#!/usr/bin/env python3
"""Script to systematically fix type errors across the codebase."""

import re
from pathlib import Path


def fix_file(file_path: Path, patterns: list[tuple[str, str]]) -> int:
    """Apply regex patterns to fix type errors in a file."""
    content = file_path.read_text()
    original = content
    fixes_applied = 0

    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            fixes_applied += 1
            content = new_content

    if content != original:
        file_path.write_text(content)
        return fixes_applied
    return 0


# Common type fix patterns
COMMON_PATTERNS = [
    # Fix: -> dict to -> dict[str, Any]
    (r'-> dict:', r'-> dict[str, Any]:'),
    (r'-> dict\n', r'-> dict[str, Any]\n'),

    # Fix: dict[str, dict] to dict[str, dict[str, Any]]
    (r'dict\[str, dict\]', r'dict[str, dict[str, Any]]'),

    # Fix: list[dict] to list[dict[str, Any]]
    (r'list\[dict\]', r'list[dict[str, Any]]'),

    # Fix: dict[str, Callable] to dict[str, Callable[..., Any]]
    (r'dict\[str, Callable\]', r'dict[str, Callable[..., Any]]'),

    # Fix: dict[EntityType, list[re.Pattern]] to dict[EntityType, list[re.Pattern[str]]]
    (r'list\[re\.Pattern\]', r'list[re.Pattern[str]]'),

    # Fix: list[tuple] to list[tuple[Any, ...]]
    (r': list\[tuple\]', r': list[tuple[Any, ...]]'),

    # Fix: triple: tuple to triple: tuple[Any, Any, Any]
    (r'triple: tuple\s+#', r'triple: tuple[Any, Any, Any]  #'),

    # Fix: self.changes: deque to self.changes: deque[Change]
    (r'self\.changes: deque', r'self.changes: deque[Change]'),
]


def add_imports_if_needed(file_path: Path) -> None:
    """Add missing typing imports if needed."""
    content = file_path.read_text()

    # Check if Any is used but not imported
    if 'dict[str, Any]' in content or 'Callable[..., Any]' in content:
        if 'from typing import' in content:
            # Add Any to existing import
            content = re.sub(
                r'(from typing import .*?)(\n)',
                lambda m: m.group(1) + (', Any' if 'Any' not in m.group(1) else '') + m.group(2),
                content,
                count=1
            )
        else:
            # Add new import after module docstring
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('"""') or line.startswith("'''"):
                    # Find end of docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            insert_idx = j + 1
                            break
                    break

            if insert_idx > 0:
                lines.insert(insert_idx, '\nfrom typing import Any\n')
                content = '\n'.join(lines)

        file_path.write_text(content)


def main() -> None:
    """Fix type errors across the codebase."""
    repo_root = Path(__file__).parent.parent

    # Files to fix
    files_to_fix = [
        'src/kgcl/hooks/nlp_query_builder.py',
        'src/kgcl/hooks/dark_matter.py',
        'src/kgcl/hooks/query_optimizer.py',
        'src/kgcl/hooks/performance.py',
        'src/kgcl/hooks/streaming.py',
        'src/kgcl/hooks/resilience.py',
        'src/kgcl/hooks/observability.py',
        'src/kgcl/workflow/scheduler.py',
        'src/kgcl/ttl2dspy/writer.py',
    ]

    total_fixes = 0
    for file_rel in files_to_fix:
        file_path = repo_root / file_rel
        if not file_path.exists():
            print(f"Skipping {file_rel} (not found)")
            continue

        print(f"Processing {file_rel}...")
        fixes = fix_file(file_path, COMMON_PATTERNS)
        add_imports_if_needed(file_path)
        total_fixes += fixes
        print(f"  Applied {fixes} fixes")

    print(f"\nTotal fixes applied: {total_fixes}")


if __name__ == '__main__':
    main()
