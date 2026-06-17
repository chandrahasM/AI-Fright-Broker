import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Annotated

from app.agent.agent import FreightBrokerAgent
from app.agent.tools import ToolExecutor
from app.dependencies import (
    get_carrier_repository,
    get_draft_repository,
    get_interaction_repository,
    get_load_repository,
    get_openai_client,
    get_rate_history_repository,
    get_voice_repository,
)
from app.models.voice import (
    BackfillResponse,
    ProcessVoiceRequest,
    ProcessVoiceResponse,
    UploadVoiceResponse,
    VoiceCallSummary,
    VoiceDetailResponse,
)
from app.repositories.carrier_repository import CarrierRepository
from app.repositories.draft_repository import DraftRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.load_repository import LoadRepository
from app.repositories.rate_history_repository import RateHistoryRepository
from app.repositories.voice_repository import VoiceRepository
from app.services.voice_processing_service import VoiceProcessingService
from openai import OpenAI

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

# Accepted audio MIME types / extensions
ALLOWED_EXTENSIONS = {"wav", "mp3", "mp4", "m4a"}


def _make_service(
    openai_client: OpenAI,
    voice_repo: VoiceRepository,
    load_repo: LoadRepository,
    carrier_repo: CarrierRepository,
    interaction_repo: InteractionRepository,
    draft_repo: DraftRepository,
    rate_history_repo: RateHistoryRepository,
) -> VoiceProcessingService:
    tool_executor = ToolExecutor(
        load_repo=load_repo,
        carrier_repo=carrier_repo,
        rate_history_repo=rate_history_repo,
    )
    agent = FreightBrokerAgent(client=openai_client, tool_executor=tool_executor)
    return VoiceProcessingService(
        openai_client=openai_client,
        agent=agent,
        voice_repo=voice_repo,
        interaction_repo=interaction_repo,
        draft_repo=draft_repo,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/voice-calls", response_model=list[VoiceCallSummary])
def list_voice_calls(
    voice_repo: VoiceRepository = Depends(get_voice_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
):
    calls = voice_repo.list_all()
    interactions = interaction_repo.list_all()
    interaction_by_id = {i.email_id: i for i in interactions}

    summaries: list[VoiceCallSummary] = []
    for call in calls:
        interaction = interaction_by_id.get(call.call_id)
        summaries.append(
            VoiceCallSummary(
                id=call.id,
                call_id=call.call_id,
                file_name=call.file_name,
                caller_name=call.caller_name,
                caller_phone=call.caller_phone,
                mc_number=call.mc_number,
                processing_status=call.processing_status,
                timestamp=call.timestamp,
                carrier_name=interaction.carrier_name if interaction else None,
                carrier_mc=interaction.carrier_mc if interaction else None,
                load_id=interaction.load_id if interaction else None,
                intent=interaction.intent if interaction else None,
            )
        )
    return summaries


@router.get("/voice-calls/{call_id}", response_model=VoiceDetailResponse)
def get_voice_call(
    call_id: str,
    voice_repo: VoiceRepository = Depends(get_voice_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
    draft_repo: DraftRepository = Depends(get_draft_repository),
):
    call = voice_repo.get_by_call_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail=f"Voice call {call_id} not found")
    interaction = interaction_repo.get_by_email_id(call_id)
    draft = draft_repo.get_by_email_id(call_id)
    return VoiceDetailResponse(call=call, extraction=interaction, draft=draft)


@router.post("/voice-calls/upload", response_model=UploadVoiceResponse)
async def upload_voice_call(
    file: Annotated[UploadFile, File(description="WAV/MP3 audio file")],
    caller_name: Annotated[str | None, Form()] = None,
    caller_phone: Annotated[str | None, Form()] = None,
    mc_number: Annotated[str | None, Form()] = None,
    voice_repo: VoiceRepository = Depends(get_voice_repository),
):
    # Validate file extension
    original_name = file.filename or "audio.wav"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()

    # Generate a short, readable call ID
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:4].upper()
    call_id = f"VC-{stamp}-{suffix}"
    storage_path = f"{call_id}.{ext}"

    try:
        voice_repo.upload_file(storage_path, file_bytes, content_type=file.content_type or "audio/wav")
    except Exception as exc:
        logger.exception("Storage upload failed for call_id=%s", call_id)
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {exc}")

    record = voice_repo.create(
        call_id=call_id,
        file_name=original_name,
        storage_path=storage_path,
        caller_name=caller_name,
        caller_phone=caller_phone,
        mc_number=mc_number,
    )

    return UploadVoiceResponse(
        call_id=record.call_id,
        file_name=record.file_name,
        processing_status=record.processing_status,
    )


@router.post("/voice-calls/backfill", response_model=BackfillResponse)
def backfill_voice_calls(
    voice_repo: VoiceRepository = Depends(get_voice_repository),
):
    """
    Scan the voice-calls Storage bucket and create DB records for any files
    that were uploaded directly (not through the /upload endpoint).

    Safe to call multiple times — already-tracked files are skipped.
    """
    # All files currently in storage
    storage_files = voice_repo.list_storage_files()

    # All call_ids already tracked in the DB (keyed by storage_path)
    existing_calls = voice_repo.list_all()
    tracked_paths = {c.storage_path for c in existing_calls}

    new_call_ids: list[str] = []
    already_tracked = 0

    for file_obj in storage_files:
        file_name: str = file_obj.get("name", "")
        if not file_name:
            continue

        # Skip placeholder / folder entries that Supabase sometimes adds
        if file_name == ".emptyFolderPlaceholder":
            continue

        if file_name in tracked_paths:
            already_tracked += 1
            continue

        # Generate a new call_id for this file
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = uuid4().hex[:4].upper()
        call_id = f"VC-{stamp}-{suffix}"

        voice_repo.create(
            call_id=call_id,
            file_name=file_name,
            storage_path=file_name,  # path in bucket = the file name as-uploaded
        )
        new_call_ids.append(call_id)
        logger.info("backfill: created call_id=%s for storage file=%s", call_id, file_name)

    logger.info(
        "backfill complete: synced=%d already_tracked=%d",
        len(new_call_ids),
        already_tracked,
    )
    return BackfillResponse(
        synced=len(new_call_ids),
        already_tracked=already_tracked,
        new_call_ids=new_call_ids,
    )


@router.post("/voice-calls/process", response_model=ProcessVoiceResponse)
def process_voice_call(
    body: ProcessVoiceRequest,
    openai_client: OpenAI = Depends(get_openai_client),
    voice_repo: VoiceRepository = Depends(get_voice_repository),
    load_repo: LoadRepository = Depends(get_load_repository),
    carrier_repo: CarrierRepository = Depends(get_carrier_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
    draft_repo: DraftRepository = Depends(get_draft_repository),
    rate_history_repo: RateHistoryRepository = Depends(get_rate_history_repository),
):
    service = _make_service(
        openai_client, voice_repo, load_repo, carrier_repo,
        interaction_repo, draft_repo, rate_history_repo,
    )
    try:
        return service.process(body.call_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to process call_id=%s", body.call_id)
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
