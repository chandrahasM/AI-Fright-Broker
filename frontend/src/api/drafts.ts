import type { DraftRecord } from "../types";
import client from "./client";

export async function generateDraft(emailId: string): Promise<DraftRecord> {
  const { data } = await client.post<DraftRecord>("/api/drafts/generate", {
    email_id: emailId,
  });
  return data;
}

export async function approveDraft(draftId: string): Promise<DraftRecord> {
  const { data } = await client.post<DraftRecord>("/api/drafts/approve", {
    draft_id: draftId,
  });
  return data;
}

export async function rejectDraft(draftId: string): Promise<DraftRecord> {
  const { data } = await client.post<DraftRecord>("/api/drafts/reject", {
    draft_id: draftId,
  });
  return data;
}
