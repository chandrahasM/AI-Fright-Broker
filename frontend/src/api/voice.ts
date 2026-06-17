import apiClient from "./client";
import type {
  BackfillResponse,
  ProcessVoiceResponse,
  UploadVoiceResponse,
  VoiceCallSummary,
  VoiceDetail,
} from "../types";

export async function listVoiceCalls(): Promise<VoiceCallSummary[]> {
  const { data } = await apiClient.get<VoiceCallSummary[]>("/api/voice-calls");
  return data;
}

export async function fetchVoiceDetail(call_id: string): Promise<VoiceDetail> {
  const { data } = await apiClient.get<VoiceDetail>(`/api/voice-calls/${call_id}`);
  return data;
}

export async function uploadVoiceCall(formData: FormData): Promise<UploadVoiceResponse> {
  const { data } = await apiClient.post<UploadVoiceResponse>("/api/voice-calls/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function processVoiceCall(call_id: string): Promise<ProcessVoiceResponse> {
  const { data } = await apiClient.post<ProcessVoiceResponse>("/api/voice-calls/process", { call_id });
  return data;
}

export async function backfillVoiceCalls(): Promise<BackfillResponse> {
  const { data } = await apiClient.post<BackfillResponse>("/api/voice-calls/backfill", {});
  return data;
}
