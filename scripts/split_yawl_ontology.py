"""Split monolithic YAWL ontology file into modular structure.

This script splits the large yawl_full_ontology.ttl file (163K+ lines) into:
- A schema file (yawl-java-schema.ttl) containing meta-model definitions
- Individual class files organized by Java package structure
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import TextIO

from rdflib import Graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class OntologySplitError(Exception):
    """Raised when ontology splitting fails."""

    pass


class OntologySplitter:
    """Split monolithic YAWL ontology into modular files."""

    # Standard prefixes for all output files
    STANDARD_PREFIXES = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix yawl: <http://yawlfoundation.org/ontology/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

"""

    def __init__(self, input_file: Path, output_dir: Path) -> None:
        """Initialize the splitter.

        Parameters
        ----------
        input_file : Path
            Path to the monolithic ontology file
        output_dir : Path
            Directory where split files will be written
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.schema_file = output_dir / "yawl-java-schema.ttl"
        self.class_pattern = re.compile(r"^# Class: ([\w\.]+)$")
        self.package_pattern = re.compile(r"^# Package: ([\w\.]+)$")

    def split(self, dry_run: bool = False) -> dict[str, int]:
        """Split the ontology file into modular structure.

        Parameters
        ----------
        dry_run : bool
            If True, validate without writing files

        Returns
        -------
        dict[str, int]
            Statistics: {'classes': count, 'packages': count, 'schema_lines': count}

        Raises
        ------
        OntologySplitError
            If splitting fails
        """
        if not self.input_file.exists():
            raise OntologySplitError(f"Input file not found: {self.input_file}")

        logger.info(f"Reading ontology file: {self.input_file}")
        with self.input_file.open(encoding="utf-8") as f:
            lines = f.readlines()

        # Extract schema (everything before first Package/Class marker)
        schema_lines, data_start = self._extract_schema(lines)
        logger.info(f"Extracted schema: {len(schema_lines)} lines")

        # Parse classes and packages
        classes = self._parse_class_blocks(lines, data_start)
        logger.info(f"Found {len(classes)} classes")

        packages = self._extract_packages(lines, data_start)
        logger.info(f"Found {len(packages)} packages")

        if not dry_run:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Write schema file
            self._write_schema_file(schema_lines)

            # Write class files
            for class_name, class_content in classes.items():
                self._write_class_file(class_name, class_content)

        return {
            "classes": len(classes),
            "packages": len(packages),
            "schema_lines": len(schema_lines),
        }

    def _extract_schema(self, lines: list[str]) -> tuple[list[str], int]:
        """Extract schema section (prefixes and meta-model definitions).

        Parameters
        ----------
        lines : list[str]
            All lines from the input file

        Returns
        -------
        tuple[list[str], int]
            Schema lines and index where data starts
        """
        schema_lines: list[str] = []
        data_start = len(lines)

        for i, line in enumerate(lines):
            # Schema ends at first Package or Class marker
            if self.package_pattern.match(line) or self.class_pattern.match(line):
                data_start = i
                break
            schema_lines.append(line)

        # Remove trailing empty lines from schema
        while schema_lines and not schema_lines[-1].strip():
            schema_lines.pop()

        return schema_lines, data_start

    def _parse_class_blocks(
        self, lines: list[str], start_index: int
    ) -> dict[str, list[str]]:
        """Parse class blocks from the ontology file.

        Parameters
        ----------
        lines : list[str]
            All lines from the input file
        start_index : int
            Index where data section starts

        Returns
        -------
        dict[str, list[str]]
            Mapping of fully qualified class names to their content lines
        """
        classes: dict[str, list[str]] = {}
        current_class: str | None = None
        current_content: list[str] = []
        pending_package: list[str] = []

        for i in range(start_index, len(lines)):
            line = lines[i]

            # Check for package marker
            package_match = self.package_pattern.match(line)
            if package_match:
                # Store package definition for next class
                pending_package = [line]
                # Continue to collect package definition lines
                j = i + 1
                while j < len(lines) and not self.class_pattern.match(
                    lines[j]
                ) and not self.package_pattern.match(lines[j]):
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        pending_package.append(lines[j])
                    j += 1
                continue

            # Check for new class marker
            class_match = self.class_pattern.match(line)
            if class_match:
                # Save previous class if exists
                if current_class and current_content:
                    classes[current_class] = current_content

                # Start new class with pending package definition
                current_class = class_match.group(1)
                current_content = pending_package + [line]
                pending_package = []
            elif current_class:
                # Accumulate content for current class
                # Stop at next class or package marker
                if self.class_pattern.match(line) or self.package_pattern.match(line):
                    # This line belongs to next block, save current class
                    if current_class and current_content:
                        classes[current_class] = current_content
                    current_class = None
                    current_content = []
                    # Process this line as start of new block
                    class_match = self.class_pattern.match(line)
                    if class_match:
                        current_class = class_match.group(1)
                        current_content = [line]
                else:
                    current_content.append(line)

        # Save last class
        if current_class and current_content:
            classes[current_class] = current_content

        return classes

    def _extract_packages(self, lines: list[str], start_index: int) -> set[str]:
        """Extract unique package names from the file.

        Parameters
        ----------
        lines : list[str]
            All lines from the input file
        start_index : int
            Index where data section starts

        Returns
        -------
        set[str]
            Set of unique package names
        """
        packages: set[str] = set()

        for line in lines[start_index:]:
            match = self.package_pattern.match(line)
            if match:
                packages.add(match.group(1))

        return packages

    def _write_schema_file(self, schema_lines: list[str]) -> None:
        """Write schema file with all prefix and meta-model definitions.

        Parameters
        ----------
        schema_lines : list[str]
            Lines containing schema definitions
        """
        logger.info(f"Writing schema file: {self.schema_file}")
        with self.schema_file.open("w", encoding="utf-8") as f:
            f.writelines(schema_lines)
            # Ensure file ends with newline
            if schema_lines and not schema_lines[-1].endswith("\n"):
                f.write("\n")

    def _write_class_file(self, class_name: str, content: list[str]) -> None:
        """Write individual class file in appropriate directory structure.

        Parameters
        ----------
        class_name : str
            Fully qualified class name (e.g., org.yawlfoundation.yawl.controlpanel.YControlPanel)
        content : list[str]
            Lines containing class definition, methods, and fields
        """
        # Parse package and class name
        parts = class_name.split(".")
        if len(parts) < 2:
            raise OntologySplitError(
                f"Invalid class name format: {class_name}"
            )

        class_simple_name = parts[-1]
        package_parts = parts[:-1]

        # Build directory path: codebase/org/yawlfoundation/yawl/...
        class_dir = self.output_dir
        for part in package_parts:
            class_dir = class_dir / part

        class_dir.mkdir(parents=True, exist_ok=True)

        # Write class file
        class_file = class_dir / f"{class_simple_name}.ttl"
        logger.debug(f"Writing class file: {class_file}")

        with class_file.open("w", encoding="utf-8") as f:
            # Write standard prefixes
            f.write(self.STANDARD_PREFIXES)
            f.write("\n")

            # Write class content
            f.writelines(content)

            # Ensure file ends with newline
            if content and not content[-1].endswith("\n"):
                f.write("\n")

    def validate_output(self) -> dict[str, int | bool]:
        """Validate the split ontology output.

        Returns
        -------
        dict[str, int | bool]
            Validation results with counts and success flags

        Raises
        ------
        OntologySplitError
            If validation fails
        """
        if not self.output_dir.exists():
            raise OntologySplitError(f"Output directory not found: {self.output_dir}")

        results: dict[str, int | bool] = {
            "schema_file_exists": False,
            "class_files_count": 0,
            "valid_turtle_files": 0,
            "invalid_turtle_files": 0,
            "total_triples": 0,
        }

        # Check schema file
        schema_file = self.output_dir / "yawl-java-schema.ttl"
        results["schema_file_exists"] = schema_file.exists()

        if not results["schema_file_exists"]:
            raise OntologySplitError("Schema file not found")

        # Count class files and validate Turtle syntax
        class_files: list[Path] = []
        for ttl_file in self.output_dir.rglob("*.ttl"):
            if ttl_file.name == "yawl-java-schema.ttl":
                continue
            class_files.append(ttl_file)

        results["class_files_count"] = len(class_files)

        # Validate each file is valid Turtle
        combined_graph = Graph()
        invalid_files: list[Path] = []

        for ttl_file in [schema_file] + class_files:
            try:
                g = Graph()
                g.parse(str(ttl_file), format="turtle")
                # Merge into combined graph
                combined_graph += g
                results["valid_turtle_files"] += 1
            except Exception as e:
                logger.error(f"Invalid Turtle syntax in {ttl_file}: {e}")
                invalid_files.append(ttl_file)
                results["invalid_turtle_files"] += 1

        results["total_triples"] = len(combined_graph)

        if invalid_files:
            raise OntologySplitError(
                f"Found {len(invalid_files)} files with invalid Turtle syntax"
            )

        logger.info(f"Validation complete:")
        logger.info(f"  Schema file: {'✓' if results['schema_file_exists'] else '✗'}")
        logger.info(f"  Class files: {results['class_files_count']}")
        logger.info(f"  Valid Turtle files: {results['valid_turtle_files']}")
        logger.info(f"  Invalid Turtle files: {results['invalid_turtle_files']}")
        logger.info(f"  Total triples: {results['total_triples']}")

        return results


def main() -> None:
    """Main entry point for the splitting script."""
    parser = argparse.ArgumentParser(
        description="Split monolithic YAWL ontology into modular structure"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/yawl_full_ontology.ttl"),
        help="Input ontology file (default: docs/yawl_full_ontology.ttl)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ontology/codebase"),
        help="Output directory (default: ontology/codebase)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without writing files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output after splitting",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        splitter = OntologySplitter(args.input, args.output)
        stats = splitter.split(dry_run=args.dry_run)

        logger.info("Splitting complete!")
        logger.info(f"  Classes: {stats['classes']}")
        logger.info(f"  Packages: {stats['packages']}")
        logger.info(f"  Schema lines: {stats['schema_lines']}")

        if args.dry_run:
            logger.info("Dry run mode - no files written")
        elif args.validate:
            logger.info("Validating output...")
            validation_results = splitter.validate_output()
            logger.info("Validation complete - all checks passed")

    except OntologySplitError as e:
        logger.error(f"Error splitting ontology: {e}")
        raise SystemExit(1) from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()

