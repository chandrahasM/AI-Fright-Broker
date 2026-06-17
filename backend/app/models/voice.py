from datetime import datetime

from pydantic import BaseModel


class VoiceCallRecord(BaseModel):
    """A single voice call record from the voice_calls table."""
    id: str
    call_id: str
    file_name: str
    storage_path: str
    caller_name: str | None = None
    caller_phone: str | None = None
    mc_number: str | None = None
    duration_seconds: int | None = None
    transcript: str | None = None
    processing_status: str  # pending | processed | needs_review
    timestamp: datetime


class VoiceCallSummary(BaseModel):
    """Lightweight view for the voice inbox table."""
    id: str
    call_id: str
    file_name: str
    caller_name: str | None = None
    caller_phone: str | None = None
    mc_number: str | None = None
    processing_status: str
    timestamp: datetime
    # Populated from extracted_interactions when available
    carrier_name: str | None = None
    carrier_mc: str | None = None
    load_id: str | None = None
    intent: str | None = None


class UploadVoiceResponse(BaseModel):
    """Returned after a successful file upload."""
    call_id: str
    file_name: str
    processing_status: str


class ProcessVoiceRequest(BaseModel):
    call_id: str


class BackfillResponse(BaseModel):
    """Returned by POST /api/voice-calls/backfill."""
    synced: int           # new DB rows created
    already_tracked: int  # files that already had a row
    new_call_ids: list[str]  # call_ids that were just created


class ProcessVoiceResponse(BaseModel):
    """Returned after the full agent pipeline runs on a voice call."""
    call_id: str
    transcript_length: int        # character count — confirms transcription worked
    extraction: "StoredInteraction"
    draft: "DraftRecord"
    status: str                   # processed | needs_review
    tools_called: list[str] = []  # Phase 2 tool names in call order


class VoiceDetailResponse(BaseModel):
    """Full detail view for the voice side panel."""
    call: VoiceCallRecord
    extraction: "StoredInteraction | None"
    draft: "DraftRecord | None"


# Resolve forward references
from app.models.extraction import StoredInteraction  # noqa: E402
from app.models.draft import DraftRecord             # noqa: E402

ProcessVoiceResponse.model_rebuild()
VoiceDetailResponse.model_rebuild()
