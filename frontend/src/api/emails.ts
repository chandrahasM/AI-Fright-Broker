import type { EmailDetail, EmailSummary, ProcessEmailResponse } from "../types";
import client from "./client";

export async function fetchEmails(): Promise<EmailSummary[]> {
  const { data } = await client.get<EmailSummary[]>("/api/emails");
  return data;
}

export async function fetchEmailDetail(emailId: string): Promise<EmailDetail> {
  const { data } = await client.get<EmailDetail>(`/api/emails/${emailId}`);
  return data;
}

export async function processEmail(emailId: string): Promise<ProcessEmailResponse> {
  const { data } = await client.post<ProcessEmailResponse>("/api/process-email", {
    email_id: emailId,
  });
  return data;
}
