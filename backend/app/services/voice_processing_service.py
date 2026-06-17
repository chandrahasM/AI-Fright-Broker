"""
VoiceProcessingService — orchestrates the full pipeline for a single voice call.

Flow:
  1. Fetch voice call record from DB
  2. Download WAV bytes from Supabase Storage
  3. Transcribe with gpt-4o-transcribe (OpenAI)
  4. Save transcript to voice_calls table
  5. Build a synthetic EmailRecord from the transcript (body = transcript)
  6. Run Phase 1 extraction (same agent as email)
  7. Persist extraction to extracted_interactions (using call_id as email_id)
  8. Run Phase 2 tool-calling + draft generation
  9. Persist draft to draft_responses (using call_id as email_id)
  10. Update voice_calls processing_status
"""
import io
import logging
from datetime import datetime, timezone

from openai import OpenAI

from app.agent.agent import FreightBrokerAgent
from app.models.draft import DraftRecord
from app.models.email import EmailRecord
from app.models.extraction import ExtractionResult
from app.models.voice import ProcessVoiceResponse
from app.repositories.draft_repository import DraftRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.voice_repository import VoiceRepository

logger = logging.getLogger(__name__)

# Fields that must be present for auto-processing without broker review
REQUIRED_FIELDS = {"mc_number", "load_id"}

# gpt-4o-transcribe limit: 25 MB per file
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Domain hint for the transcription model — improves accuracy on freight jargon
_TRANSCRIPTION_PROMPT = (
    "Freight broker phone call. The caller may mention MC numbers, load IDs, "
    "load reference numbers, equipment types like Box Truck or Sprinter Van, "
    "origin/destination states, rates per mile, and dollar amounts."
)


class VoiceProcessingService:
    def __init__(
        self,
        openai_client: OpenAI,
        agent: FreightBrokerAgent,
        voice_repo: VoiceRepository,
        interaction_repo: InteractionRepository,
        draft_repo: DraftRepository,
    ) -> None:
        self.openai_client = openai_client
        self.agent = agent
        self.voice_repo = voice_repo
        self.interaction_repo = interaction_repo
        self.draft_repo = draft_repo

    def process(self, call_id: str) -> ProcessVoiceResponse:
        logger.info("processing call_id=%s", call_id)

        call = self.voice_repo.get_by_call_id(call_id)
        if not call:
            raise ValueError(f"Voice call not found: {call_id}")

        # Step 1 — download audio from Supabase Storage
        wav_bytes = self.voice_repo.download_file(call.storage_path)

        if len(wav_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File too large ({len(wav_bytes) // (1024*1024)} MB). "
                "gpt-4o-transcribe supports up to 25 MB. "
                "Convert to mono 16kHz WAV or MP3 to reduce file size."
            )

        # Step 2 — transcribe with gpt-4o-transcribe
        logger.info("call_id=%s transcribing  bytes=%d", call_id, len(wav_bytes))
        transcript = self._transcribe(wav_bytes, call.file_name)
        logger.info("call_id=%s transcript_chars=%d", call_id, len(transcript))

        # Persist transcript
        self.voice_repo.update_transcript(call_id, transcript)

        # Step 3 — build synthetic EmailRecord so we can reuse the existing agent
        email = EmailRecord(
            id=call_id,
            email_id=call_id,
            from_name=call.caller_name,
            from_email=None,
            to_email="dispatch@goodlanelogistics.com",
            subject=f"Voice call from {call.caller_name or 'unknown caller'}",
            body=transcript,
            mc_number=call.mc_number,
            load_reference=None,
            equipment_mentioned=None,
            rate_quoted_usd=None,
            intent=None,
            timestamp=call.timestamp,
            processing_status="processing",
        )

        # Step 4 — Phase 1 extraction (reuse same agent)
        extraction = self.agent.extract(email)

        needs_review = bool(extraction.missing_fields) or any(
            f in extraction.missing_fields for f in REQUIRED_FIELDS
        )
        processing_status = "needs_review" if needs_review else "processed"

        # Persist extraction — use call_id as email_id key (TEXT field, no schema change needed)
        interaction = self.interaction_repo.save(call_id, extraction, needs_review)

        # Step 5 — Phase 2 draft generation
        draft_result = self.agent.generate_draft(email, extraction)
        draft = self.draft_repo.save(call_id, draft_result.text)

        # Update voice call status
        self.voice_repo.update_processing_status(call_id, processing_status)

        logger.info(
            "call_id=%s complete status=%s intent=%s tools=%s",
            call_id,
            processing_status,
            extraction.intent,
            draft_result.tools_called,
        )

        return ProcessVoiceResponse(
            call_id=call_id,
            transcript_length=len(transcript),
            extraction=interaction,
            draft=draft,
            status=processing_status,
            tools_called=draft_result.tools_called,
        )

    def _transcribe(self, audio_bytes: bytes, file_name: str) -> str:
        """Send audio bytes to gpt-4o-transcribe and return transcript text."""
        # Determine MIME type from extension; default to wav
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "wav"
        mime_map = {"wav": "audio/wav", "mp3": "audio/mpeg", "mp4": "audio/mp4", "m4a": "audio/mp4"}
        mime_type = mime_map.get(ext, "audio/wav")

        audio_file = (file_name, io.BytesIO(audio_bytes), mime_type)

        transcript = self.openai_client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            response_format="text",
            prompt=_TRANSCRIPTION_PROMPT,
        )
        return transcript if isinstance(transcript, str) else transcript.text
