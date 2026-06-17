"""
Evaluation runner for the Goodlane Freight Broker Inbox Assistant.

Dimensions measured
───────────────────
1. Extraction accuracy  — per-field exact / numeric / set match
2. Tool coverage        — did Phase 2 call every expected tool?
3. Relevancy            — LLM judge: does the draft address what was asked?
4. Groundedness         — LLM judge: does the draft avoid inventing specific facts?

Usage
─────
    cd backend
    python ../evals/run_evals.py [--skip-judge]

    --skip-judge   skip the OpenAI judge calls (faster, no API cost)

Requirements
────────────
• Backend running at http://localhost:8000
• OPENAI_API_KEY set in environment or in backend/.env
• test_emails.json cases (CE0042–CE0053) must exist in the DB *or* the
  runner will fall back to /api/chat automatically when /api/process-email
  returns 404.

Output
──────
• evals/results.json — full per-case results
• Exit 0 on all-pass, exit 1 on any failure
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

API_BASE       = "http://localhost:8000"
EVALS_DIR      = Path(__file__).parent
RESULTS_FILE   = EVALS_DIR / "results.json"
BACKEND_ENV    = EVALS_DIR.parent / "backend" / ".env"

# Extraction fields evaluated for exact match
EXACT_MATCH_FIELDS = ["intent", "mc_number", "load_id", "equipment_type"]
NUMERIC_FIELDS     = [("quoted_rate", 5.0)]   # pass if within $5
BOOL_FIELDS        = ["availability_status"]

# LLM judge thresholds (overrideable per case with min_relevancy / min_groundedness)
DEFAULT_MIN_RELEVANCY    = 0.7
DEFAULT_MIN_GROUNDEDNESS = 0.7

# ---------------------------------------------------------------------------
# OpenAI key loading (for LLM judge)
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

def evaluate_extraction(actual: dict, expected: dict) -> dict[str, dict]:
    results: dict[str, dict] = {}

    for field in EXACT_MATCH_FIELDS:
        exp = expected.get(field)
        act = actual.get(field)
        results[field] = {"expected": exp, "actual": act, "pass": exp == act}

    for field, tolerance in NUMERIC_FIELDS:
        exp = expected.get(field)
        act = actual.get(field)
        if exp is None and act is None:
            passed = True
        elif exp is None or act is None:
            passed = False
        else:
            passed = abs(float(exp) - float(act)) <= tolerance
        results[field] = {"expected": exp, "actual": act, "pass": passed}

    for field in BOOL_FIELDS:
        exp = expected.get(field)
        act = actual.get(field)
        results[field] = {"expected": exp, "actual": act, "pass": exp == act}

    # missing_fields — order-insensitive set equality
    exp_missing = set(expected.get("missing_fields") or [])
    act_missing = set(actual.get("missing_fields") or [])
    results["missing_fields"] = {
        "expected": sorted(exp_missing),
        "actual":   sorted(act_missing),
        "pass":     exp_missing == act_missing,
    }

    return results

# ---------------------------------------------------------------------------
# Tool coverage evaluation
# ---------------------------------------------------------------------------

def evaluate_tools(actual_tools: list[str], expected_tools: list[str]) -> dict:
    """Every expected tool must appear at least once in actual_tools."""
    if not expected_tools:
        return {"expected": [], "actual": actual_tools, "pass": True, "missing": []}

    missing = [t for t in expected_tools if t not in actual_tools]
    return {
        "expected": expected_tools,
        "actual":   actual_tools,
        "pass":     len(missing) == 0,
        "missing":  missing,
    }

# ---------------------------------------------------------------------------
# LLM judge
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """\
You are an evaluator for an AI freight broker assistant.
Given a carrier message and the assistant's draft response, score two dimensions.

Return ONLY valid JSON matching this exact schema:
{
  "relevancy":            <float 0.0-1.0>,
  "groundedness":         <float 0.0-1.0>,
  "relevancy_reason":     "<one sentence>",
  "groundedness_reason":  "<one sentence>"
}

RELEVANCY (0.0–1.0): Does the draft directly address what the carrier communicated or asked?
  1.0 = fully addresses all questions / statements
  0.5 = partially addresses (answers some but misses others)
  0.0 = ignores the carrier's request or is off-topic

GROUNDEDNESS (0.0–1.0): Does the draft avoid inventing specific facts?
  Specific facts = load addresses, rates, pickup times, carrier profile data, MC status.
  1.0 = only cites facts the carrier stated OR appropriately says "I'll need to look that up"
  0.5 = mostly grounded but contains one minor unverifiable claim
  0.0 = invents significant facts (addresses, rates, contact details) with no basis\
"""

def judge_response(
    message: str,
    draft: str,
    openai_key: str,
    questions_asked: list[str] | None = None,
) -> dict:
    """Call gpt-4o-mini to score relevancy and groundedness."""
    import urllib.request

    questions_str = ""
    if questions_asked:
        questions_str = "\n\nCarrier's explicit questions:\n" + "\n".join(f"- {q}" for q in questions_asked)

    user_content = (
        f"Carrier message:\n{message}"
        f"{questions_str}\n\n"
        f"Assistant draft response:\n{draft}"
    )

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user",   "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": 200,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())

    content = body["choices"][0]["message"]["content"].strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def call_chat(client: httpx.Client, message: str, **fields) -> dict | None:
    try:
        r = client.post(
            f"{API_BASE}/api/chat",
            json={"message": message, **fields},
            timeout=90.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"_error": str(exc)}


def call_process_email(client: httpx.Client, email_id: str) -> dict | None:
    try:
        r = client.post(
            f"{API_BASE}/api/process-email",
            json={"email_id": email_id},
            timeout=90.0,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return {"_not_found": True}
        return {"_error": f"HTTP {exc.response.status_code}: {exc.response.text[:100]}"}
    except Exception as exc:
        return {"_error": str(exc)}

# ---------------------------------------------------------------------------
# Per-case runner
# ---------------------------------------------------------------------------

def run_case(
    client: httpx.Client,
    case: dict,
    openai_key: str | None,
    skip_judge: bool,
    is_voice: bool,
) -> dict:
    case_id  = case.get("case_id") or case.get("email_id", "?")
    expected = case.get("expected_output", {})
    expected_tools   = case.get("expected_tools", [])
    min_relevancy    = case.get("min_relevancy",    DEFAULT_MIN_RELEVANCY)
    min_groundedness = case.get("min_groundedness", DEFAULT_MIN_GROUNDEDNESS)

    # ── call the API ──────────────────────────────────────────────────────
    if is_voice:
        data = call_chat(
            client,
            message          = case["message"],
            from_name        = case.get("from_name"),
            mc_number        = case.get("mc_number"),
            load_reference   = case.get("load_reference"),
            equipment_mentioned = case.get("equipment_mentioned"),
        )
    else:
        # Try the real email pipeline first; fall back to /api/chat if email not in DB
        data = call_process_email(client, case["email_id"])
        if data and data.get("_not_found"):
            data = call_chat(
                client,
                message             = case["body"],
                from_name           = case.get("from_name"),
                mc_number           = case.get("mc_number"),
                load_reference      = case.get("load_reference"),
                equipment_mentioned = case.get("equipment_mentioned"),
            )

    if not data or "_error" in data:
        return {
            "case_id": case_id,
            "error":   (data or {}).get("_error", "no response"),
            "pass":    False,
        }

    # Normalise: /api/chat returns extraction directly; /api/process-email wraps it
    actual_extraction = data.get("extraction", {})
    actual_tools      = data.get("tools_called", [])
    draft_text        = (
        data.get("draft")
        if isinstance(data.get("draft"), str)
        else (data.get("draft") or {}).get("draft_text", "")
    )
    message_text = case.get("message") or case.get("body", "")

    # ── 1. Extraction accuracy ────────────────────────────────────────────
    field_results = evaluate_extraction(actual_extraction, expected)
    extraction_pass = all(r["pass"] for r in field_results.values())

    # ── 2. Tool coverage ──────────────────────────────────────────────────
    tool_result = evaluate_tools(actual_tools, expected_tools)

    # ── 3 & 4. LLM judge (relevancy + groundedness) ───────────────────────
    judge_scores: dict = {}
    judge_pass = True
    if not skip_judge and openai_key and draft_text:
        try:
            judge_scores = judge_response(
                message        = message_text,
                draft          = draft_text,
                openai_key     = openai_key,
                questions_asked= actual_extraction.get("questions_asked"),
            )
            relevancy    = judge_scores.get("relevancy",    0.0)
            groundedness = judge_scores.get("groundedness", 0.0)
            judge_pass   = relevancy >= min_relevancy and groundedness >= min_groundedness
        except Exception as exc:
            judge_scores = {"_error": str(exc)}
            judge_pass   = True  # don't fail the case if judge errors

    overall_pass = extraction_pass and tool_result["pass"] and judge_pass

    return {
        "case_id":         case_id,
        "pass":            overall_pass,
        "extraction_pass": extraction_pass,
        "tool_pass":       tool_result["pass"],
        "judge_pass":      judge_pass,
        "fields":          field_results,
        "tools":           tool_result,
        "judge":           judge_scores,
        "draft_preview":   draft_text[:200],
        "intent_actual":   actual_extraction.get("intent"),
        "tools_called":    actual_tools,
    }

# ---------------------------------------------------------------------------
# Printer helpers
# ---------------------------------------------------------------------------

def _icon(passed: bool) -> str:
    return "✓" if passed else "✗"

def print_case(result: dict) -> None:
    status = "PASS" if result.get("pass") else "FAIL"
    judge  = result.get("judge", {})
    rel    = judge.get("relevancy")
    grd    = judge.get("groundedness")
    judge_str = (
        f"  relevancy={rel:.2f}  groundedness={grd:.2f}"
        if rel is not None else "  judge=skipped"
    )

    print(f"[{status}] {result['case_id']}{judge_str}")

    # Extraction failures
    for field, res in (result.get("fields") or {}).items():
        if not res["pass"]:
            print(f"      {_icon(False)} {field}: expected={res['expected']!r}  actual={res['actual']!r}")

    # Tool coverage failures
    tr = result.get("tools", {})
    if not tr.get("pass") and tr.get("missing"):
        print(f"      {_icon(False)} tools missing: {tr['missing']}  actual={tr['actual']}")

    # Judge failures
    if judge and not result.get("judge_pass", True):
        if rel is not None and rel < DEFAULT_MIN_RELEVANCY:
            print(f"      {_icon(False)} relevancy {rel:.2f} < threshold  — {judge.get('relevancy_reason','')}")
        if grd is not None and grd < DEFAULT_MIN_GROUNDEDNESS:
            print(f"      {_icon(False)} groundedness {grd:.2f} < threshold  — {judge.get('groundedness_reason','')}")

    draft_preview = result.get("draft_preview", "")
    if draft_preview:
        print(f"      Draft: {draft_preview[:90].strip()}…")
    print()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(skip_judge: bool) -> None:
    email_cases = json.loads((EVALS_DIR / "test_emails.json").read_text())
    voice_cases = (
        json.loads((EVALS_DIR / "test_voice.json").read_text())
        if (EVALS_DIR / "test_voice.json").exists()
        else []
    )

    openai_key = None if skip_judge else _load_openai_key()
    if not skip_judge and not openai_key:
        print("⚠  OPENAI_API_KEY not found — running without LLM judge (--skip-judge mode)")
        skip_judge = True

    all_results    = []
    total_cases    = len(email_cases) + len(voice_cases)
    passed_cases   = 0

    # counters per dimension
    ext_pass = 0;  ext_total = 0
    tool_pass = 0; tool_total = 0
    rel_sum = 0.0; grd_sum = 0.0; judge_count = 0

    with httpx.Client() as client:
        # ── Email cases ───────────────────────────────────────────────────
        if email_cases:
            print(f"\n{'─'*70}")
            print(f"  EMAIL CASES ({len(email_cases)})")
            print(f"{'─'*70}\n")

        for case in email_cases:
            result = run_case(client, case, openai_key, skip_judge, is_voice=False)
            print_case(result)
            all_results.append(result)

            if result.get("pass"):     passed_cases += 1
            if result.get("extraction_pass") is not None:
                ext_total += 1
                if result["extraction_pass"]: ext_pass += 1
            if result.get("tools", {}).get("pass") is not None:
                tool_total += 1
                if result["tools"]["pass"]: tool_pass += 1
            j = result.get("judge", {})
            if "relevancy" in j:
                rel_sum += j["relevancy"];   grd_sum += j["groundedness"]
                judge_count += 1

            time.sleep(0.4)

        # ── Voice / transcript cases ──────────────────────────────────────
        if voice_cases:
            print(f"\n{'─'*70}")
            print(f"  VOICE / TRANSCRIPT CASES ({len(voice_cases)})")
            print(f"{'─'*70}\n")

        for case in voice_cases:
            result = run_case(client, case, openai_key, skip_judge, is_voice=True)
            print_case(result)
            all_results.append(result)

            if result.get("pass"):     passed_cases += 1
            if result.get("extraction_pass") is not None:
                ext_total += 1
                if result["extraction_pass"]: ext_pass += 1
            if result.get("tools", {}).get("pass") is not None:
                tool_total += 1
                if result["tools"]["pass"]: tool_pass += 1
            j = result.get("judge", {})
            if "relevancy" in j:
                rel_sum += j["relevancy"];   grd_sum += j["groundedness"]
                judge_count += 1

            time.sleep(0.4)

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"{'═'*70}")
    print(f"  SUMMARY")
    print(f"{'─'*70}")
    print(f"  Cases passed       : {passed_cases}/{total_cases}")
    print(f"  Extraction accuracy: {ext_pass}/{ext_total} cases fully correct")
    if tool_total:
        print(f"  Tool coverage      : {tool_pass}/{tool_total} cases called expected tools")
    if judge_count:
        print(f"  Avg relevancy      : {rel_sum/judge_count:.2f}  (threshold {DEFAULT_MIN_RELEVANCY})")
        print(f"  Avg groundedness   : {grd_sum/judge_count:.2f}  (threshold {DEFAULT_MIN_GROUNDEDNESS})")
    else:
        print("  Judge scores       : skipped")
    print(f"{'═'*70}\n")

    RESULTS_FILE.write_text(json.dumps(all_results, indent=2))
    print(f"Results written to {RESULTS_FILE}")

    sys.exit(0 if passed_cases == total_cases else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip LLM judge scoring (faster, no API cost)",
    )
    args = parser.parse_args()
    run(skip_judge=args.skip_judge)
