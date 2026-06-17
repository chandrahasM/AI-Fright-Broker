import logging
from datetime import datetime, timezone

from supabase import Client

from app.models.voice import VoiceCallRecord

logger = logging.getLogger(__name__)

TABLE = "voice_calls"
BUCKET = "voice-calls"


class VoiceRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------

    def create(
        self,
        call_id: str,
        file_name: str,
        storage_path: str,
        caller_name: str | None = None,
        caller_phone: str | None = None,
        mc_number: str | None = None,
    ) -> VoiceCallRecord:
        payload = {
            "call_id": call_id,
            "file_name": file_name,
            "storage_path": storage_path,
            "caller_name": caller_name,
            "caller_phone": caller_phone,
            "mc_number": mc_number,
            "processing_status": "pending",
        }
        response = self.db.table(TABLE).insert(payload).execute()
        row = response.data[0]
        logger.info("created voice_call call_id=%s", call_id)
        return self._to_model(row)

    def get_by_call_id(self, call_id: str) -> VoiceCallRecord | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("call_id", call_id)
            .maybe_single()
            .execute()
        )
        if not response.data:
            return None
        return self._to_model(response.data)

    def list_all(self) -> list[VoiceCallRecord]:
        response = (
            self.db.table(TABLE)
            .select("*")
            .order("timestamp", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in response.data]

    def update_transcript(self, call_id: str, transcript: str) -> None:
        self.db.table(TABLE).update({"transcript": transcript}).eq("call_id", call_id).execute()
        logger.info("transcript saved for call_id=%s  chars=%d", call_id, len(transcript))

    def update_processing_status(self, call_id: str, status: str) -> None:
        self.db.table(TABLE).update({"processing_status": status}).eq("call_id", call_id).execute()
        logger.info("call_id=%s status updated to %s", call_id, status)

    # ------------------------------------------------------------------
    # Storage operations
    # ------------------------------------------------------------------

    def upload_file(self, storage_path: str, file_bytes: bytes, content_type: str = "audio/wav") -> None:
        """Upload audio bytes to the voice-calls Supabase Storage bucket."""
        self.db.storage.from_(BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "false"},
        )
        logger.info("uploaded file to storage path=%s  bytes=%d", storage_path, len(file_bytes))

    def download_file(self, storage_path: str) -> bytes:
        """Download audio bytes from the voice-calls Supabase Storage bucket."""
        data = self.db.storage.from_(BUCKET).download(storage_path)
        logger.info("downloaded file from storage path=%s  bytes=%d", storage_path, len(data))
        return data

    def list_storage_files(self) -> list[dict]:
        """Return all file objects in the voice-calls bucket.

        Each item has at least: 'name' (str), 'metadata' (dict with 'size').
        """
        files = self.db.storage.from_(BUCKET).list()
        return files or []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _to_model(self, row: dict) -> VoiceCallRecord:
        raw_ts = row.get("timestamp")
        if isinstance(raw_ts, str):
            timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        else:
            timestamp = raw_ts or datetime.now(timezone.utc)

        return VoiceCallRecord(
            id=row["id"],
            call_id=row["call_id"],
            file_name=row["file_name"],
            storage_path=row["storage_path"],
            caller_name=row.get("caller_name"),
            caller_phone=row.get("caller_phone"),
            mc_number=row.get("mc_number"),
            duration_seconds=row.get("duration_seconds"),
            transcript=row.get("transcript"),
            processing_status=row.get("processing_status", "pending"),
            timestamp=timestamp,
        )
