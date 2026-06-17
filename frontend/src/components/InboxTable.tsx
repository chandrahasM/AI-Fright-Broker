import type { EmailSummary } from "../types";
import { useEmails, useProcessEmail } from "../hooks/useEmails";
import { StatusBadge } from "./StatusBadge";

const INTENT_LABELS: Record<string, string> = {
  availability: "Availability",
  counter_offer: "Counter Offer",
  rate_quote: "Rate Quote",
  information_request: "Info Request",
  booking_interest: "Booking",
  load_question: "Load Question",
  general_inquiry: "General",
};

interface Props {
  selectedEmailId: string | null;
  onSelectEmail: (emailId: string) => void;
}

export function InboxTable({ selectedEmailId, onSelectEmail }: Props) {
  const { data: emails, isLoading, isError } = useEmails();
  const processEmail = useProcessEmail();

  function handleProcess(e: React.MouseEvent, emailId: string) {
    e.stopPropagation();
    processEmail.mutate(emailId, {
      onSuccess: () => onSelectEmail(emailId),
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Loading inbox…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-64 text-red-500">
        Failed to load emails. Is the backend running?
      </div>
    );
  }

  if (!emails?.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Inbox is empty.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {["Email ID", "Carrier", "Load ID", "Intent", "Status", "Action"].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {emails.map((email: EmailSummary) => {
            const isSelected = email.email_id === selectedEmailId;
            const isPending = email.processing_status === "pending";
            const isProcessing =
              processEmail.isPending && processEmail.variables === email.email_id;

            return (
              <tr
                key={email.email_id}
                onClick={() => onSelectEmail(email.email_id)}
                className={`cursor-pointer transition-colors hover:bg-indigo-50 ${
                  isSelected ? "bg-indigo-50 border-l-2 border-indigo-500" : ""
                }`}
              >
                <td className="px-4 py-3 text-sm font-mono text-gray-700">
                  {email.email_id}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  <div className="flex flex-col">
                    <span>
                      {email.carrier_name ?? email.from_name ?? (
                        <span className="text-gray-400 italic">—</span>
                      )}
                    </span>
                    {email.carrier_mc && (
                      <span className="text-xs text-gray-400 font-mono">
                        MC#{email.carrier_mc}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-sm font-mono text-gray-700">
                  {email.load_id ?? <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {email.intent
                    ? INTENT_LABELS[email.intent] ?? email.intent
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={email.processing_status} />
                </td>
                <td className="px-4 py-3">
                  {isPending ? (
                    <button
                      onClick={(e) => handleProcess(e, email.email_id)}
                      disabled={isProcessing}
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing ? "Processing…" : "Process"}
                    </button>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); onSelectEmail(email.email_id); }}
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
