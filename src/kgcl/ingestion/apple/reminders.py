"""Reminders task ingest engine using EventKit via PyObjC."""

from typing import Any

from rdflib import RDF

from kgcl.ingestion.apple.base import BaseIngestEngine, IngestResult


class RemindersIngestEngine(BaseIngestEngine):
    """Ingest reminders/tasks from EventKit to schema:Action RDF."""

    def ingest(self, source_object: Any) -> IngestResult:
        """Ingest a reminder/task to RDF.

        Maps: EKReminder → schema:Action with schema.org properties

        Args:
            source_object: MockEKReminder or actual EKReminder from EventKit

        Returns
        -------
            IngestResult with schema:Action RDF triple
        """
        errors = []

        try:
            # Extract task data
            task_id = getattr(source_object, "calendarItemIdentifier", None) or getattr(
                source_object, "reminder_id", None
            )
            if not task_id:
                errors.append("Missing task identifier")
                return IngestResult(
                    success=False,
                    graph=self.graph,
                    receipt_hash="",
                    items_processed=0,
                    errors=errors,
                    metadata={},
                )

            # Create task URI
            task_uri = self._create_uri(task_id, "task")

            # Add RDF type: schema:Action
            self.graph.add((task_uri, RDF.type, self.schema_ns.Action))

            # Map EKReminder properties to schema.org
            title = getattr(source_object, "title_property", None) or getattr(
                source_object, "title", None
            )
            self._add_literal(task_uri, self.schema_ns.name, title)

            # Map task status
            is_completed = getattr(source_object, "isCompleted", None) or getattr(
                source_object, "completed", None
            )
            if is_completed:
                self._add_uri(
                    task_uri,
                    self.schema_ns.actionStatus,
                    self.schema_ns.CompletedActionStatus,
                )
            else:
                self._add_uri(
                    task_uri,
                    self.schema_ns.actionStatus,
                    self.schema_ns.PotentialActionStatus,
                )

            # Add due date if present
            due_date = getattr(source_object, "dueDateComponents", None) or getattr(
                source_object, "due_date", None
            )
            self._add_literal(task_uri, self.schema_ns.dueDate, due_date)

            # Add notes if present
            notes = getattr(source_object, "notes_property", None) or getattr(
                source_object, "notes", None
            )
            self._add_literal(task_uri, self.schema_ns.description, notes)

            # Add priority if present
            priority = getattr(source_object, "priority_property", None) or getattr(
                source_object, "priority", None
            )
            if priority and priority > 0:
                priority_map = {1: "high", 5: "medium", 9: "low"}
                priority_str = priority_map.get(priority, str(priority))
                self._add_literal(
                    task_uri, self.schema_ns.keywords, f"priority:{priority_str}"
                )

            # Add Apple-specific properties
            list_obj = getattr(source_object, "calendar", None)
            if list_obj:
                list_title = getattr(list_obj, "title", None)
                self._add_literal(task_uri, self.apple_ns.list, list_title)

            self._add_literal(task_uri, self.apple_ns.sourceApp, "Reminders")
            self._add_literal(task_uri, self.apple_ns.sourceIdentifier, task_id)

            # Generate receipt
            receipt_hash = self._generate_receipt()

            return IngestResult(
                success=True,
                graph=self.graph,
                receipt_hash=receipt_hash,
                items_processed=1,
                errors=errors,
                metadata={
                    "task_id": task_id,
                    "title": title,
                    "completed": is_completed,
                },
            )

        except Exception as e:
            errors.append(f"Reminders ingest error: {e!s}")
            return IngestResult(
                success=False,
                graph=self.graph,
                receipt_hash="",
                items_processed=0,
                errors=errors,
                metadata={},
            )
