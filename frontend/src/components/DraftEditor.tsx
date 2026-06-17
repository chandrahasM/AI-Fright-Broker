import { useState, useEffect } from "react";
import type { DraftRecord } from "../types";
import { useApproveDraft, useGenerateDraft, useRejectDraft } from "../hooks/useEmails";
import { StatusBadge } from "./StatusBadge";

interface Props {
  emailId: string;
  draft: DraftRecord | null;
}

export function DraftEditor({ emailId, draft }: Props) {
  const [draftText, setDraftText] = useState(draft?.draft_text ?? "");
  const approveDraft = useApproveDraft();
  const rejectDraft = useRejectDraft();
  const generateDraft = useGenerateDraft();

  // Sync local state when draft changes (e.g. after regen)
  useEffect(() => {
    setDraftText(draft?.draft_text ?? "");
  }, [draft?.id, draft?.draft_text]);

  if (!draft) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400 space-y-3">
        <p className="text-sm">No draft generated yet.</p>
        <p className="text-xs">Process the email to generate a draft response.</p>
      </div>
    );
  }

  const isTerminal = draft.draft_status === "approved" || draft.draft_status === "rejected";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          Draft status:
        </span>
        <StatusBadge status={draft.draft_status} />
      </div>

      <textarea
        value={draftText}
        onChange={(e) => setDraftText(e.target.value)}
        disabled={isTerminal}
        rows={10}
        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 font-mono leading-relaxed focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-500 resize-none"
        placeholder="Draft response will appear here…"
      />

      {!isTerminal && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => approveDraft.mutate(draft.id)}
            disabled={approveDraft.isPending}
            className="flex-1 rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {approveDraft.isPending ? "Approving…" : "Approve Draft"}
          </button>
          <button
            onClick={() => rejectDraft.mutate(draft.id)}
            disabled={rejectDraft.isPending}
            className="flex-1 rounded-md bg-red-50 px-3 py-2 text-sm font-medium text-red-600 border border-red-200 hover:bg-red-100 disabled:opacity-50 transition-colors"
          >
            {rejectDraft.isPending ? "Rejecting…" : "Reject Draft"}
          </button>
          <button
            onClick={() => generateDraft.mutate(emailId)}
            disabled={generateDraft.isPending}
            className="rounded-md bg-gray-100 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 disabled:opacity-50 transition-colors"
            title="Regenerate draft"
          >
            {generateDraft.isPending ? "…" : "↺"}
          </button>
        </div>
      )}

      {isTerminal && (
        <p className="text-xs text-gray-400 text-center">
          Draft has been {draft.draft_status}. Regenerate to create a new one.
        </p>
      )}

      {(approveDraft.isError || rejectDraft.isError || generateDraft.isError) && (
        <p className="text-xs text-red-500">Action failed. Please try again.</p>
      )}
    </div>
  );
}
