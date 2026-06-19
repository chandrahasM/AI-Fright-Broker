import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { runChat } from "../api/chat";
import type { ChatRequest, ChatResponse } from "../types";

// ---------------------------------------------------------------------------
// Preset example messages
// ---------------------------------------------------------------------------
const PRESETS: { label: string; value: ChatRequest }[] = [
  {
    label: "Rate history — PA to NJ",
    value: {
      message:
        "Hi, I run Box Trucks out of PA going to NJ. What have rates been like on that lane over the last few weeks?",
      from_name: "Alex Rivera",
      from_email: "alex@riveratransport.com",
    },
  },
  {
    label: "Booking interest",
    value: {
      message:
        "Interested in load #29001091. I have a Sprinter Van available Friday. MC 445521.",
      from_name: "Maria Chen",
      from_email: "maria@cargoquick.net",
      mc_number: "445521",
      load_reference: "29001091",
      equipment_mentioned: "Sprinter Van",
    },
  },
  {
    label: "Counter offer",
    value: {
      message:
        "Saw load #29001055 posted. Can you do $1,800? That's the best I can do for a Box Truck run to Maryland. MC 334412.",
      from_name: "James Howell",
      from_email: "jhowell@quickfreight.com",
      mc_number: "334412",
      load_reference: "29001055",
      rate_quoted_usd: 1800,
    },
  },
  {
    label: "Open loads — PA to NJ",
    value: {
      message: "Are there any open loads going from PA to NJ right now?",
      from_name: "Internal",
    },
  },
  {
    label: "Max rate this week",
    value: {
      message:
        "What's the highest per-mile rate anyone got on a Box Truck from MD to PA this week?",
      from_name: "Internal",
      equipment_mentioned: "Box Truck",
    },
  },
];

// ---------------------------------------------------------------------------
// Intent badge
// ---------------------------------------------------------------------------
function IntentBadge({ intent }: { intent: string }) {
  const colors: Record<string, string> = {
    rate_quote: "bg-blue-100 text-blue-700",
    booking_interest: "bg-green-100 text-green-700",
    counter_offer: "bg-amber-100 text-amber-700",
    load_question: "bg-purple-100 text-purple-700",
    availability: "bg-teal-100 text-teal-700",
    information_request: "bg-gray-100 text-gray-700",
    general_inquiry: "bg-gray-100 text-gray-500",
  };
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[intent] ?? "bg-gray-100 text-gray-600"
      }`}
    >
      {intent.replace(/_/g, " ")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Accordion panel — used inside "View all details"
// ---------------------------------------------------------------------------
function AccordionSection({
  title,
  badge,
  children,
  defaultOpen = false,
}: {
  title: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {badge}
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="bg-white">{children}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase 1 extraction detail panel
// ---------------------------------------------------------------------------
function ExtractionDetail({ result }: { result: ChatResponse }) {
  const e = result.extraction;
  const rows: [string, string | number | boolean | null][] = [
    ["Intent", e.intent],
    ["Carrier name", e.carrier_name],
    ["MC number", e.mc_number],
    ["Load ID", e.load_id],
    ["Equipment", e.equipment_type],
    ["Quoted rate", e.quoted_rate != null ? `$${e.quoted_rate}` : null],
    ["Availability", e.availability_status != null ? String(e.availability_status) : null],
    ["Origin state", e.origin_state],
    ["Destination state", e.destination_state],
    ["Confidence", `${Math.round(e.confidence_score * 100)}%`],
  ];

  return (
    <div className="divide-y divide-gray-50">
      {rows.map(([label, val]) => (
        <div key={label} className="flex px-4 py-2 text-sm">
          <span className="w-36 shrink-0 text-gray-400">{label}</span>
          <span className="text-gray-800 font-medium">
            {val != null && val !== "" ? (
              String(val)
            ) : (
              <span className="text-gray-300 font-normal">—</span>
            )}
          </span>
        </div>
      ))}

      {e.questions_asked.length > 0 && (
        <div className="px-4 py-3">
          <p className="text-xs font-medium text-gray-400 mb-1.5">Questions asked</p>
          <ul className="space-y-1">
            {e.questions_asked.map((q, i) => (
              <li key={i} className="text-sm text-gray-700 flex gap-2">
                <span className="text-gray-300 shrink-0">›</span> {q}
              </li>
            ))}
          </ul>
        </div>
      )}

      {e.missing_fields.length > 0 && (
        <div className="px-4 py-2 bg-amber-50 flex items-start gap-2">
          <span className="text-amber-500 text-xs mt-0.5">⚠</span>
          <p className="text-xs text-amber-700">
            Missing fields:{" "}
            <span className="font-medium">{e.missing_fields.join(", ")}</span>
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Draft email detail panel (shown only inside accordion)
// ---------------------------------------------------------------------------
function DraftEmailDetail({ draftEmail }: { draftEmail: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(draftEmail);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <div className="px-4 py-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-gray-400">Ready to send or edit before sending</p>
        <button
          type="button"
          onClick={copy}
          className="text-xs text-indigo-500 hover:text-indigo-700 font-medium transition-colors"
        >
          {copied ? "Copied!" : "Copy email"}
        </button>
      </div>
      <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap border-l-2 border-indigo-200 pl-3">
        {draftEmail}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Answer card — primary result shown to the user
// ---------------------------------------------------------------------------
function AnswerCard({
  question,
  result,
}: {
  question: string;
  result: ChatResponse;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  return (
    <div className="flex flex-col gap-3">
      {/* Question bubble */}
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-3">
          <p className="text-sm text-white leading-relaxed whitespace-pre-wrap">{question}</p>
        </div>
      </div>

      {/* Answer bubble */}
      <div className="flex justify-start">
        <div className="max-w-[90%] flex flex-col gap-2">
          <div className="rounded-2xl rounded-tl-sm bg-white border border-gray-200 shadow-sm px-4 py-3">
            <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
              {result.answer}
            </p>
          </div>

          {/* View all details toggle */}
          <div className="px-1">
            <button
              type="button"
              onClick={() => setDetailsOpen((v) => !v)}
              className="text-xs text-indigo-500 hover:text-indigo-700 flex items-center gap-1 transition-colors font-medium"
            >
              <svg
                className={`w-3.5 h-3.5 transition-transform duration-200 ${detailsOpen ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              {detailsOpen ? "Hide details" : "View all details"}
            </button>
          </div>

          {/* Accordion details */}
          {detailsOpen && (
            <div className="flex flex-col gap-2 mt-1">
              <AccordionSection
                title="Phase 1 — Extraction"
                badge={<IntentBadge intent={result.extraction.intent} />}
                defaultOpen={false}
              >
                <ExtractionDetail result={result} />
              </AccordionSection>

              <AccordionSection
                title="Draft Email"
                defaultOpen
              >
                <DraftEmailDetail draftEmail={result.draft_email} />
              </AccordionSection>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function ChatTab() {
  const [message, setMessage] = useState("");
  const [showOptional, setShowOptional] = useState(false);
  const [fromName, setFromName] = useState("");
  const [fromEmail, setFromEmail] = useState("");
  const [mcNumber, setMcNumber] = useState("");
  const [loadRef, setLoadRef] = useState("");
  const [equipment, setEquipment] = useState("");
  const [rateQuoted, setRateQuoted] = useState("");
  // Keep track of the question text at the time of submission
  const [submittedQuestion, setSubmittedQuestion] = useState("");

  const mutation = useMutation({ mutationFn: runChat });

  function applyPreset(preset: ChatRequest) {
    setMessage(preset.message);
    setFromName(preset.from_name ?? "");
    setFromEmail(preset.from_email ?? "");
    setMcNumber(preset.mc_number ?? "");
    setLoadRef(preset.load_reference ?? "");
    setEquipment(preset.equipment_mentioned ?? "");
    setRateQuoted(preset.rate_quoted_usd != null ? String(preset.rate_quoted_usd) : "");
    if (
      preset.mc_number ||
      preset.load_reference ||
      preset.equipment_mentioned ||
      preset.rate_quoted_usd
    ) {
      setShowOptional(true);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setSubmittedQuestion(message.trim());
    mutation.mutate({
      message: message.trim(),
      from_name: fromName || undefined,
      from_email: fromEmail || undefined,
      mc_number: mcNumber || undefined,
      load_reference: loadRef || undefined,
      equipment_mentioned: equipment || undefined,
      rate_quoted_usd: rateQuoted ? parseFloat(rateQuoted) : undefined,
    });
  }

  function handleReset() {
    setMessage("");
    setFromName("");
    setFromEmail("");
    setMcNumber("");
    setLoadRef("");
    setEquipment("");
    setRateQuoted("");
    setSubmittedQuestion("");
    mutation.reset();
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto px-6 py-6 gap-5 max-w-3xl mx-auto w-full">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-gray-900">QnA</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Ask questions about carriers, loads, or rates. Results are not saved.
        </p>
      </div>

      {/* Preset chips */}
      <div>
        <p className="text-xs font-medium text-gray-400 mb-2">Quick examples</p>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => applyPreset(p.value)}
              className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 hover:border-indigo-400 hover:text-indigo-600 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Answer area */}
      {mutation.isError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}

      {mutation.isPending && (
        <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
          <span className="inline-block w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
          Running agent…
        </div>
      )}

      {mutation.data && (
        <AnswerCard question={submittedQuestion} result={mutation.data} />
      )}

      {/* Input form — pinned at the bottom feel by being last in the flow */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-auto pt-2">
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            placeholder="Ask about a carrier, load, rate, or anything freight-related…"
            className="w-full px-4 py-3 text-sm text-gray-800 placeholder-gray-300 focus:outline-none resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as unknown as React.FormEvent);
              }
            }}
          />
          <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100 bg-gray-50">
            <button
              type="button"
              onClick={() => setShowOptional((v) => !v)}
              className="text-xs text-gray-400 hover:text-indigo-600 flex items-center gap-1 transition-colors"
            >
              <span>{showOptional ? "▾" : "▸"}</span>
              {showOptional ? "Hide" : "Add"} context
            </button>
            <div className="flex items-center gap-2">
              {(mutation.data || mutation.isError) && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  Clear
                </button>
              )}
              <button
                type="submit"
                disabled={!message.trim() || mutation.isPending}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
              >
                {mutation.isPending ? (
                  "Running…"
                ) : (
                  <>
                    Ask
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Optional context fields */}
        {showOptional && (
          <div className="grid grid-cols-2 gap-3 p-4 rounded-xl border border-gray-200 bg-white">
            {[
              { label: "From name", value: fromName, set: setFromName, placeholder: "Alex Rivera" },
              { label: "From email", value: fromEmail, set: setFromEmail, placeholder: "alex@carrier.com" },
              { label: "MC number", value: mcNumber, set: setMcNumber, placeholder: "445521" },
              { label: "Load reference", value: loadRef, set: setLoadRef, placeholder: "29001091" },
              { label: "Equipment", value: equipment, set: setEquipment, placeholder: "Box Truck" },
              { label: "Rate quoted ($)", value: rateQuoted, set: setRateQuoted, placeholder: "1800" },
            ].map(({ label, value, set, placeholder }) => (
              <div key={label}>
                <label className="block text-xs font-medium text-gray-400 mb-1">{label}</label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => set(e.target.value)}
                  placeholder={placeholder}
                  className="w-full rounded-md border border-gray-200 px-2.5 py-1.5 text-sm text-gray-700 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            ))}
          </div>
        )}
      </form>
    </div>
  );
}
