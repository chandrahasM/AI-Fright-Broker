import { useState } from "react";
import { useEmailDetail } from "../hooks/useEmails";
import { DraftEditor } from "./DraftEditor";
import { StatusBadge } from "./StatusBadge";

type Tab = "email" | "extraction" | "draft";

interface Props {
  emailId: string;
  onClose: () => void;
}

export function SidePanel({ emailId, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("email");
  const { data, isLoading, isError } = useEmailDetail(emailId);

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
        <div>
          <p className="text-xs text-gray-500 font-mono">{emailId}</p>
          <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate max-w-xs">
            {data?.email.subject ?? "Loading…"}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          aria-label="Close panel"
        >
          ×
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 shrink-0">
        {(["email", "extraction", "draft"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2.5 text-xs font-medium capitalize transition-colors ${
              activeTab === tab
                ? "border-b-2 border-indigo-500 text-indigo-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "draft" ? "Draft Response" : tab === "extraction" ? "Extraction" : "Email"}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {isLoading && (
          <div className="text-sm text-gray-400 text-center py-8">Loading…</div>
        )}
        {isError && (
          <div className="text-sm text-red-500 text-center py-8">Failed to load email details.</div>
        )}

        {data && activeTab === "email" && (
          <EmailTab email={data.email} />
        )}
        {data && activeTab === "extraction" && (
          <ExtractionTab extraction={data.extraction} />
        )}
        {data && activeTab === "draft" && (
          <DraftEditor emailId={emailId} draft={data.draft} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function EmailTab({ email }: { email: NonNullable<ReturnType<typeof useEmailDetail>["data"]>["email"] }) {
  return (
    <div className="space-y-4">
      <div>
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">From</span>
        <p className="text-sm text-gray-700 mt-0.5">
          {email.from_name && <span className="font-medium">{email.from_name} </span>}
          {email.from_email && <span className="text-gray-500">&lt;{email.from_email}&gt;</span>}
          {!email.from_name && !email.from_email && "—"}
        </p>
      </div>
      {email.to_email && (
        <div>
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">To</span>
          <p className="text-sm text-gray-500 mt-0.5">{email.to_email}</p>
        </div>
      )}
      <div>
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Subject</span>
        <p className="text-sm text-gray-700 mt-0.5">{email.subject ?? "—"}</p>
      </div>
      <div>
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Status</span>
        <div className="mt-1">
          <StatusBadge status={email.processing_status} />
        </div>
      </div>
      {(email.mc_number || email.load_reference || email.equipment_mentioned || email.rate_quoted_usd) && (
        <div className="rounded-md bg-gray-50 border border-gray-100 p-3 space-y-1">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Email Metadata</p>
          {email.mc_number && (
            <p className="text-xs text-gray-600">MC#: <span className="font-mono">{email.mc_number}</span></p>
          )}
          {email.load_reference && (
            <p className="text-xs text-gray-600">Load Ref: <span className="font-mono">{email.load_reference}</span></p>
          )}
          {email.equipment_mentioned && (
            <p className="text-xs text-gray-600">Equipment: {email.equipment_mentioned}</p>
          )}
          {email.rate_quoted_usd != null && (
            <p className="text-xs text-gray-600">Rate Quoted: <span className="font-mono">${email.rate_quoted_usd}</span></p>
          )}
        </div>
      )}
      <div>
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Body</span>
        <div className="mt-1.5 rounded-md bg-gray-50 border border-gray-100 p-3">
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {email.body ?? "(empty)"}
          </p>
        </div>
      </div>
    </div>
  );
}

function ExtractionTab({
  extraction,
}: {
  extraction: ReturnType<typeof useEmailDetail>["data"] extends undefined ? null : NonNullable<ReturnType<typeof useEmailDetail>["data"]>["extraction"];
}) {
  if (!extraction) {
    return (
      <div className="text-sm text-gray-400 text-center py-8">
        Not yet processed. Click "Process" in the inbox to extract data.
      </div>
    );
  }

  const fields: [string, unknown][] = [
    ["Intent", extraction.intent],
    ["Carrier Name", extraction.carrier_name],
    ["MC Number", extraction.carrier_mc],
    ["Load ID", extraction.load_id],
    ["Equipment Type", extraction.equipment_type],
    ["Quoted Rate", extraction.quoted_rate != null ? `$${extraction.quoted_rate}` : null],
    ["Availability", extraction.availability_status != null ? (extraction.availability_status ? "Available" : "Not Available") : null],
    ["Confidence", extraction.confidence_score != null ? `${(extraction.confidence_score * 100).toFixed(0)}%` : null],
    ["Needs Review", extraction.needs_review ? "Yes" : "No"],
  ];

  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-gray-400 font-medium">{label}</dt>
            <dd className="text-sm text-gray-800 mt-0.5 font-mono">
              {value != null ? String(value) : <span className="text-gray-400 font-sans italic">—</span>}
            </dd>
          </div>
        ))}
      </dl>

      {extraction.questions_asked.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 font-medium mb-1">Questions Asked</p>
          <ul className="space-y-1">
            {extraction.questions_asked.map((q, i) => (
              <li key={i} className="text-sm text-gray-700 bg-gray-50 rounded px-2 py-1">
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}

      {extraction.missing_fields.length > 0 && (
        <div className="rounded-md bg-amber-50 border border-amber-200 p-3">
          <p className="text-xs font-medium text-amber-700 mb-1">Missing Fields</p>
          <div className="flex flex-wrap gap-1">
            {extraction.missing_fields.map((f) => (
              <span key={f} className="text-xs bg-amber-100 text-amber-800 rounded px-2 py-0.5 font-mono">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
