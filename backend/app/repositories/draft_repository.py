import logging
from datetime import datetime

from supabase import Client

from app.models.draft import DraftRecord

logger = logging.getLogger(__name__)

TABLE = "draft_responses"


class DraftRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def save(self, email_id: str, draft_text: str) -> DraftRecord:
        payload = {
            "email_id": email_id,
            "draft_text": draft_text,
            "draft_status": "drafted",
        }
        response = self.db.table(TABLE).insert(payload).execute()
        row = response.data[0]
        logger.info("saved draft for email_id=%s", email_id)
        return self._to_model(row)

    def get_by_email_id(self, email_id: str) -> DraftRecord | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("email_id", email_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data[0])

    def get_by_id(self, draft_id: str) -> DraftRecord | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("id", draft_id)
            .maybe_single()
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data)

    def update_status(self, draft_id: str, status: str) -> DraftRecord:
        response = (
            self.db.table(TABLE)
            .update({"draft_status": status})
            .eq("id", draft_id)
            .execute()
        )
        row = response.data[0]
        logger.info("draft %s status updated to %s", draft_id, status)
        return self._to_model(row)

    def update_text(self, draft_id: str, draft_text: str) -> DraftRecord:
        response = (
            self.db.table(TABLE)
            .update({"draft_text": draft_text, "draft_status": "drafted"})
            .eq("id", draft_id)
            .execute()
        )
        return self._to_model(response.data[0])

    def _to_model(self, row: dict) -> DraftRecord:
        return DraftRecord(
            id=row["id"],
            email_id=row["email_id"],
            draft_text=row.get("draft_text", ""),
            draft_status=row.get("draft_status", "drafted"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            if isinstance(row["created_at"], str)
            else row["created_at"],
        )
