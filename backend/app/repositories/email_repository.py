import logging
from datetime import datetime

from supabase import Client

from app.models.email import EmailRecord, EmailSummary
from app.models.extraction import StoredInteraction

logger = logging.getLogger(__name__)

TABLE = "emails"


class EmailRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def get_by_email_id(self, email_id: str) -> EmailRecord | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("email_id", email_id)
            .maybe_single()
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data)

    def get_by_id(self, record_id: str) -> EmailRecord | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("id", record_id)
            .maybe_single()
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data)

    def list_all(self) -> list[EmailRecord]:
        response = (
            self.db.table(TABLE)
            .select("*")
            .order("timestamp", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in response.data]

    def list_summaries(self, interactions: list[StoredInteraction]) -> list[EmailSummary]:
        """Merge email records with their latest extraction for the inbox view."""
        emails = self.list_all()
        interaction_by_email: dict[str, StoredInteraction] = {
            i.email_id: i for i in interactions
        }
        summaries: list[EmailSummary] = []
        for email in emails:
            interaction = interaction_by_email.get(email.email_id)
            summaries.append(
                EmailSummary(
                    id=email.id,
                    email_id=email.email_id,
                    from_name=email.from_name,
                    from_email=email.from_email,
                    subject=email.subject,
                    processing_status=email.processing_status,
                    timestamp=email.timestamp,
                    carrier_name=interaction.carrier_name if interaction else None,
                    carrier_mc=interaction.carrier_mc if interaction else None,
                    load_id=interaction.load_id if interaction else None,
                    # Use agent-extracted intent if available, fall back to email-level intent
                    intent=interaction.intent if interaction else email.intent,
                )
            )
        return summaries

    def update_processing_status(self, email_id: str, status: str) -> None:
        self.db.table(TABLE).update({"processing_status": status}).eq("email_id", email_id).execute()
        logger.info("email_id=%s status updated to %s", email_id, status)

    def _to_model(self, row: dict) -> EmailRecord:
        raw_ts = row.get("timestamp") or row.get("received_at")
        if isinstance(raw_ts, str):
            timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        else:
            timestamp = raw_ts or datetime.utcnow()

        return EmailRecord(
            id=row["id"],
            email_id=row["email_id"],
            from_name=row.get("from_name"),
            from_email=row.get("from_email") or row.get("sender_email"),
            to_email=row.get("to_email"),
            subject=row.get("subject"),
            body=row.get("body"),
            mc_number=row.get("mc_number"),
            load_reference=row.get("load_reference"),
            equipment_mentioned=row.get("equipment_mentioned"),
            rate_quoted_usd=row.get("rate_quoted_usd"),
            intent=row.get("intent"),
            timestamp=timestamp,
            processing_status=row.get("processing_status", "pending"),
        )
