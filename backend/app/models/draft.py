from datetime import datetime

from pydantic import BaseModel


class DraftRecord(BaseModel):
    id: str
    email_id: str
    draft_text: str
    draft_status: str  # drafted | approved | rejected | sent
    created_at: datetime


class ProcessEmailResponse(BaseModel):
    """Returned by POST /api/process-email."""
    email_id: str
    extraction: "StoredInteraction"
    draft: DraftRecord
    status: str              # processed | needs_review
    tools_called: list[str] = []  # Phase 2 tool names in call order


class EmailDetailResponse(BaseModel):
    """Returned by GET /api/emails/{id} — full view for the side panel."""
    email: "EmailRecord"
    extraction: "StoredInteraction | None"
    draft: DraftRecord | None


# Avoid circular imports with forward references resolved at module level
from app.models.email import EmailRecord  # noqa: E402
from app.models.extraction import StoredInteraction  # noqa: E402

ProcessEmailResponse.model_rebuild()
EmailDetailResponse.model_rebuild()
