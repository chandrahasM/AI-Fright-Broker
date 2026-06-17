import logging
from datetime import datetime

from supabase import Client

from app.models.extraction import ExtractionResult, StoredInteraction

logger = logging.getLogger(__name__)

TABLE = "extracted_interactions"


class InteractionRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def save(self, email_id: str, extraction: ExtractionResult, needs_review: bool) -> StoredInteraction:
        payload = {
            "email_id": email_id,
            "carrier_name": extraction.carrier_name,
            "carrier_mc": extraction.mc_number,
            "load_id": extraction.load_id,
            "equipment_type": extraction.equipment_type,
            "quoted_rate": extraction.quoted_rate,
            "intent": extraction.intent,
            "availability_status": extraction.availability_status,
            "confidence_score": extraction.confidence_score,
            "needs_review": needs_review,
            "questions_asked": extraction.questions_asked,
            "missing_fields": extraction.missing_fields,
        }
        response = self.db.table(TABLE).insert(payload).execute()
        row = response.data[0]
        logger.info("saved interaction for email_id=%s intent=%s", email_id, extraction.intent)
        return self._to_model(row)

    def get_by_email_id(self, email_id: str) -> StoredInteraction | None:
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

    def list_all(self) -> list[StoredInteraction]:
        response = self.db.table(TABLE).select("*").execute()
        return [self._to_model(row) for row in response.data]

    def _to_model(self, row: dict) -> StoredInteraction:
        return StoredInteraction(
            id=row["id"],
            email_id=row["email_id"],
            carrier_name=row.get("carrier_name"),
            carrier_mc=row.get("carrier_mc"),
            load_id=row.get("load_id"),
            equipment_type=row.get("equipment_type"),
            quoted_rate=row.get("quoted_rate"),
            intent=row.get("intent"),
            availability_status=row.get("availability_status"),
            confidence_score=row.get("confidence_score"),
            needs_review=row.get("needs_review", False),
            questions_asked=row.get("questions_asked") or [],
            missing_fields=row.get("missing_fields") or [],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            if isinstance(row["created_at"], str)
            else row["created_at"],
        )
