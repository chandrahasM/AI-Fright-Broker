import logging

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
from app.models.draft import EmailDetailResponse, ProcessEmailResponse
from app.models.email import EmailSummary, ProcessEmailRequest
from app.repositories.carrier_repository import CarrierRepository
from app.repositories.draft_repository import DraftRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.load_repository import LoadRepository
from app.repositories.rate_history_repository import RateHistoryRepository
from app.services.email_processing_service import EmailProcessingService
from openai import OpenAI

logger = logging.getLogger(__name__)
router = APIRouter(tags=["emails"])


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


@router.get("/emails", response_model=list[EmailSummary])
def list_emails(
    email_repo: EmailRepository = Depends(get_email_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
):
    interactions = interaction_repo.list_all()
    return email_repo.list_summaries(interactions)


@router.get("/emails/{email_id}", response_model=EmailDetailResponse)
def get_email(
    email_id: str,
    email_repo: EmailRepository = Depends(get_email_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
    draft_repo: DraftRepository = Depends(get_draft_repository),
):
    email = email_repo.get_by_email_id(email_id)
    if not email:
        raise HTTPException(status_code=404, detail=f"Email {email_id} not found")
    interaction = interaction_repo.get_by_email_id(email_id)
    draft = draft_repo.get_by_email_id(email_id)
    return EmailDetailResponse(email=email, extraction=interaction, draft=draft)


@router.post("/process-email", response_model=ProcessEmailResponse)
def process_email(
    body: ProcessEmailRequest,
    openai_client: OpenAI = Depends(get_openai_client),
    email_repo: EmailRepository = Depends(get_email_repository),
    load_repo: LoadRepository = Depends(get_load_repository),
    carrier_repo: CarrierRepository = Depends(get_carrier_repository),
    interaction_repo: InteractionRepository = Depends(get_interaction_repository),
    draft_repo: DraftRepository = Depends(get_draft_repository),
    rate_history_repo: RateHistoryRepository = Depends(get_rate_history_repository),
):
    service = _make_service(
        openai_client, email_repo, load_repo, carrier_repo, interaction_repo, draft_repo, rate_history_repo
    )
    try:
        return service.process(body.email_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to process email_id=%s", body.email_id)
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
