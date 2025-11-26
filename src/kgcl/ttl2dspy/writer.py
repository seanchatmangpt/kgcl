"""Module writer for generated DSPy signatures."""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Result of writing a module."""

    output_path: Path
    shapes_count: int
    signatures_count: int
    file_size: int
    write_time: float
    lines_count: int
    timestamp: str
    ttl_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "output_path": str(self.output_path),
            "ttl_source": str(self.ttl_source) if self.ttl_source else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class ModuleWriter:
    """Write generated modules to Python files."""

    def __init__(self, track_commits: bool = False):
        """Initialize writer.

        Args:
            track_commits: Enable git commit tracking
        """
        self.track_commits = track_commits
        self._write_history: list[WriteResult] = []

    def write_module(
        self,
        code: str,
        output_path: str | Path,
        shapes_count: int = 0,
        ttl_source: str | Path | None = None,
        format_code: bool = True,
    ) -> WriteResult:
        """Write generated code to a Python file.

        Args:
            code: Generated Python code
            output_path: Output file path
            shapes_count: Number of shapes processed
            ttl_source: Source TTL file path
            format_code: Apply code formatting

        Returns
        -------
            WriteResult with metrics
        """
        output_path = Path(output_path)
        start_time = time.time()

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Format code if requested
        if format_code:
            code = self._format_code(code)

        # Write file
        logger.info(f"Writing module to {output_path}")
        output_path.write_text(code, encoding="utf-8")

        # Calculate metrics
        write_time = time.time() - start_time
        file_size = output_path.stat().st_size
        lines_count = code.count("\n") + 1
        signatures_count = code.count("class ") - code.count("# class")

        result = WriteResult(
            output_path=output_path,
            shapes_count=shapes_count,
            signatures_count=signatures_count,
            file_size=file_size,
            write_time=write_time,
            lines_count=lines_count,
            timestamp=datetime.now().isoformat(),
            ttl_source=str(ttl_source) if ttl_source else None,
        )

        # Track history
        self._write_history.append(result)

        logger.info(
            f"Wrote {signatures_count} signatures ({lines_count} lines, {file_size} bytes) in {write_time:.3f}s"
        )

        return result

    def write_batch(
        self, modules: dict[str, str], output_dir: str | Path, format_code: bool = True
    ) -> list[WriteResult]:
        """Write multiple modules in batch.

        Args:
            modules: Dictionary mapping module name to code
            output_dir: Output directory
            format_code: Apply code formatting

        Returns
        -------
            List of WriteResults
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for module_name, code in modules.items():
            output_path = output_dir / f"{module_name}.py"
            result = self.write_module(code=code, output_path=output_path, format_code=format_code)
            results.append(result)

        # Write __init__.py to make it a package
        init_path = output_dir / "__init__.py"
        if not init_path.exists():
            init_code = self._generate_init(list(modules.keys()))
            init_path.write_text(init_code, encoding="utf-8")

        return results

    def write_receipt(self, result: WriteResult, receipt_path: str | Path | None = None) -> Path:
        """Write a JSON receipt for a module write.

        Args:
            result: WriteResult to serialize
            receipt_path: Path to write receipt (default: beside module)

        Returns
        -------
            Path to receipt file
        """
        if receipt_path is None:
            receipt_path = result.output_path.with_suffix(".json")
        else:
            receipt_path = Path(receipt_path)

        receipt_path.write_text(result.to_json(), encoding="utf-8")
        logger.debug(f"Wrote receipt to {receipt_path}")

        return receipt_path

    def _format_code(self, code: str) -> str:
        """Format Python code.

        Args:
            code: Python code to format

        Returns
        -------
            Formatted code
        """
        # Try to use black if available
        try:
            import black

            mode = black.Mode(line_length=88)
            code = black.format_str(code, mode=mode)
            logger.debug("Formatted code with black")
        except ImportError:
            logger.debug("black not available, skipping formatting")
        except Exception as e:
            logger.warning(f"Failed to format with black: {e}")

        return code

    def _generate_init(self, module_names: list[str]) -> str:
        """Generate __init__.py for a package.

        Args:
            module_names: List of module names

        Returns
        -------
            __init__.py content
        """
        lines = ['"""Auto-generated DSPy signatures package."""', "", "# Import all signatures from submodules"]

        for name in module_names:
            lines.append(f"from .{name} import *")

        return "\n".join(lines) + "\n"

    def get_history(self) -> list[WriteResult]:
        """Get write history."""
        return self._write_history

    def export_metrics(self, output_path: str | Path):
        """Export all metrics to JSON.

        Args:
            output_path: Path to write metrics
        """
        output_path = Path(output_path)

        metrics = {
            "total_writes": len(self._write_history),
            "total_signatures": sum(r.signatures_count for r in self._write_history),
            "total_lines": sum(r.lines_count for r in self._write_history),
            "total_bytes": sum(r.file_size for r in self._write_history),
            "total_time": sum(r.write_time for r in self._write_history),
            "history": [r.to_dict() for r in self._write_history],
        }

        output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        logger.info(f"Exported metrics to {output_path}")
