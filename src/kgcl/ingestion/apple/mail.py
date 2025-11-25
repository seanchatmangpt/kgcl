"""Mail message ingest engine for Mail.app metadata."""

from typing import Any

from rdflib import RDF

from kgcl.ingestion.apple.base import BaseIngestEngine, IngestResult


class MailIngestEngine(BaseIngestEngine):
    """Ingest email metadata from Mail.app to schema:Message RDF.

    Note: Only metadata is ingested, not message bodies (privacy).
    """

    def ingest(self, source_object: Any) -> IngestResult:
        """Ingest email metadata to RDF.

        Maps: Mail.app Message → schema:Message with RFC 5322 properties

        Args:
            source_object: MockMailMessage or actual Mail message

        Returns
        -------
            IngestResult with schema:Message RDF triple
        """
        errors = []

        try:
            # Extract message data
            message_id = getattr(source_object, "messageID", None) or getattr(
                source_object, "message_id", None
            )
            if not message_id:
                errors.append("Missing message identifier")
                return IngestResult(
                    success=False,
                    graph=self.graph,
                    receipt_hash="",
                    items_processed=0,
                    errors=errors,
                    metadata={},
                )

            # Create message URI
            message_uri = self._create_uri(message_id, "message")

            # Add RDF type: schema:Message
            self.graph.add((message_uri, RDF.type, self.schema_ns.Message))

            # Map email properties to schema.org
            subject = getattr(source_object, "subject_property", None) or getattr(
                source_object, "subject", None
            )
            self._add_literal(message_uri, self.schema_ns.name, subject)

            # Add sender as schema:author (schema:Person)
            senders = getattr(source_object, "senders", None) or []
            for sender in senders:
                if isinstance(sender, dict):
                    sender_email = sender.get("email")
                    sender_name = sender.get("name")
                    if sender_email:
                        sender_uri = self._create_uri(sender_email, "person")
                        self.graph.add((sender_uri, RDF.type, self.schema_ns.Person))
                        if sender_name:
                            self._add_literal(sender_uri, self.schema_ns.name, sender_name)
                        self._add_literal(sender_uri, self.schema_ns.email, sender_email)
                        self._add_uri(message_uri, self.schema_ns.author, sender_uri)

            # Add recipients as schema:recipient (schema:Person)
            recipients = getattr(source_object, "recipients", None) or []
            for recipient in recipients:
                if isinstance(recipient, dict):
                    recipient_email = recipient.get("email")
                    recipient_name = recipient.get("name")
                    if recipient_email:
                        recipient_uri = self._create_uri(recipient_email, "person")
                        self.graph.add((recipient_uri, RDF.type, self.schema_ns.Person))
                        if recipient_name:
                            self._add_literal(recipient_uri, self.schema_ns.name, recipient_name)
                        self._add_literal(recipient_uri, self.schema_ns.email, recipient_email)
                        self._add_uri(message_uri, self.schema_ns.recipient, recipient_uri)

            # Add date received
            date_received = getattr(source_object, "dateReceived", None) or getattr(
                source_object, "date_received", None
            )
            self._add_literal(message_uri, self.schema_ns.dateReceived, date_received)

            # Add flagged status
            is_flagged = getattr(source_object, "isFlagged", None) or getattr(
                source_object, "is_flagged", None
            )
            if is_flagged:
                self._add_literal(message_uri, self.schema_ns.keywords, "flagged")

            # Add Apple-specific properties
            self._add_literal(message_uri, self.apple_ns.sourceApp, "Mail")
            self._add_literal(message_uri, self.apple_ns.sourceIdentifier, message_id)

            # Generate receipt
            receipt_hash = self._generate_receipt()

            return IngestResult(
                success=True,
                graph=self.graph,
                receipt_hash=receipt_hash,
                items_processed=1,
                errors=errors,
                metadata={
                    "message_id": message_id,
                    "subject": subject,
                    "date_received": date_received,
                },
            )

        except Exception as e:
            errors.append(f"Mail ingest error: {e!s}")
            return IngestResult(
                success=False,
                graph=self.graph,
                receipt_hash="",
                items_processed=0,
                errors=errors,
                metadata={},
            )
