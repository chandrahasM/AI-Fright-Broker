"""
FreightBrokerAgent — single agent, two phases.

Phase 1: Structured extraction via OpenAI Responses API with json_schema output.
Phase 2: Tool-calling loop to gather context, then draft generation.
"""
import json
import logging
from dataclasses import dataclass, field

from openai import OpenAI

from app.agent.tools import CARRIER_TOOL_DEFINITIONS, ToolExecutor
from app.config import settings
from app.models.email import EmailRecord
from app.models.extraction import ExtractionResult


@dataclass
class DraftResult:
    """Return value of generate_draft — carries both the text and audit metadata."""
    text: str
    tools_called: list[str] = field(default_factory=list)  # names of every tool invoked

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers for structured trace output
# ---------------------------------------------------------------------------

_SEP  = "─" * 72
_SEP2 = "═" * 72


def _section(title: str) -> str:
    return f"\n{_SEP2}\n  {title}\n{_SEP2}"


def _subsection(title: str) -> str:
    return f"\n{_SEP}\n  {title}\n{_SEP}"


def _log_tokens(response, label: str) -> None:
    """Log token usage from an OpenAI Responses API response if available."""
    usage = getattr(response, "usage", None)
    if usage:
        logger.debug(
            "%s | tokens → input=%s  output=%s  total=%s",
            label,
            getattr(usage, "input_tokens", "?"),
            getattr(usage, "output_tokens", "?"),
            getattr(usage, "total_tokens", "?"),
        )


# ---------------------------------------------------------------------------
# Extraction JSON schema (strict mode)
# ---------------------------------------------------------------------------

_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "carrier_name": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Name of the carrier company if mentioned",
        },
        "mc_number": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Motor Carrier (MC) number if present in the email",
        },
        "load_id": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Load reference number or ID mentioned in the email",
        },
        "equipment_type": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Type of equipment (e.g. Box Truck, Sprinter Van, Flatbed, Refrigerated, Dry Van)",
        },
        "quoted_rate": {
            "anyOf": [{"type": "number"}, {"type": "null"}],
            "description": "Rate quoted by the carrier in USD, null if not mentioned",
        },
        "availability_status": {
            "anyOf": [{"type": "boolean"}, {"type": "null"}],
            "description": "True if carrier states availability, False if unavailable, null if unclear",
        },
        "origin_state": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Two-letter origin state code if mentioned (e.g. 'PA'). Null if not stated.",
        },
        "destination_state": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Two-letter destination state code if mentioned (e.g. 'NJ'). Null if not stated.",
        },
        "intent": {
            "type": "string",
            "enum": [
                "availability",
                "counter_offer",
                "rate_quote",
                "information_request",
                "booking_interest",
                "load_question",
                "general_inquiry",
            ],
            "description": "Primary intent of the carrier's email",
        },
        "questions_asked": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific questions the carrier is asking",
        },
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Required fields that could not be extracted (mc_number, load_id)",
        },
        "confidence_score": {
            "type": "number",
            "description": "Confidence in extraction accuracy from 0.0 to 1.0",
        },
    },
    "required": [
        "carrier_name",
        "mc_number",
        "load_id",
        "equipment_type",
        "quoted_rate",
        "availability_status",
        "origin_state",
        "destination_state",
        "intent",
        "questions_asked",
        "missing_fields",
        "confidence_score",
    ],
    "additionalProperties": False,
}

_EXTRACTION_SYSTEM_PROMPT = """You are a data extraction assistant for a freight brokerage.
Extract structured information from carrier emails.

Intent classification — determine this first, it controls which fields are required:
- counter_offer:       carrier is countering a specific posted rate on a load
- load_question:       carrier has specific questions about a load (pickup address, lumper fee, requirements, hazmat, etc.)
- booking_interest:    carrier wants to book or confirm a specific load
- rate_quote:          carrier is asking about rates — either current lane rates OR historical/average/market rates
- availability:        carrier is announcing truck availability on a lane, looking for loads
- information_request: carrier wants info about becoming a carrier, onboarding, or required documents
- general_inquiry:     partnership outreach, check-in, or anything that doesn't fit above

Required fields by intent (add to missing_fields ONLY if the intent applies and the field is absent):
- counter_offer, load_question, booking_interest:
    → load_id is required (these messages are always about a specific load)
    → mc_number is required
- rate_quote, availability, general_inquiry:
    → mc_number is required
    → load_id is NOT required — do NOT add load_id to missing_fields for these intents
- information_request:
    → neither mc_number nor load_id is required — new carriers may have neither yet

Lane extraction:
- origin_state: extract two-letter state code if carrier mentions origin (e.g. "out of PA", "from Bethlehem PA" → "PA")
- destination_state: extract two-letter state code if carrier mentions destination (e.g. "going to NJ", "toward New York" → "NY")
- If only one direction is mentioned, extract what is available and leave the other null.

Be precise. Only extract what is explicitly stated."""

_DRAFT_SYSTEM_PROMPT = """You are a professional freight broker at Goodlane Logistics.
You have been given context about an inbound carrier email along with data from internal tools.

Available tools and when to use them:
- get_load_details: use when a specific load ID is mentioned
- get_carrier_profile: use when a carrier MC number is known
- get_market_rate: use for a quick current benchmark rate on a lane
- get_rate_history: use when the carrier asks about historical rates, average rates, rate trends,
                   lowest/highest rates, or "what have rates been" on a lane or equipment type.
                   Results are in $/mile (per-mile rates, not total load cost).
                   If the tool returns no data, tell the carrier you don't have enough history
                   for that lane or time period — do not guess or make up numbers.

Write a concise, professional response to the carrier:
- Reference the load number if known
- Acknowledge the carrier's rate or question directly
- When sharing rate history, present $/mile figures clearly and mention the time period covered
- Mention next steps clearly
- Keep it under 150 words
- Sound like a human broker, not a chatbot
- Sign off as: Best, Goodlane Logistics

Do not invent information. Use only what the tools return."""

# Used by the internal QnA chat to convert a broker email draft into a
# concise direct answer for display in the UI bubble.
_DIRECT_ANSWER_SYSTEM_PROMPT = """You are an internal assistant for Goodlane Logistics freight brokers.
Convert the provided broker email draft into a short, direct answer (2–4 sentences max).

Rules:
- Answer the question directly — no greeting, no sign-off, no "Hi [name]"
- Use plain language, not email formality
- Include the key facts (rates, load IDs, counts, statuses) from the draft
- If the draft says there is not enough data, say so plainly
- Do not add information not present in the draft"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class FreightBrokerAgent:
    def __init__(
        self,
        client: OpenAI,
        tool_executor: ToolExecutor,
        tools: list[dict] | None = None,
    ) -> None:
        self.client = client
        self.tool_executor = tool_executor
        # Default to the carrier-safe set; internal callers pass INTERNAL_TOOL_DEFINITIONS
        self.tools = tools if tools is not None else CARRIER_TOOL_DEFINITIONS

    # ------------------------------------------------------------------
    # Phase 1: Structured extraction
    # ------------------------------------------------------------------

    def extract(self, email: EmailRecord) -> ExtractionResult:
        user_content = self._build_extraction_prompt(email)

        logger.info(_section(f"PHASE 1 — EXTRACTION  |  email_id={email.email_id}"))

        logger.debug(
            "%s\nSYSTEM PROMPT:\n%s",
            _subsection("Phase 1 › System Prompt"),
            _EXTRACTION_SYSTEM_PROMPT,
        )
        logger.debug(
            "%s\nUSER PROMPT (extraction input):\n%s",
            _subsection("Phase 1 › User Prompt"),
            user_content,
        )
        logger.info("Phase 1 › calling OpenAI  model=%s", settings.openai_model)

        response = self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "email_extraction",
                    "strict": True,
                    "schema": _EXTRACTION_SCHEMA,
                }
            },
        )

        _log_tokens(response, "Phase 1")
        logger.debug("Phase 1 › response_id=%s", response.id)

        raw_json = self._get_text(response)
        data = json.loads(raw_json)

        logger.debug(
            "%s\nEXTRACTED JSON:\n%s",
            _subsection("Phase 1 › Extracted Output"),
            json.dumps(data, indent=2),
        )
        logger.info(
            "Phase 1 DONE › intent=%s  mc=%s  load=%s  confidence=%.2f  missing=%s",
            data.get("intent"),
            data.get("mc_number"),
            data.get("load_id"),
            data.get("confidence_score", 0.0),
            data.get("missing_fields"),
        )

        return ExtractionResult(**data)

    # ------------------------------------------------------------------
    # Phase 2: Tool calling + draft generation
    # ------------------------------------------------------------------

    def generate_draft(self, email: EmailRecord, extraction: ExtractionResult) -> DraftResult:
        user_content = self._build_draft_prompt(email, extraction)

        logger.info(_section(f"PHASE 2 — DRAFT GENERATION  |  email_id={email.email_id}"))

        logger.debug(
            "%s\nSYSTEM PROMPT:\n%s",
            _subsection("Phase 2 › System Prompt"),
            _DRAFT_SYSTEM_PROMPT,
        )
        logger.debug(
            "%s\nUSER PROMPT (draft input):\n%s",
            _subsection("Phase 2 › User Prompt"),
            user_content,
        )
        logger.debug(
            "Phase 2 › tools available: %s",
            [t["name"] for t in self.tools],
        )
        logger.info("Phase 2 › calling OpenAI  model=%s", settings.openai_model)

        response = self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": _DRAFT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            tools=self.tools,
        )

        _log_tokens(response, "Phase 2 iteration 0")

        # Agentic tool-call loop — continue until the model produces text
        iterations = 0
        max_iterations = 5  # safety limit
        tools_called: list[str] = []  # accumulate every tool name invoked

        while iterations < max_iterations:
            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                logger.info("Phase 2 › no more tool calls — producing draft  (iterations=%d)", iterations)
                break

            logger.info(
                "Phase 2 › iteration %d — model requested %d tool call(s): %s",
                iterations + 1,
                len(tool_calls),
                [c.name for c in tool_calls],
            )

            tool_outputs = []
            for call in tool_calls:
                tools_called.append(call.name)
                args = json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments

                logger.debug(
                    "%s\nTOOL CALL  name=%s  call_id=%s\nARGUMENTS:\n%s",
                    _subsection(f"Tool Call › {call.name}"),
                    call.name,
                    call.call_id,
                    json.dumps(args, indent=2),
                )

                result_json = self.tool_executor.execute(call.name, call.arguments)
                result_data = json.loads(result_json)

                logger.debug(
                    "%s\nTOOL RESULT  name=%s\n%s",
                    _subsection(f"Tool Result › {call.name}"),
                    call.name,
                    json.dumps(result_data, indent=2),
                )
                logger.info(
                    "Phase 2 › tool=%s  status=%s",
                    call.name,
                    "error" if "error" in result_data else "ok",
                )

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result_json,
                    }
                )

            response = self.client.responses.create(
                model=settings.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
            )
            _log_tokens(response, f"Phase 2 iteration {iterations + 1}")
            iterations += 1

        draft_text = self._get_text(response)

        logger.debug(
            "%s\nFINAL DRAFT:\n%s",
            _subsection("Phase 2 › Final Draft"),
            draft_text,
        )
        logger.info(
            "Phase 2 DONE › draft generated  length=%d chars  total_tool_iterations=%d  tools=%s",
            len(draft_text),
            iterations,
            tools_called,
        )

        return DraftResult(text=draft_text, tools_called=tools_called)

    # ------------------------------------------------------------------
    # Direct answer (internal QnA chat only)
    # ------------------------------------------------------------------

    def summarize_to_direct_answer(self, draft_text: str, questions_asked: list[str]) -> str:
        """Convert a broker email draft into a short direct answer for internal UI display."""
        questions_context = (
            f"Questions asked: {', '.join(questions_asked)}\n\n" if questions_asked else ""
        )
        user_content = f"{questions_context}Email draft to convert:\n{draft_text}"

        logger.info("Direct answer › converting draft to direct answer")
        response = self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": _DIRECT_ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        answer = self._get_text(response)
        logger.info("Direct answer › done  length=%d chars", len(answer))
        return answer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_extraction_prompt(self, email: EmailRecord) -> str:
        parts = [
            f"Subject: {email.subject or '(no subject)'}",
            f"Body:\n{email.body or '(empty)'}",
        ]
        if email.from_name:
            parts.append(f"Sender Name: {email.from_name}")
        if email.mc_number:
            parts.append(f"MC Number (from email metadata): {email.mc_number}")
        if email.load_reference:
            parts.append(f"Load Reference (from email metadata): {email.load_reference}")
        if email.equipment_mentioned:
            parts.append(f"Equipment Mentioned (from email metadata): {email.equipment_mentioned}")
        if email.rate_quoted_usd is not None:
            parts.append(f"Rate Quoted (from email metadata): ${email.rate_quoted_usd}")
        return "\n\n".join(parts)

    def _build_draft_prompt(self, email: EmailRecord, extraction: ExtractionResult) -> str:
        sender = email.from_name or email.from_email or "there"
        first_name = sender.split()[0] if sender and sender != "there" else sender

        lane = None
        if extraction.origin_state and extraction.destination_state:
            lane = f"{extraction.origin_state} → {extraction.destination_state}"
        elif extraction.origin_state:
            lane = f"from {extraction.origin_state}"
        elif extraction.destination_state:
            lane = f"to {extraction.destination_state}"

        return f"""Carrier Email:
Subject: {email.subject or '(no subject)'}
From: {email.from_name or ''} <{email.from_email or 'unknown'}>
Body:
{email.body or '(empty)'}

Extracted Information:
- Intent: {extraction.intent}
- Carrier MC: {extraction.mc_number or 'unknown'}
- Load ID: {extraction.load_id or 'unknown'}
- Quoted Rate: ${extraction.quoted_rate or 'not mentioned'}
- Equipment: {extraction.equipment_type or 'unknown'}
- Lane (origin → destination): {lane or 'not specified'}
- Questions Asked: {', '.join(extraction.questions_asked) if extraction.questions_asked else 'none'}

Address the carrier by their first name ({first_name}) in the response.
Use the available tools to look up relevant data before writing the response.
If the intent is rate_quote or the carrier asks about historical/average rates, call get_rate_history
with the lane and equipment type extracted above.
Then write a professional broker reply."""

    def _get_text(self, response) -> str:
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        return content.text
        raise ValueError("No text output found in OpenAI Responses API response")
