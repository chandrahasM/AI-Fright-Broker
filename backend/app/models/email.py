from datetime import datetime

from pydantic import BaseModel


class EmailRecord(BaseModel):
    id: str
    email_id: str
    from_name: str | None = None
    from_email: str | None = None
    to_email: str | None = None
    subject: str | None = None
    body: str | None = None
    mc_number: str | None = None
    load_reference: str | None = None
    equipment_mentioned: str | None = None
    rate_quoted_usd: float | None = None  # pre-parsed rate from email, if any
    intent: str | None = None             # rough pre-label from email system
    timestamp: datetime
    processing_status: str  # pending | processed | needs_review


class EmailSummary(BaseModel):
    """Lightweight view used by the inbox table."""
    id: str
    email_id: str
    from_name: str | None = None
    from_email: str | None = None
    subject: str | None = None
    processing_status: str
    timestamp: datetime
    # Populated from extracted_interactions when available
    carrier_name: str | None = None
    carrier_mc: str | None = None
    load_id: str | None = None
    intent: str | None = None  # extracted intent (from agent), overrides email-level


class ProcessEmailRequest(BaseModel):
    email_id: str
