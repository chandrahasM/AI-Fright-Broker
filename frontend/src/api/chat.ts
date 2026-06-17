import apiClient from "./client";
import type { ChatRequest, ChatResponse } from "../types";

export async function runChat(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/api/chat", req);
  return data;
}
