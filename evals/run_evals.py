"""
Evaluation runner — Goodlane Freight Broker Inbox Assistant
============================================================

Metrics measured
────────────────
1. Intent Classification Accuracy  — correct intent / total cases
2. Field Extraction Accuracy       — correct field values / total field checks
                                     (mc_number, load_id, quoted_rate, equipment_type)
3. Tool Selection Accuracy         — cases where all expected tools were called / cases
                                     that have expected_tools defined
4. Grounded Draft Rate             — drafts scoring ≥ 3.5/5 on groundedness (LLM judge)
5. End-to-End Workflow Pass Rate   — cases passing ALL four dimensions above

LLM Judge (1–5 scale per draft)
────────────────────────────────
  professionalism  — appropriate broker tone, no chatbot-speak
  correctness      — references the right load, rate, and carrier facts
  groundedness     — no invented facts; every specific claim traces to input or tool data
  overall          — holistic quality

Usage
─────
    cd backend
    python ../evals/run_evals.py                          # full run with LLM judge
    python ../evals/run_evals.py --skip-judge             # skip judge (faster, no API cost)
    python ../evals/run_evals.py --emails-only --limit 3  # first 3 email cases only
    python ../evals/run_evals.py --voice-only  --limit 3  # first 3 voice cases only
    python ../evals/run_evals.py --verbose                # show per-field breakdown for every case
    python ../evals/run_evals.py --emails-file my.json    # custom email eval file

Notes
─────
• Email cases use POST /api/process-email with email_id only — the production pipeline
  (DB fetch → Phase 1 extract → persist → Phase 2 tools + draft → persist).
• Emails must exist in Supabase before running; use evals/seed_emails.sql if needed.
• StoredInteraction uses carrier_mc; the runner maps it to mc_number for comparison.
• Each eval run re-processes and overwrites extraction/draft rows for that email_id.
• availability_status is compared and shown but does NOT count toward field accuracy.
• Simulated voice cases (VC0001–VC0005) use POST /api/chat with a fixed transcript
  string — fast, deterministic, full extraction + tool accuracy checks.
• Real voice cases (is_real_call=true) use POST /api/voice-calls/process, which
  re-transcribes the WAV from Supabase Storage via Whisper then re-runs the agent.
  Returns tools_called. Transcript fetched via GET for judge context.
  Pipeline health checked: transcript_length > 0 and intent not null.
  Budget ~60-90s per real voice case. Multi-speaker dialogue audio (e.g. VC-5762)
  can give inconsistent Whisper transcripts — set expected_output:{} for those.

Output
──────
• evals/email_response.json — full per-case detail for email cases
• evals/voice_response.json — full per-case detail for voice cases
• Exits 0 on all pass, 1 on any failure
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE           = "http://localhost:8000"
EVALS_DIR          = Path(__file__).parent
EMAIL_RESULTS_FILE = EVALS_DIR / "email_response.json"
VOICE_RESULTS_FILE = EVALS_DIR / "voice_response.json"
BACKEND_ENV        = EVALS_DIR.parent / "backend" / ".env"

# Hard comparison fields — must match to count toward field accuracy.
# availability_status is intentionally excluded: it is often *implied* not
# stated explicitly, so the LLM inconsistently returns null vs true/false.
# It is still compared and reported but does not affect pass/fail.
EXACT_MATCH_FIELDS = ["mc_number", "load_id", "equipment_type"]
NUMERIC_FIELDS     = [("quoted_rate", 5.0)]    # pass within $5
SOFT_BOOL_FIELDS   = ["availability_status"]   # reported but not counted in pass/fail

# Judge pass thresholds (out of 5)
JUDGE_GROUNDEDNESS_PASS = 3.5   # >= this to count as "grounded"
JUDGE_OVERALL_PASS      = 3.0   # >= this for overall judge pass

# ---------------------------------------------------------------------------
# OpenAI key loader
# ---------------------------------------------------------------------------

def _load_openai_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    if BACKEND_ENV.exists():
        for line in BACKEND_ENV.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

# ---------------------------------------------------------------------------
# Extraction evaluation
# ---------------------------------------------------------------------------

def normalize_stored_extraction(extraction: dict) -> dict:
    """Map ProcessEmailResponse.extraction (StoredInteraction) to eval field names."""
    return {
        "intent":              extraction.get("intent"),
        "mc_number":           extraction.get("carrier_mc"),
        "load_id":             extraction.get("load_id"),
        "equipment_type":      extraction.get("equipment_type"),
        "quoted_rate":         extraction.get("quoted_rate"),
        "availability_status": extraction.get("availability_status"),
        "missing_fields":      extraction.get("missing_fields") or [],
        "questions_asked":     extraction.get("questions_asked") or [],
    }


def resolve_email_message(client: httpx.Client, case: dict) -> tuple[str, str, str]:
    """Return (subject, body, formatted_message) for the LLM judge."""
    email_id = case["email_id"]
    detail = call_email_detail(client, email_id)
    if detail and not detail.get("_error") and not detail.get("_not_found"):
        email_obj = detail.get("email") or {}
        subject = email_obj.get("subject") or case.get("subject") or ""
        body = email_obj.get("body") or case.get("body") or ""
    else:
        subject = case.get("subject") or ""
        body = case.get("body") or ""
    message = f"Subject: {subject}\n\n{body}" if subject else body
    return subject, body, message


def evaluate_extraction(actual: dict, expected: dict) -> dict[str, dict]:
    """Return a per-field pass/fail dict."""
    results: dict[str, dict] = {}

    # Exact match fields — string comparisons are case-insensitive so that
    # minor agent capitalisation variation (e.g. "box truck" vs "Box Truck") doesn't
    # count as a failure.
    for field in EXACT_MATCH_FIELDS:
        exp = expected.get(field)
        act = actual.get(field)
        if isinstance(exp, str) and isinstance(act, str):
            passed = exp.strip().lower() == act.strip().lower()
        else:
            passed = exp == act
        results[field] = {"expected": exp, "actual": act, "pass": passed}

    # Numeric fields (within tolerance)
    for field, tol in NUMERIC_FIELDS:
        exp = expected.get(field)
        act = actual.get(field)
        if exp is None and act is None:
            passed = True
        elif exp is None or act is None:
            passed = False
        else:
            passed = abs(float(exp) - float(act)) <= tol
        results[field] = {"expected": exp, "actual": act, "pass": passed}

    # Soft boolean fields — compared and reported but not counted in pass/fail
    for field in SOFT_BOOL_FIELDS:
        exp = expected.get(field)
        act = actual.get(field)
        results[field] = {"expected": exp, "actual": act, "pass": exp == act, "soft": True}

    # missing_fields — order-insensitive set comparison
    exp_miss = set(expected.get("missing_fields") or [])
    act_miss = set(actual.get("missing_fields") or [])
    results["missing_fields"] = {
        "expected": sorted(exp_miss),
        "actual":   sorted(act_miss),
        "pass":     exp_miss == act_miss,
    }

    return results

# ---------------------------------------------------------------------------
# Tool coverage evaluation
# ---------------------------------------------------------------------------

def evaluate_tools(actual: list[str], expected: list[str]) -> dict:
    """All expected tools must appear at least once in actual."""
    if not expected:
        return {"expected": [], "actual": actual, "pass": True, "missing": []}
    missing = [t for t in expected if t not in actual]
    return {
        "expected": expected,
        "actual":   actual,
        "pass":     not missing,
        "missing":  missing,
    }

# ---------------------------------------------------------------------------
# LLM judge (1–5 scale, four dimensions)
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """\
You are a quality evaluator for an AI freight broker assistant.
Read the carrier message and the assistant's draft response, then score four dimensions.

Return ONLY valid JSON — no markdown, no explanation outside the JSON:
{
  "professionalism":      <integer 1-5>,
  "correctness":          <integer 1-5>,
  "groundedness":         <integer 1-5>,
  "overall":              <integer 1-5>,
  "reasoning":            "<one sentence explaining the lowest scoring dimension>"
}

SCORING RUBRIC (1 = very poor, 5 = excellent)

PROFESSIONALISM — tone, format, length
  5 = concise, professional, sounds like a real broker
  3 = functional but slightly robotic or verbose
  1 = chatbot-sounding, excessive pleasantries, or inappropriate tone

CORRECTNESS — references the right facts from the message
  5 = references the correct load ID, carrier rate, equipment, and next steps
  3 = partially correct — mentions the main point but misses a detail
  1 = references wrong load, wrong rate, or answers a different question

GROUNDEDNESS — no invented facts
  5 = every specific claim (rates, addresses, load details) traces to the carrier message,
      extracted data, or plausible tool-backed load/carrier data
  4 = one minor unverifiable detail but no significant fabrication
  3 = one invented fact but the main content is correct
  1 = invents significant facts (wrong rate, made-up load details, fabricated MC status)

Use the extracted structured data block to verify the draft references the correct
load ID, rate, and equipment from Phase 1 extraction.

OVERALL — holistic quality as a broker communication
  5 = would send as-is
  3 = needs minor edits before sending
  1 = would not send — misleading or unhelpful\
"""

def judge_response(
    message: str,
    draft: str,
    openai_key: str,
    questions_asked: list[str] | None = None,
    extracted_data: dict | None = None,
) -> dict:
    """Score a draft with a 1–5 LLM judge. Returns dict with four integer scores."""
    import urllib.request

    qs = ""
    if questions_asked:
        qs = "\n\nCarrier's explicit questions:\n" + "\n".join(f"- {q}" for q in questions_asked)

    extract_block = ""
    if extracted_data:
        extract_block = (
            "\n\nExtracted structured data (Phase 1):\n"
            + json.dumps(extracted_data, indent=2)
        )

    user_content = (
        f"Carrier message:\n{message}{qs}{extract_block}"
        f"\n\nAssistant draft response:\n{draft}"
    )

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user",   "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": 250,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {openai_key}",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())

    content = body["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def call_chat(client: httpx.Client, message: str, subject: str | None = None,
              **kwargs) -> dict | None:
    payload = {"message": message, **kwargs}
    if subject:
        payload["subject"] = subject
    try:
        r = client.post(f"{API_BASE}/api/chat", json=payload, timeout=120.0)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"_error": str(exc)}


def call_process_email(client: httpx.Client, email_id: str) -> dict | None:
    try:
        r = client.post(f"{API_BASE}/api/process-email",
                        json={"email_id": email_id}, timeout=120.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return {"_not_found": True}
        return {"_error": f"HTTP {exc.response.status_code}: {exc.response.text[:120]}"}
    except Exception as exc:
        return {"_error": str(exc)}


def call_email_detail(client: httpx.Client, email_id: str) -> dict | None:
    """Fetch email record from DB (subject + body for judge input)."""
    try:
        r = client.get(f"{API_BASE}/api/emails/{email_id}", timeout=30.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return {"_not_found": True}
        return {"_error": f"HTTP {exc.response.status_code}: {exc.response.text[:120]}"}
    except Exception as exc:
        return {"_error": str(exc)}


def call_process_voice(client: httpx.Client, call_id: str) -> dict | None:
    """POST /api/voice-calls/process — re-runs Whisper + agent pipeline.

    Returns ProcessVoiceResponse including tools_called, mirroring call_process_email.
    Timeout is set high (120s) because Whisper transcription can take ~30s on its own.
    """
    try:
        r = client.post(
            f"{API_BASE}/api/voice-calls/process",
            json={"call_id": call_id},
            timeout=120.0,
        )
        if r.status_code == 404:
            return {"_not_found": True}
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        return {"_error": f"HTTP {exc.response.status_code}: {exc.response.text[:120]}"}
    except Exception as exc:
        return {"_error": str(exc)}


def call_voice_transcript(client: httpx.Client, call_id: str) -> str:
    """Fetch the persisted transcript from GET /api/voice-calls/{call_id} for judge context.

    Called after call_process_voice so the transcript is already saved in the DB.
    """
    try:
        r = client.get(f"{API_BASE}/api/voice-calls/{call_id}", timeout=30.0)
        data = r.json()
        return (data.get("call") or {}).get("transcript") or ""
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# Per-case runner
# ---------------------------------------------------------------------------

def run_case(client: httpx.Client, case: dict, openai_key: str | None,
             skip_judge: bool, is_voice: bool) -> dict:
    case_id         = case.get("case_id") or case.get("email_id", "?")
    expected        = case.get("expected_output", {})
    expected_tools  = case.get("expected_tools", [])
    min_gnd         = case.get("min_groundedness", JUDGE_GROUNDEDNESS_PASS)
    min_ovr         = case.get("min_overall", JUDGE_OVERALL_PASS)
    is_real_call    = case.get("is_real_call", False)
    input_snapshot: dict | None = None
    processing_status: str | None = None

    # ── call the right API ────────────────────────────────────────────────
    if is_real_call:
        # Re-run the full pipeline (Whisper + agent) via POST to get tools_called,
        # mirroring how email evals use POST /api/process-email.
        data = call_process_voice(client, case["call_id"])
        if not data or "_error" in data:
            return {"case_id": case_id,
                    "error": (data or {}).get("_error", "no response"), "pass": False}
        if data.get("_not_found"):
            return {"case_id": case_id,
                    "error": "call not found — check call_id in test_voice.json", "pass": False}

        draft_obj    = data.get("draft") or {}
        draft_text   = draft_obj.get("draft_text", "") if isinstance(draft_obj, dict) else ""
        actual_extraction = data.get("extraction") or {}
        actual_extraction_norm = normalize_stored_extraction(actual_extraction)
        actual_tools      = data.get("tools_called") or []
        processing_status = data.get("status")
        transcript_length = data.get("transcript_length", 0)
        # Fetch the persisted transcript for judge context (saved during processing above)
        message_text = call_voice_transcript(client, case["call_id"]) or f"[Real call {case_id}]"
        has_extraction_expected = bool(expected)
        input_snapshot = {
            "call_id":          case["call_id"],
            "transcript_length": transcript_length,
            "transcript_preview": message_text[:300],
        }
        # Pipeline health: transcription and extraction must have succeeded
        if transcript_length == 0 or not actual_extraction_norm.get("intent"):
            return {
                "case_id":    case_id,
                "is_real_call": True,
                "pass":       False,
                "error":      f"Pipeline failed — transcript_length={transcript_length}, intent={actual_extraction_norm.get('intent')}",
                "input":      input_snapshot,
            }

    elif is_voice:
        # Simulated transcript via /api/chat — send ONLY the message body,
        # mirroring the real voice pipeline where the agent receives only the
        # Whisper transcript and must extract everything from it (no MC/load hints).
        data = call_chat(client, case["message"])
        if not data or "_error" in data:
            return {"case_id": case_id,
                    "error": (data or {}).get("_error", "no response"), "pass": False}
        actual_extraction_norm = data.get("extraction", {})
        actual_tools  = data.get("tools_called", [])
        draft_text    = data.get("draft_email") or data.get("draft") or ""
        message_text  = case.get("message", "")
        has_extraction_expected = bool(expected)

    else:
        # Email — production pipeline via POST /api/process-email (email_id only)
        email_id = case["email_id"]
        data = call_process_email(client, email_id)
        if not data:
            return {"email_id": email_id, "case_id": case_id,
                    "error": "no response", "pass": False}
        if data.get("_not_found"):
            return {"email_id": email_id, "case_id": case_id,
                    "error": "email not in DB — run evals/seed_emails.sql", "pass": False}
        if "_error" in data:
            return {"email_id": email_id, "case_id": case_id,
                    "error": data["_error"], "pass": False}

        extraction_raw = data.get("extraction") or {}
        actual_extraction_norm = normalize_stored_extraction(extraction_raw)
        actual_tools = data.get("tools_called") or []
        draft_obj = data.get("draft") or {}
        draft_text = draft_obj.get("draft_text", "") if isinstance(draft_obj, dict) else ""
        subject, body, message_text = resolve_email_message(client, case)
        input_snapshot = {"subject": subject, "body": body}
        processing_status = data.get("status")
        has_extraction_expected = bool(expected)

    # ── 1. Intent accuracy (tracked separately from other fields) ─────────
    intent_actual   = actual_extraction_norm.get("intent")
    intent_expected = expected.get("intent")
    intent_pass     = (not has_extraction_expected) or (intent_actual == intent_expected)

    # ── 2. Field accuracy (mc_number, load_id, quoted_rate, equipment_type) ─
    field_results: dict[str, dict] = {}
    if has_extraction_expected:
        field_results = evaluate_extraction(actual_extraction_norm, expected)
        # Exclude intent (tracked separately) and soft fields (availability_status)
        # from the hard pass/fail calculation.
        fields_only_pass = all(
            r["pass"] for k, r in field_results.items()
            if k != "intent" and not r.get("soft")
        )
    else:
        fields_only_pass = True   # real calls: no expected extraction to compare

    extraction_pass = intent_pass and fields_only_pass

    # ── 3. Tool selection ─────────────────────────────────────────────────
    tool_result = evaluate_tools(actual_tools, expected_tools)

    # ── 4. LLM judge ─────────────────────────────────────────────────────
    judge_scores: dict = {}
    judge_pass = True
    if not skip_judge and openai_key and draft_text:
        try:
            judge_scores = judge_response(
                message         = message_text,
                draft           = draft_text,
                openai_key      = openai_key,
                questions_asked = actual_extraction_norm.get("questions_asked"),
                extracted_data  = actual_extraction_norm,
            )
            gnd = judge_scores.get("groundedness", 0)
            ovr = judge_scores.get("overall", 0)
            judge_pass = (gnd >= min_gnd) and (ovr >= min_ovr)
        except Exception as exc:
            judge_scores = {"_error": str(exc)}
            judge_pass   = True   # don't fail case on judge errors

    overall_pass = extraction_pass and tool_result["pass"] and judge_pass

    result: dict = {
        "case_id":          case_id,
        "email_id":         case.get("email_id") if not is_voice else None,
        "is_real_call":     is_real_call,
        "pass":             overall_pass,
        "extraction_pass":  extraction_pass,
        "intent_pass":      intent_pass,
        "fields_pass":      fields_only_pass,
        "tool_pass":        tool_result["pass"],
        "judge_pass":       judge_pass,
        "intent_expected":  intent_expected,
        "intent_actual":    intent_actual,
        "fields":           field_results,
        "tools":            tool_result,
        "judge":            judge_scores,
        "draft_preview":    draft_text[:200],
    }

    if has_extraction_expected:
        result["expected_output"] = expected
        result["actual_output"] = actual_extraction_norm
    if input_snapshot is not None:
        result["input"] = input_snapshot
    if processing_status is not None:
        result["processing_status"] = processing_status

    return result

# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

_W = 72

def _icon(p: bool) -> str: return "✓" if p else "✗"

def print_case(result: dict, verbose: bool) -> None:
    status = "PASS" if result.get("pass") else "FAIL"
    j      = result.get("judge", {})
    grd    = j.get("groundedness")
    ovr    = j.get("overall")
    pro    = j.get("professionalism")
    crt    = j.get("correctness")

    # Always show judge scores when they exist (not just on failure)
    if grd is not None:
        grd_icon = _icon(grd >= JUDGE_GROUNDEDNESS_PASS)
        ovr_icon = _icon(ovr >= JUDGE_OVERALL_PASS)
        judge_str = (f"  judge: P={pro}/5  C={crt}/5  "
                     f"{grd_icon}G={grd}/5  {ovr_icon}O={ovr}/5")
    else:
        judge_str = "  judge=skipped (use without --skip-judge for scores)"

    rc_tag = " [real-call]" if result.get("is_real_call") else ""
    label = result.get("email_id") or result.get("case_id", "?")
    print(f"[{status}] {label}{rc_tag}{judge_str}")

    # Always show intent
    intent_icon = _icon(result.get("intent_pass", True))
    print(f"      {intent_icon} intent: "
          f"expected={result.get('intent_expected')!r}  "
          f"actual={result.get('intent_actual')!r}")

    # Always show fields (compact pass line when all pass, full detail when any fails or verbose)
    fields = result.get("fields") or {}
    hard_fields = {k: v for k, v in fields.items()
                   if k not in ("intent",) and not v.get("soft")}
    soft_fields = {k: v for k, v in fields.items() if v.get("soft")}

    for field, res in hard_fields.items():
        if verbose or not res["pass"]:
            icon = _icon(res["pass"])
            print(f"      {icon} {field}: expected={res['expected']!r}  actual={res['actual']!r}")
        elif result.get("fields_pass") and not verbose:
            pass  # silent on pass unless verbose

    # Always show soft fields in verbose mode, or when they fail
    for field, res in soft_fields.items():
        if verbose or not res["pass"]:
            print(f"      ~ {field} (soft): expected={res['expected']!r}  actual={res['actual']!r}")

    # Tool check
    tr = result.get("tools", {})
    if not tr.get("pass") and tr.get("missing"):
        print(f"      {_icon(False)} tools missing: {tr['missing']}  actual={tr['actual']}")
    elif verbose and tr.get("actual"):
        print(f"      {_icon(True)} tools: {tr['actual']}")

    # Judge reasoning (always shown when judge ran)
    if j.get("reasoning"):
        pass_tag = "" if result.get("judge_pass", True) else f"  {_icon(False)} below threshold"
        print(f"      judge note: {j['reasoning']}{pass_tag}")

    preview = result.get("draft_preview", "")
    if preview:
        print(f"      Draft: {preview[:90].strip()}…")
    print()

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary(
    total: int,
    passed: int,
    intent_pass: int,   intent_total: int,
    field_pass: int,    field_total: int,
    tool_pass: int,     tool_total: int,
    grounded: int,      judged: int,
    avg_prof: float | None,
    avg_crt: float | None,
    avg_gnd: float | None,
    avg_ovr: float | None,
) -> None:
    def pct(n: int, d: int) -> str:
        return f"{n}/{d} ({100*n//d}%)" if d else "n/a"

    def avg_str(v: float | None) -> str:
        return f"{v:.1f}/5" if v is not None else "skipped"

    W = _W
    print(f"\n{'╔' + '═'*(W-2) + '╗'}")
    print(f"{'║':<1}{'  EVALUATION RESULTS — GOODLANE FREIGHT BROKER ASSISTANT':^{W-2}}{'║':>1}")
    print(f"{'╠' + '═'*(W-2) + '╣'}")
    rows = [
        ("Metric",                          "Score",                  "Detail"),
        ("─"*32,                            "─"*14,                   "─"*18),
        ("Intent Classification Accuracy",  pct(intent_pass, intent_total),
                                                                       f"{intent_pass} / {intent_total} correct"),
        ("Field Extraction Accuracy",       pct(field_pass, field_total),
                                                                       "mc, load, rate, equip"),
        ("Tool Selection Accuracy",         pct(tool_pass, tool_total),
                                                                       "cases w/ expected tools"),
        ("Grounded Draft Rate",             pct(grounded, judged),
                                                                       f"groundedness ≥ {JUDGE_GROUNDEDNESS_PASS}/5"),
        ("End-to-End Workflow Pass Rate",   pct(passed, total),
                                                                       "all dimensions pass"),
    ]
    for label, score, detail in rows:
        print(f"║  {label:<32}  {score:<14}  {detail:<16}  ║")
    print(f"{'╠' + '═'*(W-2) + '╣'}")
    print(f"║  {'LLM Judge Averages (1–5 scale)':<32}  {'Prof':>4}  {'Corr':>4}  {'Gnd':>4}  {'Ovrl':>4}        ║")
    print(f"║  {'':32}  {avg_str(avg_prof):>7}  {avg_str(avg_crt):>7}  {avg_str(avg_gnd):>7}  {avg_str(avg_ovr):>7}  ║")
    print(f"{'╚' + '═'*(W-2) + '╝'}\n")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(skip_judge: bool, verbose: bool,
        emails_only: bool, voice_only: bool,
        limit: int | None,
        emails_file: str | None, voice_file: str | None) -> None:

    ef = Path(emails_file) if emails_file else EVALS_DIR / "test_emails.json"
    vf = Path(voice_file)  if voice_file  else EVALS_DIR / "test_voice.json"

    email_cases: list[dict] = []
    voice_cases: list[dict] = []

    if not voice_only:
        if ef.exists():
            email_cases = json.loads(ef.read_text(encoding="utf-8"))
            if limit:
                email_cases = email_cases[:limit]
        else:
            print(f"⚠  Email test file not found: {ef}")

    if not emails_only:
        if vf.exists():
            voice_cases = json.loads(vf.read_text(encoding="utf-8"))
            if limit:
                voice_cases = voice_cases[:limit]
        else:
            print(f"⚠  Voice test file not found: {vf}")

    openai_key = None if skip_judge else _load_openai_key()
    if not skip_judge and not openai_key:
        print("⚠  OPENAI_API_KEY not found — running without LLM judge")
        skip_judge = True

    all_results:   list[dict] = []
    email_results: list[dict] = []
    voice_results: list[dict] = []
    total   = 0
    passed  = 0

    intent_pass_n = 0;  intent_total_n = 0
    field_pass_n  = 0;  field_total_n  = 0
    tool_pass_n   = 0;  tool_total_n   = 0
    grounded_n    = 0;  judged_n       = 0

    prof_sum = 0.0; crt_sum = 0.0; gnd_sum = 0.0; ovr_sum = 0.0

    with httpx.Client() as client:
        for section_label, cases, is_voice in [
            (f"EMAIL CASES ({len(email_cases)})", email_cases, False),
            (f"VOICE / TRANSCRIPT CASES ({len(voice_cases)})", voice_cases, True),
        ]:
            if not cases:
                continue
            print(f"\n{'─'*_W}")
            print(f"  {section_label}")
            print(f"{'─'*_W}\n")

            for case in cases:
                result = run_case(client, case, openai_key, skip_judge, is_voice)
                print_case(result, verbose)
                all_results.append(result)
                if is_voice:
                    voice_results.append(result)
                else:
                    email_results.append(result)
                total += 1

                if result.get("pass"):       passed += 1

                # Intent
                if result.get("intent_expected") is not None:
                    intent_total_n += 1
                    if result.get("intent_pass"):    intent_pass_n += 1

                # Fields (count each hard field individually; skip soft / intent)
                for fname, fres in (result.get("fields") or {}).items():
                    if fname == "intent" or fres.get("soft"):
                        continue
                    if result.get("is_real_call"):
                        continue
                    field_total_n += 1
                    if fres.get("pass"):     field_pass_n += 1

                # Tools
                if result.get("tools", {}).get("expected"):
                    tool_total_n += 1
                    if result.get("tool_pass"):      tool_pass_n += 1

                # Judge
                j = result.get("judge", {})
                if "groundedness" in j:
                    judged_n += 1
                    gnd = j["groundedness"]
                    if gnd >= JUDGE_GROUNDEDNESS_PASS:
                        grounded_n += 1
                    prof_sum += j.get("professionalism", 0)
                    crt_sum  += j.get("correctness",     0)
                    gnd_sum  += gnd
                    ovr_sum  += j.get("overall",         0)

                time.sleep(0.3)

    avg_prof = prof_sum / judged_n if judged_n else None
    avg_crt  = crt_sum  / judged_n if judged_n else None
    avg_gnd  = gnd_sum  / judged_n if judged_n else None
    avg_ovr  = ovr_sum  / judged_n if judged_n else None

    print_summary(
        total, passed,
        intent_pass_n, intent_total_n,
        field_pass_n,  field_total_n,
        tool_pass_n,   tool_total_n,
        grounded_n,    judged_n,
        avg_prof, avg_crt, avg_gnd, avg_ovr,
    )

    EMAIL_RESULTS_FILE.write_text(json.dumps(email_results, indent=2))
    VOICE_RESULTS_FILE.write_text(json.dumps(voice_results, indent=2))
    print(f"Email results written to {EMAIL_RESULTS_FILE}")
    print(f"Voice results written to {VOICE_RESULTS_FILE}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Goodlane Freight Broker agent evaluations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_evals.py                         # full run with LLM judge
  python run_evals.py --skip-judge            # fast run, no API cost
  python run_evals.py --emails-only --limit 3 # first 3 email cases only
  python run_evals.py --voice-only  --limit 3 # first 3 voice cases only
  python run_evals.py --emails-file my_cases.json
        """,
    )
    parser.add_argument("--skip-judge",   action="store_true",
                        help="Skip LLM judge scoring (faster, no API cost)")
    parser.add_argument("--verbose",      action="store_true",
                        help="Show per-field breakdown for every case")
    parser.add_argument("--emails-only",  action="store_true",
                        help="Run only email cases")
    parser.add_argument("--voice-only",   action="store_true",
                        help="Run only voice cases")
    parser.add_argument("--limit",        type=int, default=None, metavar="N",
                        help="Run only the first N cases per section")
    parser.add_argument("--emails-file",  default=None, metavar="PATH",
                        help="Path to email eval JSON (default: evals/test_emails.json)")
    parser.add_argument("--voice-file",   default=None, metavar="PATH",
                        help="Path to voice eval JSON (default: evals/test_voice.json)")
    args = parser.parse_args()
    run(
        skip_judge  = args.skip_judge,
        verbose     = args.verbose,
        emails_only = args.emails_only,
        voice_only  = args.voice_only,
        limit       = args.limit,
        emails_file = args.emails_file,
        voice_file  = args.voice_file,
    )
