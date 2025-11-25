"""File metadata ingest engine using Spotlight/Finder via PyObjC."""

from pathlib import Path
from typing import Any

from rdflib import RDF

from kgcl.ingestion.apple.base import BaseIngestEngine, IngestResult


class FilesIngestEngine(BaseIngestEngine):
    """Ingest file metadata from Spotlight/Finder to schema:CreativeWork RDF."""

    def ingest(self, source_object: Any) -> IngestResult:
        """Ingest file metadata to RDF.

        Maps: File metadata → schema:CreativeWork with file properties

        Args:
            source_object: MockFileMetadata or actual file metadata

        Returns
        -------
            IngestResult with schema:CreativeWork RDF triple
        """
        errors = []

        try:
            # Extract file data
            file_path = getattr(source_object, "path", None) or getattr(
                source_object, "file_path", None
            )
            if not file_path:
                errors.append("Missing file path")
                return IngestResult(
                    success=False,
                    graph=self.graph,
                    receipt_hash="",
                    items_processed=0,
                    errors=errors,
                    metadata={},
                )

            # Validate absolute path
            try:
                path_obj = Path(file_path)
                if not path_obj.is_absolute():
                    errors.append(f"File path must be absolute: {file_path}")
                    return IngestResult(
                        success=False,
                        graph=self.graph,
                        receipt_hash="",
                        items_processed=0,
                        errors=errors,
                        metadata={},
                    )
            except Exception as e:
                errors.append(f"Invalid file path: {e!s}")
                return IngestResult(
                    success=False,
                    graph=self.graph,
                    receipt_hash="",
                    items_processed=0,
                    errors=errors,
                    metadata={},
                )

            # Create file URI based on path
            file_uri = self._create_uri(file_path.replace("/", "_"), "file")

            # Add RDF type: schema:CreativeWork
            self.graph.add((file_uri, RDF.type, self.schema_ns.CreativeWork))

            # Map file properties to schema.org
            file_name = getattr(source_object, "name", None) or getattr(
                source_object, "file_name", None
            )
            self._add_literal(file_uri, self.schema_ns.name, file_name)

            # Add file URL
            self._add_literal(file_uri, self.schema_ns.url, f"file://{file_path}")

            # Add creation date
            created_date = getattr(source_object, "contentCreationDate", None) or getattr(
                source_object, "created_date", None
            )
            self._add_literal(file_uri, self.schema_ns.dateCreated, created_date)

            # Add modification date
            modified_date = getattr(source_object, "contentModificationDate", None) or getattr(
                source_object, "modified_date", None
            )
            self._add_literal(file_uri, self.schema_ns.dateModified, modified_date)

            # Add file size
            file_size = getattr(source_object, "fileSize", None) or getattr(
                source_object, "file_size", None
            )
            self._add_literal(file_uri, self.schema_ns.contentSize, file_size)

            # Add file format/MIME type
            file_format = getattr(source_object, "contentType", None) or getattr(
                source_object, "file_type", None
            )
            self._add_literal(file_uri, self.schema_ns.fileFormat, file_format)

            # Add Finder tags as keywords
            tags = (
                getattr(source_object, "tags", None)
                or getattr(source_object, "finder_tags", None)
                or []
            )
            for tag in tags:
                self._add_literal(file_uri, self.schema_ns.keywords, tag)

            # Add Apple-specific properties
            self._add_literal(file_uri, self.apple_ns.sourceApp, "Finder")
            self._add_literal(file_uri, self.apple_ns.sourceIdentifier, file_path)

            # Generate receipt
            receipt_hash = self._generate_receipt()

            return IngestResult(
                success=True,
                graph=self.graph,
                receipt_hash=receipt_hash,
                items_processed=1,
                errors=errors,
                metadata={"file_path": file_path, "file_name": file_name, "file_size": file_size},
            )

        except Exception as e:
            errors.append(f"Files ingest error: {e!s}")
            return IngestResult(
                success=False,
                graph=self.graph,
                receipt_hash="",
                items_processed=0,
                errors=errors,
                metadata={},
            )
