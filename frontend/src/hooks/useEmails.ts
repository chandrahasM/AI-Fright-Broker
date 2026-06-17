import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchEmailDetail, fetchEmails, processEmail } from "../api/emails";
import { approveDraft, generateDraft, rejectDraft } from "../api/drafts";

export const EMAILS_KEY = ["emails"] as const;
export const emailDetailKey = (id: string) => ["email", id] as const;

export function useEmails() {
  return useQuery({
    queryKey: EMAILS_KEY,
    queryFn: fetchEmails,
    refetchInterval: 30_000, // poll every 30s to pick up new emails
  });
}

export function useEmailDetail(emailId: string | null) {
  return useQuery({
    queryKey: emailDetailKey(emailId ?? ""),
    queryFn: () => fetchEmailDetail(emailId!),
    enabled: !!emailId,
  });
}

export function useProcessEmail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: processEmail,
    onSuccess: (data) => {
      // Invalidate the inbox list and the specific email detail
      queryClient.invalidateQueries({ queryKey: EMAILS_KEY });
      queryClient.invalidateQueries({ queryKey: emailDetailKey(data.email_id) });
    },
  });
}

export function useGenerateDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateDraft,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: emailDetailKey(data.email_id) });
    },
  });
}

export function useApproveDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: approveDraft,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: emailDetailKey(data.email_id) });
      queryClient.invalidateQueries({ queryKey: EMAILS_KEY });
    },
  });
}

export function useRejectDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: rejectDraft,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: emailDetailKey(data.email_id) });
    },
  });
}
