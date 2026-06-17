import { useRef, useState } from "react";
import {
  useBackfillVoiceCalls,
  useProcessVoiceCall,
  useUploadVoiceCall,
  useVoiceCalls,
  useVoiceDetail,
} from "../hooks/useVoice";
import { useApproveDraft, useRejectDraft } from "../hooks/useEmails";
import { StatusBadge } from "./StatusBadge";
import type { VoiceCallSummary } from "../types";

// ---------------------------------------------------------------------------
// Intent label map (reused from email inbox)
// ---------------------------------------------------------------------------
const INTENT_LABELS: Record<string, string> = {
  availability: "Availability",
  counter_offer: "Counter Offer",
  rate_quote: "Rate Quote",
  information_request: "Info Request",
  booking_interest: "Booking",
  load_question: "Load Question",
  general_inquiry: "General",
};

// ---------------------------------------------------------------------------
// Upload button
// ---------------------------------------------------------------------------
function UploadButton() {
  const fileRef = useRef<HTMLInputElement>(null);
  const upload = useUploadVoiceCall();
  const [showForm, setShowForm] = useState(false);
  const [callerName, setCallerName] = useState("");
  const [callerPhone, setCallerPhone] = useState("");
  const [mcNumber, setMcNumber] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setShowForm(true);
    }
  }

  function handleUpload() {
    if (!selectedFile) return;
    const fd = new FormData();
    fd.append("file", selectedFile);
    if (callerName) fd.append("caller_name", callerName);
    if (callerPhone) fd.append("caller_phone", callerPhone);
    if (mcNumber) fd.append("mc_number", mcNumber);

    upload.mutate(fd, {
      onSuccess: () => {
        setShowForm(false);
        setSelectedFile(null);
        setCallerName("");
        setCallerPhone("");
        setMcNumber("");
        if (fileRef.current) fileRef.current.value = "";
      },
    });
  }

  return (
    <div>
      <input
        ref={fileRef}
        type="file"
        accept=".wav,.mp3,.mp4,.m4a"
        className="hidden"
        onChange={handleFileChange}
      />

      {!showForm ? (
        <button
          onClick={() => fileRef.current?.click()}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          Upload WAV
        </button>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3 min-w-[300px]">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-700 truncate max-w-[200px]">
              {selectedFile?.name}
            </p>
            <button
              onClick={() => { setShowForm(false); setSelectedFile(null); }}
              className="text-gray-400 hover:text-gray-600 text-lg leading-none"
            >
              ×
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Caller name", value: callerName, set: setCallerName, placeholder: "Alex Rivera" },
              { label: "Caller phone", value: callerPhone, set: setCallerPhone, placeholder: "215-555-0100" },
              { label: "MC number", value: mcNumber, set: setMcNumber, placeholder: "445521" },
            ].map(({ label, value, set, placeholder }) => (
              <div key={label} className={label === "Caller name" ? "col-span-2" : ""}>
                <label className="block text-xs text-gray-400 mb-0.5">{label}</label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => set(e.target.value)}
                  placeholder={placeholder}
                  className="w-full rounded border border-gray-200 px-2 py-1 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={upload.isPending}
            className="w-full rounded-md bg-indigo-600 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {upload.isPending ? "Uploading…" : "Upload"}
          </button>
          {upload.isError && (
            <p className="text-xs text-red-500">{(upload.error as Error).message}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Voice call list table
// ---------------------------------------------------------------------------
function VoiceTable({
  selectedCallId,
  onSelect,
}: {
  selectedCallId: string | null;
  onSelect: (id: string) => void;
}) {
  const { data: calls, isLoading, isError } = useVoiceCalls();
  const processCall = useProcessVoiceCall();

  function handleProcess(e: React.MouseEvent, callId: string) {
    e.stopPropagation();
    processCall.mutate(callId, { onSuccess: () => onSelect(callId) });
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-48 text-gray-400 text-sm">Loading…</div>;
  }
  if (isError) {
    return <div className="flex items-center justify-center h-48 text-red-500 text-sm">Failed to load voice calls.</div>;
  }
  if (!calls?.length) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-400 text-sm gap-1">
        <p>No voice calls yet.</p>
        <p className="text-xs">Upload a WAV file to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {["Call ID", "Caller", "Load ID", "Intent", "Status", "Action"].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {calls.map((call: VoiceCallSummary) => {
            const isSelected = call.call_id === selectedCallId;
            const isPending = call.processing_status === "pending";
            const isProcessing =
              processCall.isPending && processCall.variables === call.call_id;

            return (
              <tr
                key={call.call_id}
                onClick={() => onSelect(call.call_id)}
                className={`cursor-pointer transition-colors hover:bg-indigo-50 ${
                  isSelected ? "bg-indigo-50 border-l-2 border-indigo-500" : ""
                }`}
              >
                <td className="px-4 py-3 text-sm font-mono text-gray-700">
                  {call.call_id}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  <div className="flex flex-col">
                    <span>
                      {call.carrier_name ?? call.caller_name ?? (
                        <span className="text-gray-400 italic">Unknown caller</span>
                      )}
                    </span>
                    {(call.carrier_mc ?? call.mc_number) && (
                      <span className="text-xs text-gray-400 font-mono">
                        MC#{call.carrier_mc ?? call.mc_number}
                      </span>
                    )}
                    {call.caller_phone && (
                      <span className="text-xs text-gray-400">{call.caller_phone}</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-sm font-mono text-gray-700">
                  {call.load_id ?? <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {call.intent
                    ? INTENT_LABELS[call.intent] ?? call.intent
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={call.processing_status} />
                </td>
                <td className="px-4 py-3">
                  {isPending ? (
                    <button
                      onClick={(e) => handleProcess(e, call.call_id)}
                      disabled={isProcessing}
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing ? "Processing…" : "Process"}
                    </button>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); onSelect(call.call_id); }}
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                    >
                      Review
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Voice side panel
// ---------------------------------------------------------------------------
type PanelTab = "call" | "transcript" | "extraction" | "draft";

function VoiceSidePanel({
  callId,
  onClose,
}: {
  callId: string;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<PanelTab>("call");
  const { data, isLoading, isError } = useVoiceDetail(callId);
  const approveDraft = useApproveDraft();
  const rejectDraft = useRejectDraft();

  const tabs: { id: PanelTab; label: string }[] = [
    { id: "call", label: "Call" },
    { id: "transcript", label: "Transcript" },
    { id: "extraction", label: "Extraction" },
    { id: "draft", label: "Draft" },
  ];

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
        <div>
          <p className="text-xs text-gray-500 font-mono">{callId}</p>
          <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate max-w-xs">
            {data?.call.caller_name
              ? `Call from ${data.call.caller_name}`
              : data?.call.file_name ?? "Loading…"}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "border-b-2 border-indigo-500 text-indigo-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {isLoading && <div className="text-sm text-gray-400 text-center py-8">Loading…</div>}
        {isError && <div className="text-sm text-red-500 text-center py-8">Failed to load call details.</div>}

        {data && activeTab === "call" && (
          <div className="space-y-4">
            {[
              ["Call ID", data.call.call_id],
              ["File", data.call.file_name],
              ["Caller name", data.call.caller_name],
              ["Caller phone", data.call.caller_phone],
              ["MC number", data.call.mc_number],
              ["Status", data.call.processing_status],
            ].map(([label, value]) => value && (
              <div key={label}>
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
                {label === "Status" ? (
                  <div className="mt-1"><StatusBadge status={value} /></div>
                ) : (
                  <p className="text-sm text-gray-700 mt-0.5 font-mono">{value}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {data && activeTab === "transcript" && (
          <div>
            {data.call.transcript ? (
              <div className="rounded-md bg-gray-50 border border-gray-100 p-3">
                <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {data.call.transcript}
                </p>
              </div>
            ) : (
              <div className="text-sm text-gray-400 text-center py-8">
                No transcript yet. Process the call to transcribe.
              </div>
            )}
          </div>
        )}

        {data && activeTab === "extraction" && (
          <div>
            {!data.extraction ? (
              <div className="text-sm text-gray-400 text-center py-8">
                Not yet processed. Click "Process" in the table to run the agent.
              </div>
            ) : (
              <div className="space-y-4">
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
                  {(
                    [
                      ["Intent", data.extraction.intent],
                      ["Carrier Name", data.extraction.carrier_name],
                      ["MC Number", data.extraction.carrier_mc],
                      ["Load ID", data.extraction.load_id],
                      ["Equipment", data.extraction.equipment_type],
                      ["Quoted Rate", data.extraction.quoted_rate != null ? `$${data.extraction.quoted_rate}` : null],
                      ["Availability", data.extraction.availability_status != null ? (data.extraction.availability_status ? "Available" : "Unavailable") : null],
                      ["Confidence", data.extraction.confidence_score != null ? `${Math.round(data.extraction.confidence_score * 100)}%` : null],
                      ["Needs Review", data.extraction.needs_review ? "Yes" : "No"],
                    ] as [string, string | null][]
                  ).map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-xs text-gray-400 font-medium">{label}</dt>
                      <dd className="text-sm text-gray-800 mt-0.5 font-mono">
                        {value ?? <span className="text-gray-400 font-sans italic">—</span>}
                      </dd>
                    </div>
                  ))}
                </dl>

                {data.extraction.questions_asked.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-400 font-medium mb-1">Questions Asked</p>
                    <ul className="space-y-1">
                      {data.extraction.questions_asked.map((q, i) => (
                        <li key={i} className="text-sm text-gray-700 bg-gray-50 rounded px-2 py-1">{q}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.extraction.missing_fields.length > 0 && (
                  <div className="rounded-md bg-amber-50 border border-amber-200 p-3">
                    <p className="text-xs font-medium text-amber-700 mb-1">Missing Fields</p>
                    <div className="flex flex-wrap gap-1">
                      {data.extraction.missing_fields.map((f) => (
                        <span key={f} className="text-xs bg-amber-100 text-amber-800 rounded px-2 py-0.5 font-mono">{f}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {data && activeTab === "draft" && (
          <div>
            {!data.draft ? (
              <div className="text-sm text-gray-400 text-center py-8">
                No draft yet. Process the call to generate a response.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Draft status:</span>
                  <StatusBadge status={data.draft.draft_status} />
                </div>
                <div className="rounded-md bg-gray-50 border border-gray-100 p-3">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                    {data.draft.draft_text}
                  </p>
                </div>
                {data.draft.draft_status === "drafted" && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => approveDraft.mutate(data.draft!.id)}
                      disabled={approveDraft.isPending}
                      className="flex-1 rounded-md bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {approveDraft.isPending ? "Approving…" : "Approve"}
                    </button>
                    <button
                      onClick={() => rejectDraft.mutate(data.draft!.id)}
                      disabled={rejectDraft.isPending}
                      className="flex-1 rounded-md bg-red-50 py-2 text-sm font-medium text-red-600 border border-red-200 hover:bg-red-100 disabled:opacity-50 transition-colors"
                    >
                      {rejectDraft.isPending ? "Rejecting…" : "Reject"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main VoiceTab
// ---------------------------------------------------------------------------
export function VoiceTab() {
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);
  const { data: calls } = useVoiceCalls();
  const pendingCount = calls?.filter((c) => c.processing_status === "pending").length ?? 0;
  const processCall = useProcessVoiceCall();
  const backfill = useBackfillVoiceCalls();

  return (
    <div className="flex flex-1 overflow-hidden h-full">
      {/* Main panel */}
      <main
        className={`flex-1 overflow-y-auto transition-all duration-200 ${
          selectedCallId ? "max-w-[60%]" : "w-full"
        }`}
      >
        <div className="px-6 py-4">
          {/* Header row */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-gray-700">
                Voice Calls
                {calls && (
                  <span className="ml-2 text-gray-400 font-normal">({calls.length} calls)</span>
                )}
              </h2>
              {pendingCount > 0 && (
                <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-0.5">
                  {pendingCount} pending
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Sync button — for files already in Supabase Storage but not in DB */}
              <button
                onClick={() =>
                  backfill.mutate(undefined, {
                    onSuccess: (res) => {
                      if (res.synced > 0) {
                        setBackfillMsg(`Synced ${res.synced} new file${res.synced > 1 ? "s" : ""} from storage.`);
                      } else {
                        setBackfillMsg("All storage files are already tracked.");
                      }
                      setTimeout(() => setBackfillMsg(null), 4000);
                    },
                  })
                }
                disabled={backfill.isPending}
                title="Sync files uploaded directly to Supabase Storage"
                className="rounded-md border border-gray-300 text-gray-600 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-40 transition-colors"
              >
                {backfill.isPending ? "Syncing…" : "Sync Storage"}
              </button>

              {pendingCount > 0 && (
                <button
                  onClick={() => {
                    const pending = calls?.find((c) => c.processing_status === "pending");
                    if (pending) processCall.mutate(pending.call_id);
                  }}
                  disabled={processCall.isPending}
                  className="rounded-md border border-indigo-300 text-indigo-600 px-3 py-1.5 text-sm font-medium hover:bg-indigo-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {processCall.isPending ? "Processing…" : "Process Next"}
                </button>
              )}
              <UploadButton />
            </div>
          </div>

          {/* Backfill result banner */}
          {backfillMsg && (
            <div className="mb-3 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
              {backfillMsg}
            </div>
          )}

          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <VoiceTable
              selectedCallId={selectedCallId}
              onSelect={setSelectedCallId}
            />
          </div>
        </div>
      </main>

      {/* Side panel */}
      {selectedCallId && (
        <aside className="w-[480px] shrink-0 overflow-hidden flex flex-col">
          <VoiceSidePanel
            callId={selectedCallId}
            onClose={() => setSelectedCallId(null)}
          />
        </aside>
      )}
    </div>
  );
}
