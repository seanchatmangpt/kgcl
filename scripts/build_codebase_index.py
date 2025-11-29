"""Build RDF index for codebase ontology.

This script scans all class files in ontology/codebase/ and builds a comprehensive
RDF index for fast lookups, navigation, and search.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

YAWL = Namespace("http://yawlfoundation.org/ontology/")
INDEX = Namespace("http://yawlfoundation.org/ontology/index#")


class CodebaseIndexBuilder:
    """Build RDF index for codebase ontology."""

    def __init__(self, codebase_dir: Path, output_file: Path) -> None:
        """Initialize the index builder.

        Parameters
        ----------
        codebase_dir : Path
            Directory containing the codebase ontology files
        output_file : Path
            Path where the index file will be written
        """
        self.codebase_dir = codebase_dir
        self.output_file = output_file
        self.index_graph = Graph()
        self.index_graph.bind("yawl", YAWL)
        self.index_graph.bind("index", INDEX)
        self.index_graph.bind("rdf", RDF)
        self.index_graph.bind("rdfs", RDFS)
        self.index_graph.bind("owl", OWL)
        self.index_graph.bind("xsd", XSD)

        # Pattern matching
        self.class_pattern = re.compile(r"^# Class: ([\w\.]+)$")
        self.package_pattern = re.compile(r"^# Package: ([\w\.]+)$")
        self.method_pattern = re.compile(r"^# Method: ([\w\.]+)\.(\w+)$")
        self.field_pattern = re.compile(r"^yawl:(\w+)_(\w+) a yawl:Field")

        # Data structures for indexing
        self.classes: dict[str, dict[str, Any]] = {}
        self.packages: dict[str, set[str]] = {}
        self.methods: dict[str, set[str]] = {}
        self.fields: dict[str, set[str]] = {}
        self.references: dict[str, set[str]] = {}

    def build_index(self) -> None:
        """Build the complete index from all class files.

        Raises
        ------
        FileNotFoundError
            If codebase directory doesn't exist
        """
        if not self.codebase_dir.exists():
            raise FileNotFoundError(f"Codebase directory not found: {self.codebase_dir}")

        logger.info(f"Building index from: {self.codebase_dir}")
        logger.info(f"Output file: {self.output_file}")

        # Scan all class files
        self.scan_class_files()

        # Build indexes
        self.build_class_index()
        self.build_package_index()
        self.build_inheritance_index()
        self.build_method_index()
        self.build_field_index()
        self.build_reference_index()
        self.build_search_index()

        # Write index file
        self.write_index_file()

        logger.info("Index build complete!")

    def scan_class_files(self) -> None:
        """Scan all class files and extract metadata.

        Iterates through all .ttl files in the codebase directory,
        excluding the schema file, and extracts class metadata.
        """
        class_files = list(self.codebase_dir.rglob("*.ttl"))
        schema_file = self.codebase_dir / "yawl-java-schema.ttl"

        for ttl_file in class_files:
            if ttl_file.name == "yawl-java-schema.ttl":
                continue

            try:
                self.extract_class_metadata(ttl_file)
            except Exception as e:
                logger.warning(f"Failed to process {ttl_file}: {e}")

        logger.info(f"Scanned {len(self.classes)} classes")

    def extract_class_metadata(self, ttl_file: Path) -> None:
        """Extract metadata from a class file.

        Parameters
        ----------
        ttl_file : Path
            Path to the class .ttl file
        """
        content = ttl_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        class_name: str | None = None
        package_name: str | None = None
        fully_qualified: str | None = None
        file_path = str(ttl_file.relative_to(self.codebase_dir))
        extends: str | None = None
        implements: list[str] = []
        methods: list[str] = []
        fields: list[str] = []
        comment: str | None = None

        for line in lines:
            # Extract class name
            class_match = self.class_pattern.match(line)
            if class_match:
                fully_qualified = class_match.group(1)
                parts = fully_qualified.split(".")
                class_name = parts[-1]
                package_name = ".".join(parts[:-1])
                continue

            # Extract package
            package_match = self.package_pattern.match(line)
            if package_match:
                package_name = package_match.group(1)
                continue

            # Extract extends (handle multi-line format)
            if "yawl:extends" in line and not line.strip().startswith("#"):
                # Match: yawl:extends yawl:ClassName
                match = re.search(r"yawl:extends\s+yawl:(\w+)", line)
                if match:
                    extends = match.group(1)
                continue

            # Extract implements (handle multi-line format)
            if "yawl:implements" in line and not line.strip().startswith("#"):
                # Match: yawl:implements yawl:InterfaceName
                match = re.search(r"yawl:implements\s+yawl:(\w+)", line)
                if match:
                    impl_name = match.group(1)
                    if impl_name not in implements:
                        implements.append(impl_name)
                continue

            # Extract methods (format: yawl:hasMethod yawl:ClassName_methodName_number)
            if "yawl:hasMethod" in line and not line.strip().startswith("#"):
                # Match: yawl:hasMethod yawl:ClassName_methodName_number
                match = re.search(r"yawl:hasMethod\s+yawl:\w+_(\w+)_\d+", line)
                if match:
                    method_name = match.group(1)
                    if method_name not in methods:
                        methods.append(method_name)
                continue

            # Extract fields (format: yawl:hasField yawl:ClassName_fieldName)
            if "yawl:hasField" in line and not line.strip().startswith("#"):
                # Match: yawl:hasField yawl:ClassName_fieldName
                match = re.search(r"yawl:hasField\s+yawl:\w+_(\w+)", line)
                if match:
                    field_name = match.group(1)
                    if field_name not in fields:
                        fields.append(field_name)
                continue

            # Extract comment (handle multi-line format)
            if "rdfs:comment" in line and not comment:
                # Match: rdfs:comment """text"""
                match = re.search(r'rdfs:comment\s+"""([^"]+)"""', line)
                if match:
                    comment = match.group(1)

        if class_name and fully_qualified:
            self.classes[fully_qualified] = {
                "class_name": class_name,
                "package_name": package_name or "",
                "fully_qualified": fully_qualified,
                "file_path": file_path,
                "extends": extends,
                "implements": implements,
                "methods": methods,
                "fields": fields,
                "comment": comment,
            }

            # Track package membership
            if package_name:
                if package_name not in self.packages:
                    self.packages[package_name] = set()
                self.packages[package_name].add(fully_qualified)

            # Track methods
            for method in methods:
                if method not in self.methods:
                    self.methods[method] = set()
                self.methods[method].add(fully_qualified)

            # Track fields
            for field in fields:
                if field not in self.fields:
                    self.fields[field] = set()
                self.fields[field].add(fully_qualified)

    def build_class_index(self) -> None:
        """Build the class index entries."""
        logger.info("Building class index...")

        for fq_name, metadata in self.classes.items():
            class_uri = YAWL[metadata["class_name"]]
            index_uri = INDEX[f"class_{metadata['class_name']}"]

            self.index_graph.add((index_uri, RDF.type, INDEX.ClassIndex))
            self.index_graph.add((index_uri, INDEX.indexedClass, class_uri))
            self.index_graph.add(
                (index_uri, INDEX.filePath, Literal(metadata["file_path"], datatype=XSD.string))
            )
            self.index_graph.add(
                (
                    index_uri,
                    INDEX.packageName,
                    Literal(metadata["package_name"], datatype=XSD.string),
                )
            )
            self.index_graph.add(
                (
                    index_uri,
                    INDEX.className,
                    Literal(metadata["class_name"], datatype=XSD.string),
                )
            )
            self.index_graph.add(
                (
                    index_uri,
                    INDEX.fullyQualifiedName,
                    Literal(fq_name, datatype=XSD.string),
                )
            )

            if metadata["comment"]:
                self.index_graph.add(
                    (class_uri, RDFS.comment, Literal(metadata["comment"]))
                )

    def build_package_index(self) -> None:
        """Build the package index entries."""
        logger.info("Building package index...")

        for package_name, class_names in self.packages.items():
            package_uri = YAWL[package_name.replace(".", "_")]
            index_uri = INDEX[f"package_{package_name.replace('.', '_')}"]

            self.index_graph.add((index_uri, RDF.type, INDEX.PackageIndex))
            self.index_graph.add((index_uri, INDEX.packageUri, package_uri))
            self.index_graph.add(
                (
                    index_uri,
                    INDEX.packageName,
                    Literal(package_name, datatype=XSD.string),
                )
            )

            for class_name in class_names:
                class_index_uri = INDEX[f"class_{self.classes[class_name]['class_name']}"]
                self.index_graph.add((index_uri, INDEX.hasClass, class_index_uri))

    def build_inheritance_index(self) -> None:
        """Build the inheritance index (extends/implements)."""
        logger.info("Building inheritance index...")

        for fq_name, metadata in self.classes.items():
            class_index_uri = INDEX[f"class_{metadata['class_name']}"]

            if metadata["extends"]:
                parent_class = metadata["extends"]
                parent_index_uri = INDEX[f"class_{parent_class}"]
                self.index_graph.add(
                    (class_index_uri, INDEX.extendsClass, YAWL[parent_class])
                )

                # Build inverse relationship (hasSubclass)
                # Find parent class index
                for parent_idx in self.index_graph.subjects(
                    INDEX.indexedClass, YAWL[parent_class]
                ):
                    self.index_graph.add(
                        (parent_idx, INDEX.hasSubclass, class_index_uri)
                    )
                    break

            for interface in metadata["implements"]:
                self.index_graph.add(
                    (class_index_uri, INDEX.implementsInterface, YAWL[interface])
                )

    def build_method_index(self) -> None:
        """Build the method name index."""
        logger.info("Building method index...")

        for method_name, class_names in self.methods.items():
            method_index_uri = INDEX[f"method_{method_name}"]

            self.index_graph.add((method_index_uri, RDF.type, INDEX.MethodIndex))
            self.index_graph.add(
                (method_index_uri, INDEX.methodName, Literal(method_name, datatype=XSD.string))
            )

            for class_name in class_names:
                class_index_uri = INDEX[f"class_{self.classes[class_name]['class_name']}"]
                self.index_graph.add(
                    (method_index_uri, INDEX.hasMethodNamed, class_index_uri)
                )

    def build_field_index(self) -> None:
        """Build the field name index."""
        logger.info("Building field index...")

        for field_name, class_names in self.fields.items():
            field_index_uri = INDEX[f"field_{field_name}"]

            self.index_graph.add((field_index_uri, RDF.type, INDEX.FieldIndex))
            self.index_graph.add(
                (field_index_uri, INDEX.fieldName, Literal(field_name, datatype=XSD.string))
            )

            for class_name in class_names:
                class_index_uri = INDEX[f"class_{self.classes[class_name]['class_name']}"]
                self.index_graph.add(
                    (field_index_uri, INDEX.hasFieldNamed, class_index_uri)
                )

    def build_reference_index(self) -> None:
        """Build cross-reference index (classes that reference other classes)."""
        logger.info("Building reference index...")

        # Find references by looking at extends, implements, and method/field types
        for fq_name, metadata in self.classes.items():
            class_index_uri = INDEX[f"class_{metadata['class_name']}"]

            # References through inheritance
            if metadata["extends"]:
                ref_class = metadata["extends"]
                # Find the referenced class index (may not be in our classes dict if external)
                ref_entry = INDEX[f"ref_{metadata['class_name']}_to_{ref_class}"]

                self.index_graph.add((ref_entry, RDF.type, INDEX.ReferenceIndex))
                self.index_graph.add((ref_entry, INDEX.referencedBy, class_index_uri))

                # Find referenced class index if it exists
                if ref_class in self.classes:
                    ref_index_uri = INDEX[f"class_{self.classes[ref_class]['class_name']}"]
                    self.index_graph.add((ref_entry, INDEX.referencesClass, ref_index_uri))
                else:
                    # External class reference - use YAWL namespace
                    self.index_graph.add(
                        (ref_entry, INDEX.referencesClass, YAWL[ref_class])
                    )

            # References through interfaces
            for interface in metadata["implements"]:
                if interface in self.classes:
                    ref_index_uri = INDEX[f"class_{self.classes[interface]['class_name']}"]
                    ref_entry = INDEX[f"ref_{metadata['class_name']}_to_{interface}"]

                    self.index_graph.add((ref_entry, RDF.type, INDEX.ReferenceIndex))
                    self.index_graph.add((ref_entry, INDEX.referencedBy, class_index_uri))
                    self.index_graph.add((ref_entry, INDEX.referencesClass, ref_index_uri))

    def build_search_index(self) -> None:
        """Build full-text search index."""
        logger.info("Building search index...")

        for fq_name, metadata in self.classes.items():
            class_index_uri = INDEX[f"class_{metadata['class_name']}"]
            search_uri = INDEX[f"search_{metadata['class_name']}"]

            # Build searchable text from class name, package, methods, fields, comment
            searchable_parts: list[str] = [
                metadata["class_name"],
                metadata["package_name"],
            ]

            if metadata["comment"]:
                searchable_parts.append(metadata["comment"])

            searchable_parts.extend(metadata["methods"])
            searchable_parts.extend(metadata["fields"])

            searchable_text = " ".join(searchable_parts).lower()

            self.index_graph.add((search_uri, RDF.type, INDEX.SearchIndex))
            self.index_graph.add((search_uri, INDEX.searchableClass, class_index_uri))
            self.index_graph.add(
                (
                    search_uri,
                    INDEX.searchableText,
                    Literal(searchable_text, datatype=XSD.string),
                )
            )

    def write_index_file(self) -> None:
        """Write the index to a Turtle file."""
        logger.info(f"Writing index to: {self.output_file}")

        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        with self.output_file.open("w", encoding="utf-8") as f:
            f.write(self.index_graph.serialize(format="turtle"))

        logger.info(f"Index written: {len(self.index_graph)} triples")


def main() -> None:
    """Main entry point for the index builder."""
    parser = argparse.ArgumentParser(description="Build RDF index for codebase ontology")
    parser.add_argument(
        "--codebase-dir",
        type=Path,
        default=Path("ontology/codebase"),
        help="Codebase directory (default: ontology/codebase)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ontology/codebase/index.ttl"),
        help="Output index file (default: ontology/codebase/index.ttl)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        builder = CodebaseIndexBuilder(args.codebase_dir, args.output)
        builder.build_index()

        logger.info("Index build successful!")

    except Exception as e:
        logger.error(f"Index build failed: {e}", exc_info=True)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()

