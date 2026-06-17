import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  backfillVoiceCalls,
  fetchVoiceDetail,
  listVoiceCalls,
  processVoiceCall,
  uploadVoiceCall,
} from "../api/voice";

export const VOICE_CALLS_KEY = ["voice-calls"] as const;
export const voiceDetailKey = (id: string) => ["voice-call", id] as const;

export function useVoiceCalls() {
  return useQuery({
    queryKey: VOICE_CALLS_KEY,
    queryFn: listVoiceCalls,
    refetchInterval: 30_000,
  });
}

export function useVoiceDetail(callId: string | null) {
  return useQuery({
    queryKey: voiceDetailKey(callId ?? ""),
    queryFn: () => fetchVoiceDetail(callId!),
    enabled: !!callId,
  });
}

export function useUploadVoiceCall() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: uploadVoiceCall,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: VOICE_CALLS_KEY });
    },
  });
}

export function useProcessVoiceCall() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: processVoiceCall,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: VOICE_CALLS_KEY });
      queryClient.invalidateQueries({ queryKey: voiceDetailKey(data.call_id) });
    },
  });
}

export function useBackfillVoiceCalls() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: backfillVoiceCalls,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: VOICE_CALLS_KEY });
    },
  });
}
