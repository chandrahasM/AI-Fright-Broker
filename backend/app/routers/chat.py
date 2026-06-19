"""
POST /api/chat — dev testing endpoint.

Runs a free-form message through the full agent pipeline (extract + draft)
without touching the database.  Useful for testing prompts, tools, and
rate history queries without needing a real email in the DB.
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agent.agent import FreightBrokerAgent
from app.agent.tools import INTERNAL_TOOL_DEFINITIONS, ToolExecutor
from app.dependencies import (
    get_carrier_repository,
    get_load_repository,
    get_openai_client,
    get_rate_history_repository,
)
from app.models.email import EmailRecord
from app.repositories.carrier_repository import CarrierRepository
from app.repositories.load_repository import LoadRepository
from app.repositories.rate_history_repository import RateHistoryRepository
from openai import OpenAI

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str                           # carrier email body (required)
    subject: str | None = None
    from_name: str | None = None
    from_email: str | None = None
    mc_number: str | None = None
    load_reference: str | None = None
    equipment_mentioned: str | None = None
    rate_quoted_usd: float | None = None


class ExtractionOut(BaseModel):
    carrier_name: str | None
    mc_number: str | None
    load_id: str | None
    equipment_type: str | None
    quoted_rate: float | None
    availability_status: bool | None
    origin_state: str | None
    destination_state: str | None
    intent: str
    questions_asked: list[str]
    missing_fields: list[str]
    confidence_score: float


class ChatResponse(BaseModel):
    email_id: str
    extraction: ExtractionOut
    answer: str        # direct 2-4 sentence answer for the UI bubble
    draft_email: str   # full email-style draft shown only in "View all details"
    tools_called: list[str] = []  # Phase 2 tool names, used by evals for tool accuracy


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    openai_client: OpenAI = Depends(get_openai_client),
    load_repo: LoadRepository = Depends(get_load_repository),
    carrier_repo: CarrierRepository = Depends(get_carrier_repository),
    rate_history_repo: RateHistoryRepository = Depends(get_rate_history_repository),
):
    email_id = f"TEST-{uuid4().hex[:6].upper()}"

    # Synthetic EmailRecord — no DB involved
    email = EmailRecord(
        id=email_id,
        email_id=email_id,
        from_name=body.from_name,
        from_email=body.from_email or "test@carrier.com",
        to_email="dispatch@goodlanelogistics.com",
        subject=body.subject or "(test message)",
        body=body.message,
        mc_number=body.mc_number,
        load_reference=body.load_reference,
        equipment_mentioned=body.equipment_mentioned,
        rate_quoted_usd=body.rate_quoted_usd,
        intent=None,
        timestamp=datetime.now(timezone.utc),
        processing_status="test",
    )

    tool_executor = ToolExecutor(
        load_repo=load_repo,
        carrier_repo=carrier_repo,
        rate_history_repo=rate_history_repo,
    )
    # Internal chat gets the full tool set including search_loads.
    # Carrier email processing always uses the default CARRIER_TOOL_DEFINITIONS.
    agent = FreightBrokerAgent(
        client=openai_client,
        tool_executor=tool_executor,
        tools=INTERNAL_TOOL_DEFINITIONS,
    )

    try:
        extraction = agent.extract(email)
        # Phase 2: generate email-style draft (calls tools)
        draft_result = agent.generate_draft(email, extraction)
        # Convert the draft into a short direct answer for the UI bubble
        direct_answer = agent.summarize_to_direct_answer(
            draft_result.text,
            extraction.questions_asked,
        )
    except Exception as exc:
        logger.exception("Chat agent failed for email_id=%s", email_id)
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}")

    return ChatResponse(
        email_id=email_id,
        extraction=ExtractionOut(**extraction.model_dump()),
        answer=direct_answer,
        draft_email=draft_result.text,
        tools_called=draft_result.tools_called,
    )
