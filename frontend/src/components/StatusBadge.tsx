type Status = "pending" | "processed" | "needs_review" | string;

const STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  processed: "bg-green-100 text-green-700",
  needs_review: "bg-amber-100 text-amber-700",
  drafted: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  sent: "bg-purple-100 text-purple-700",
};

const LABELS: Record<string, string> = {
  pending: "Pending",
  processed: "Processed",
  needs_review: "Needs Review",
  drafted: "Drafted",
  approved: "Approved",
  rejected: "Rejected",
  sent: "Sent",
};

interface Props {
  status: Status;
}

export function StatusBadge({ status }: Props) {
  const style = STYLES[status] ?? "bg-gray-100 text-gray-500";
  const label = LABELS[status] ?? status;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}
