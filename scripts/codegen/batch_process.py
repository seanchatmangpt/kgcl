"""Process all Java files in parallel.

This module orchestrates batch processing of Java source files into Python clients,
utilizing parallel processing for efficiency.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codegen.generator import CodeGenerator


@dataclass(frozen=True)
class ProcessingResult:
    """Result of processing a single Java file.

    Parameters
    ----------
    java_file : Path
        Source Java file
    python_file : Path | None
        Generated Python file (None if failed)
    success : bool
        Whether processing succeeded
    error : str | None
        Error message if failed
    """

    java_file: Path
    python_file: Path | None
    success: bool
    error: str | None


class BatchProcessor:
    """Process multiple Java files in parallel."""

    def __init__(
        self, template_dir: Path, output_dir: Path, max_workers: int = 8
    ) -> None:
        """Initialize batch processor.

        Parameters
        ----------
        template_dir : Path
            Directory containing Jinja2 templates
        output_dir : Path
            Root directory for generated Python code
        max_workers : int, default=8
            Maximum number of parallel workers
        """
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.max_workers = max_workers

    def process_all_java_files(self, java_root: Path) -> list[ProcessingResult]:
        """Process all Java files in directory tree.

        Parameters
        ----------
        java_root : Path
            Root directory containing Java sources

        Returns
        -------
        list[ProcessingResult]
            Results for each processed file
        """
        # Find all Java files
        java_files = list(java_root.glob("**/*.java"))

        if not java_files:
            return []

        # Process in parallel
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    self._process_single_file, java_file
                ): java_file
                for java_file in java_files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                java_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(
                        ProcessingResult(
                            java_file=java_file,
                            python_file=None,
                            success=False,
                            error=str(e),
                        )
                    )

        return results

    def process_by_package(
        self, java_root: Path
    ) -> dict[str, list[ProcessingResult]]:
        """Process Java files grouped by package.

        Parameters
        ----------
        java_root : Path
            Root directory containing Java sources

        Returns
        -------
        dict[str, list[ProcessingResult]]
            Results grouped by package name
        """
        # Group files by package
        packages: dict[str, list[Path]] = {}

        for java_file in java_root.glob("**/*.java"):
            # Extract package from relative path
            relative = java_file.relative_to(java_root)
            package = str(relative.parent).replace("/", ".")
            if package == ".":
                package = "default"

            if package not in packages:
                packages[package] = []
            packages[package].append(java_file)

        # Process each package
        results_by_package: dict[str, list[ProcessingResult]] = {}

        for package, files in packages.items():
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._process_single_file, java_file)
                    for java_file in files
                ]

                package_results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        package_results.append(result)
                    except Exception as e:
                        package_results.append(
                            ProcessingResult(
                                java_file=Path("unknown"),
                                python_file=None,
                                success=False,
                                error=str(e),
                            )
                        )

                results_by_package[package] = package_results

        return results_by_package

    def _process_single_file(self, java_file: Path) -> ProcessingResult:
        """Process a single Java file.

        Parameters
        ----------
        java_file : Path
            Java source file

        Returns
        -------
        ProcessingResult
            Processing result
        """
        try:
            generator = CodeGenerator(self.template_dir, self.output_dir)
            python_file = generator.generate_python_client(java_file)

            return ProcessingResult(
                java_file=java_file,
                python_file=python_file,
                success=True,
                error=None,
            )
        except Exception as e:
            return ProcessingResult(
                java_file=java_file,
                python_file=None,
                success=False,
                error=str(e),
            )


def process_yawl_ui() -> None:
    """Process all YAWL UI Java files.

    Main entry point for batch processing YAWL UI sources.
    """
    java_root = Path("vendors/yawlui-v5.2/src/main/java/org/yawlfoundation/yawl/ui")
    template_dir = Path("templates/codegen")
    output_dir = Path("src")

    if not java_root.exists():
        raise FileNotFoundError(f"YAWL UI source not found: {java_root}")

    processor = BatchProcessor(template_dir, output_dir, max_workers=8)

    # Process by package for organization
    results_by_package = processor.process_by_package(java_root)

    # Print summary
    total_files = sum(len(results) for results in results_by_package.values())
    successful = sum(
        sum(1 for r in results if r.success)
        for results in results_by_package.values()
    )
    failed = total_files - successful

    print("\nProcessing Summary:")
    print(f"  Total files: {total_files}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    for package, results in sorted(results_by_package.items()):
        package_success = sum(1 for r in results if r.success)
        print(f"\n  {package}: {package_success}/{len(results)} successful")

        # Show failures
        for result in results:
            if not result.success:
                print(f"    FAILED: {result.java_file.name} - {result.error}")


if __name__ == "__main__":
    process_yawl_ui()
