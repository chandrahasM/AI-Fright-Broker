import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { runChat } from "../api/chat";
import type { ChatRequest, ChatResponse } from "../types";

// ---------------------------------------------------------------------------
// Preset example messages for quick testing
// ---------------------------------------------------------------------------
const PRESETS: { label: string; value: ChatRequest }[] = [
  {
    label: "Rate history query",
    value: {
      message:
        "Hi, I run Box Trucks out of PA going to NJ. What have rates been like on that lane over the last few weeks? Looking to know if it's worth picking up loads there.",
      from_name: "Alex Rivera",
      from_email: "alex@riveratransport.com",
    },
  },
  {
    label: "Booking interest + MC",
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
    label: "Load question",
    value: {
      message:
        "Quick question on load #29001062 — is there a liftgate requirement? Also what's the pickup address? MC 887732.",
      from_name: "Sandra Park",
      from_email: "spark@parktransport.com",
      mc_number: "887732",
      load_reference: "29001062",
    },
  },
  {
    label: "Max rate this week",
    value: {
      message:
        "What's the highest per-mile rate anyone got on a Box Truck from MD to PA this week?",
      from_name: "Test User",
      equipment_mentioned: "Box Truck",
    },
  },
];

// ---------------------------------------------------------------------------
// Sub-components
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

function ExtractionCard({ result }: { result: ChatResponse }) {
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
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">Phase 1 — Extraction</span>
        <IntentBadge intent={e.intent} />
      </div>
      <div className="divide-y divide-gray-50">
        {rows.map(([label, val]) => (
          <div key={label} className="flex px-4 py-2 text-sm">
            <span className="w-36 shrink-0 text-gray-400">{label}</span>
            <span className="text-gray-800 font-medium">
              {val != null && val !== "" ? String(val) : <span className="text-gray-300 font-normal">—</span>}
            </span>
          </div>
        ))}
      </div>

      {e.questions_asked.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-100">
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
        <div className="px-4 py-2 bg-amber-50 border-t border-amber-100 flex items-start gap-2">
          <span className="text-amber-500 text-xs mt-0.5">⚠</span>
          <p className="text-xs text-amber-700">
            Missing required fields: <span className="font-medium">{e.missing_fields.join(", ")}</span>
          </p>
        </div>
      )}
    </div>
  );
}

function DraftCard({ draft }: { draft: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(draft);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">Phase 2 — Draft Response</span>
        <button
          onClick={copy}
          className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <div className="px-4 py-4">
        <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{draft}</p>
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

  const mutation = useMutation({ mutationFn: runChat });

  function applyPreset(preset: ChatRequest) {
    setMessage(preset.message);
    setFromName(preset.from_name ?? "");
    setFromEmail(preset.from_email ?? "");
    setMcNumber(preset.mc_number ?? "");
    setLoadRef(preset.load_reference ?? "");
    setEquipment(preset.equipment_mentioned ?? "");
    setRateQuoted(preset.rate_quoted_usd != null ? String(preset.rate_quoted_usd) : "");
    if (preset.mc_number || preset.load_reference || preset.equipment_mentioned || preset.rate_quoted_usd) {
      setShowOptional(true);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
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
    mutation.reset();
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto px-6 py-6 gap-6">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-gray-900">Agent Test</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Send a test message directly to the agent — no email needed. Results are not saved.
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

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Carrier message <span className="text-red-400">*</span>
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={5}
            placeholder="Type or paste the carrier's email body here…"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          />
        </div>

        {/* Optional context fields */}
        <div>
          <button
            type="button"
            onClick={() => setShowOptional((v) => !v)}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
          >
            <span>{showOptional ? "▾" : "▸"}</span>
            {showOptional ? "Hide" : "Add"} optional context (from_name, MC, load ref…)
          </button>

          {showOptional && (
            <div className="mt-3 grid grid-cols-2 gap-3">
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
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!message.trim() || mutation.isPending}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? "Running agent…" : "Run agent"}
          </button>
          {(mutation.data || mutation.isError) && (
            <button
              type="button"
              onClick={handleReset}
              className="text-sm text-gray-400 hover:text-gray-600"
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {/* Error */}
      {mutation.isError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}

      {/* Results */}
      {mutation.data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ExtractionCard result={mutation.data} />
          <DraftCard draft={mutation.data.draft} />
        </div>
      )}
    </div>
  );
}
