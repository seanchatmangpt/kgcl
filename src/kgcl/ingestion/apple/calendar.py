"""Calendar event ingest engine using EventKit via PyObjC."""

from typing import Any

from rdflib import RDF

from kgcl.ingestion.apple.base import BaseIngestEngine, IngestResult


class CalendarIngestEngine(BaseIngestEngine):
    """Ingest calendar events from EventKit to schema:Event RDF."""

    def ingest(self, source_object: Any) -> IngestResult:
        """Ingest a calendar event to RDF.

        Maps: EKEvent → schema:Event with schema.org properties

        Args:
            source_object: MockEKEvent or actual EKEvent from EventKit

        Returns
        -------
            IngestResult with schema:Event RDF triple
        """
        errors = []

        try:
            # Extract event data
            event_id = getattr(source_object, "eventIdentifier", None) or getattr(source_object, "event_id", None)
            if not event_id:
                errors.append("Missing event identifier")
                return IngestResult(
                    success=False, graph=self.graph, receipt_hash="", items_processed=0, errors=errors, metadata={}
                )

            # Create event URI
            event_uri = self._create_uri(event_id, "event")

            # Add RDF type: schema:Event
            self.graph.add((event_uri, RDF.type, self.schema_ns.Event))

            # Map EKEvent properties to schema.org
            title = getattr(source_object, "title_property", None) or getattr(source_object, "title", None)
            self._add_literal(event_uri, self.schema_ns.name, title)

            start_date = getattr(source_object, "startDate", None) or getattr(source_object, "start_date", None)
            self._add_literal(event_uri, self.schema_ns.startDate, start_date)

            end_date = getattr(source_object, "endDate", None) or getattr(source_object, "end_date", None)
            self._add_literal(event_uri, self.schema_ns.endDate, end_date)

            location = getattr(source_object, "location_property", None) or getattr(source_object, "location", None)
            self._add_literal(event_uri, self.schema_ns.location, location)

            notes = getattr(source_object, "notes_property", None) or getattr(source_object, "notes", None)
            self._add_literal(event_uri, self.schema_ns.description, notes)

            # Add attendees
            attendees = (
                getattr(source_object, "attendees_list", None) or getattr(source_object, "attendees", None) or []
            )
            for attendee in attendees:
                if isinstance(attendee, dict):
                    attendee_name = attendee.get("name")
                    attendee_email = attendee.get("email")
                    if attendee_email:
                        attendee_uri = self._create_uri(attendee_email, "person")
                        self.graph.add((attendee_uri, RDF.type, self.schema_ns.Person))
                        if attendee_name:
                            self._add_literal(attendee_uri, self.schema_ns.name, attendee_name)
                        self._add_literal(attendee_uri, self.schema_ns.email, attendee_email)
                        self._add_uri(event_uri, self.schema_ns.attendee, attendee_uri)

            # Add Apple-specific properties
            calendar = getattr(source_object, "calendar", None)
            if calendar:
                calendar_title = getattr(calendar, "title", None)
                self._add_literal(event_uri, self.apple_ns.calendar, calendar_title)

            self._add_literal(event_uri, self.apple_ns.sourceApp, "Calendar")
            self._add_literal(event_uri, self.apple_ns.sourceIdentifier, event_id)

            # Generate receipt
            receipt_hash = self._generate_receipt()

            return IngestResult(
                success=True,
                graph=self.graph,
                receipt_hash=receipt_hash,
                items_processed=1,
                errors=errors,
                metadata={"event_id": event_id, "title": title},
            )

        except Exception as e:
            errors.append(f"Calendar ingest error: {e!s}")
            return IngestResult(
                success=False, graph=self.graph, receipt_hash="", items_processed=0, errors=errors, metadata={}
            )
