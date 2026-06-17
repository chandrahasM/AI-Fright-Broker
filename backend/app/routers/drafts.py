import logging
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException

from app.agent.agent import FreightBrokerAgent
from app.agent.tools import ToolExecutor
from app.dependencies import (
    get_carrier_repository,
    get_draft_repository,
    get_email_repository,
    get_interaction_repository,
    get_load_repository,
    get_openai_client,
    get_rate_history_repository,
)
from app.models.draft import DraftRecord
from app.repositories.carrier_repository import CarrierRepository
from app.repositories.draft_repository import DraftRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.load_repository import LoadRepository
from app.repositories.rate_history_repository import RateHistoryRepository
from app.services.email_processing_service import EmailProcessingService
from openai import OpenAI

logger = logging.getLogger(__name__)
router = APIRouter(tags=["drafts"])


class GenerateDraftRequest(BaseModel):
    email_id: str


class ApproveDraftRequest(BaseModel):
    draft_id: str


class RejectDraftRequest(BaseModel):
    draft_id: str


def _make_service(
    openai_client: OpenAI,
    email_repo: EmailRepository,
    load_repo: LoadRepository,
    carrier_repo: CarrierRepository,
    interaction_repo: InteractionRepository,
    draft_repo: DraftRepository,
    rate_history_repo: RateHistoryRepository,
) -> EmailProcessingService:
    tool_executor = ToolExecutor(
        load_repo=load_repo,
        carrier_repo=carrier_repo,
        rate_history_repo=rate_history_repo,
    )
    agent = FreightBrokerAgent(client=openai_client, tool_executor=tool_executor)
    return EmailProcessingService(
        agent=agent,
        email_repo=email_repo,
        interaction_repo=interaction_repo,
        draft_repo=draft_repo,
    )


@router.post("/drafts/generate", response_model=DraftRecord)
def generate_draft(
    body: GenerateDraftRequest,
    openai_client: OpenAI = Depends(get_openai_client),
    email_repo: EmailRepository = Depends(get_email_repository),
    load_repo: LoadRepository = Depends(get_load_repository),
    carrier_repo: CarrierRepository = Depends(get_carrier_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
    draft_repo: DraftRepository = Depends(get_draft_repository),
    rate_history_repo: RateHistoryRepository = Depends(get_rate_history_repository),
):
    """Re-generate a draft for an already-processed email."""
    existing_draft = draft_repo.get_by_email_id(body.email_id)
    if not existing_draft:
        raise HTTPException(status_code=404, detail=f"No draft found for email {body.email_id}. Process the email first.")

    service = _make_service(
        openai_client, email_repo, load_repo, carrier_repo, interaction_repo, draft_repo, rate_history_repo
    )
    try:
        return service.regenerate_draft(body.email_id, existing_draft.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to regenerate draft for email_id=%s", body.email_id)
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {exc}")


@router.post("/drafts/approve", response_model=DraftRecord)
def approve_draft(
    body: ApproveDraftRequest,
    draft_repo: DraftRepository = Depends(get_draft_repository),
):
    draft = draft_repo.get_by_id(body.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {body.draft_id} not found")
    return draft_repo.update_status(body.draft_id, "approved")


@router.post("/drafts/reject", response_model=DraftRecord)
def reject_draft(
    body: RejectDraftRequest,
    draft_repo: DraftRepository = Depends(get_draft_repository),
):
    draft = draft_repo.get_by_id(body.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {body.draft_id} not found")
    return draft_repo.update_status(body.draft_id, "rejected")
