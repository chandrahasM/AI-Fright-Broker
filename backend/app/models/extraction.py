from datetime import datetime

from pydantic import BaseModel


class ExtractionResult(BaseModel):
    """Output schema from Phase 1 LLM extraction."""
    carrier_name: str | None = None
    mc_number: str | None = None
    load_id: str | None = None
    equipment_type: str | None = None
    quoted_rate: float | None = None
    availability_status: bool | None = None
    origin_state: str | None = None       # two-letter state if mentioned (e.g. "PA")
    destination_state: str | None = None  # two-letter state if mentioned (e.g. "NJ")
    intent: str
    questions_asked: list[str] = []
    missing_fields: list[str] = []
    confidence_score: float = 0.0


class StoredInteraction(BaseModel):
    """An ExtractionResult that has been persisted to the database."""
    id: str
    email_id: str
    carrier_name: str | None = None
    carrier_mc: str | None = None
    load_id: str | None = None
    equipment_type: str | None = None
    quoted_rate: float | None = None
    intent: str | None = None
    availability_status: bool | None = None
    confidence_score: float | None = None
    needs_review: bool = False
    questions_asked: list[str] = []
    missing_fields: list[str] = []
    created_at: datetime
