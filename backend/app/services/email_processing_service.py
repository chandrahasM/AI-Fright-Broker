"""
EmailProcessingService — orchestrates the full pipeline for a single email.

Flow:
  1. Fetch email from DB
  2. Run Phase 1 extraction (LLM structured output)
  3. Determine needs_review (any required fields missing)
  4. Persist extraction to extracted_interactions
  5. Update email processing_status
  6. Run Phase 2 tool-calling + draft generation
  7. Persist draft to draft_responses
  8. Return ProcessEmailResponse
"""
import logging

from app.agent.agent import FreightBrokerAgent
from app.models.draft import EmailDetailResponse, ProcessEmailResponse
from app.repositories.draft_repository import DraftRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.interaction_repository import InteractionRepository

logger = logging.getLogger(__name__)

# Fields that must be present for auto-processing without broker review
REQUIRED_FIELDS = {"mc_number", "load_id"}


class EmailProcessingService:
    def __init__(
        self,
        agent: FreightBrokerAgent,
        email_repo: EmailRepository,
        interaction_repo: InteractionRepository,
        draft_repo: DraftRepository,
    ) -> None:
        self.agent = agent
        self.email_repo = email_repo
        self.interaction_repo = interaction_repo
        self.draft_repo = draft_repo

    def process(self, email_id: str) -> ProcessEmailResponse:
        logger.info("processing email_id=%s", email_id)

        email = self.email_repo.get_by_email_id(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")

        # Phase 1 — extraction
        extraction = self.agent.extract(email)

        # Determine if broker review is needed
        needs_review = bool(extraction.missing_fields) or any(
            field in extraction.missing_fields for field in REQUIRED_FIELDS
        )
        processing_status = "needs_review" if needs_review else "processed"

        # Persist extraction
        interaction = self.interaction_repo.save(email_id, extraction, needs_review)

        # Update email status
        self.email_repo.update_processing_status(email_id, processing_status)

        # Phase 2 — draft generation (runs regardless of needs_review)
        draft_result = self.agent.generate_draft(email, extraction)
        draft = self.draft_repo.save(email_id, draft_result.text)

        logger.info(
            "email_id=%s complete status=%s intent=%s tools=%s",
            email_id,
            processing_status,
            extraction.intent,
            draft_result.tools_called,
        )

        return ProcessEmailResponse(
            email_id=email_id,
            extraction=interaction,
            draft=draft,
            status=processing_status,
            tools_called=draft_result.tools_called,
        )

    def get_email_detail(self, email_id: str) -> EmailDetailResponse:
        email = self.email_repo.get_by_email_id(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")
        interaction = self.interaction_repo.get_by_email_id(email_id)
        draft = self.draft_repo.get_by_email_id(email_id)
        return EmailDetailResponse(email=email, extraction=interaction, draft=draft)

    def regenerate_draft(self, email_id: str, draft_id: str) -> "DraftRecord":  # noqa: F821
        from app.models.draft import DraftRecord  # avoid circular at module level

        email = self.email_repo.get_by_email_id(email_id)
        if not email:
            raise ValueError(f"Email not found: {email_id}")

        interaction = self.interaction_repo.get_by_email_id(email_id)
        if not interaction:
            raise ValueError(f"No extraction found for email: {email_id}")

        # Re-use existing extraction, generate fresh draft text
        from app.models.extraction import ExtractionResult
        extraction = ExtractionResult(
            carrier_name=interaction.carrier_name,
            mc_number=interaction.carrier_mc,
            load_id=interaction.load_id,
            equipment_type=interaction.equipment_type,
            quoted_rate=interaction.quoted_rate,
            availability_status=interaction.availability_status,
            intent=interaction.intent or "general_inquiry",
            questions_asked=interaction.questions_asked,
            missing_fields=interaction.missing_fields,
            confidence_score=interaction.confidence_score or 0.0,
        )
        draft_result = self.agent.generate_draft(email, extraction)
        return self.draft_repo.update_text(draft_id, draft_result.text)
