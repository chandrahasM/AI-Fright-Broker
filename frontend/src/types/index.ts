// Mirrors backend Pydantic models exactly

export interface EmailSummary {
  id: string;
  email_id: string;
  from_name: string | null;
  from_email: string | null;
  subject: string | null;
  processing_status: "pending" | "processed" | "needs_review";
  timestamp: string;
  carrier_name: string | null;
  carrier_mc: string | null;
  load_id: string | null;
  intent: string | null;
}

export interface EmailRecord {
  id: string;
  email_id: string;
  from_name: string | null;
  from_email: string | null;
  to_email: string | null;
  subject: string | null;
  body: string | null;
  mc_number: string | null;
  load_reference: string | null;
  equipment_mentioned: string | null;
  rate_quoted_usd: number | null;
  intent: string | null;
  timestamp: string;
  processing_status: string;
}

export interface StoredInteraction {
  id: string;
  email_id: string;
  carrier_name: string | null;
  carrier_mc: string | null;
  load_id: string | null;
  equipment_type: string | null;
  quoted_rate: number | null;
  intent: string | null;
  availability_status: boolean | null;
  confidence_score: number | null;
  needs_review: boolean;
  questions_asked: string[];
  missing_fields: string[];
  created_at: string;
}

export interface DraftRecord {
  id: string;
  email_id: string;
  draft_text: string;
  draft_status: "drafted" | "approved" | "rejected" | "sent";
  created_at: string;
}

export interface EmailDetail {
  email: EmailRecord;
  extraction: StoredInteraction | null;
  draft: DraftRecord | null;
}

export interface ProcessEmailResponse {
  email_id: string;
  extraction: StoredInteraction;
  draft: DraftRecord;
  status: string;
}

// Voice call types
export interface VoiceCallSummary {
  id: string;
  call_id: string;
  file_name: string;
  caller_name: string | null;
  caller_phone: string | null;
  mc_number: string | null;
  processing_status: "pending" | "processed" | "needs_review";
  timestamp: string;
  // Populated from extracted_interactions when available
  carrier_name: string | null;
  carrier_mc: string | null;
  load_id: string | null;
  intent: string | null;
}

export interface VoiceCallRecord {
  id: string;
  call_id: string;
  file_name: string;
  storage_path: string;
  caller_name: string | null;
  caller_phone: string | null;
  mc_number: string | null;
  duration_seconds: number | null;
  transcript: string | null;
  processing_status: string;
  timestamp: string;
}

export interface VoiceDetail {
  call: VoiceCallRecord;
  extraction: StoredInteraction | null;
  draft: DraftRecord | null;
}

export interface UploadVoiceResponse {
  call_id: string;
  file_name: string;
  processing_status: string;
}

export interface ProcessVoiceResponse {
  call_id: string;
  transcript_length: number;
  extraction: StoredInteraction;
  draft: DraftRecord;
  status: string;
}

export interface BackfillResponse {
  synced: number;
  already_tracked: number;
  new_call_ids: string[];
}

// Chat / dev-test types
export interface ChatRequest {
  message: string;
  subject?: string;
  from_name?: string;
  from_email?: string;
  mc_number?: string;
  load_reference?: string;
  equipment_mentioned?: string;
  rate_quoted_usd?: number;
}

export interface ChatExtraction {
  carrier_name: string | null;
  mc_number: string | null;
  load_id: string | null;
  equipment_type: string | null;
  quoted_rate: number | null;
  availability_status: boolean | null;
  origin_state: string | null;
  destination_state: string | null;
  intent: string;
  questions_asked: string[];
  missing_fields: string[];
  confidence_score: number;
}

export interface ChatResponse {
  email_id: string;
  extraction: ChatExtraction;
  answer: string;       // direct 2-4 sentence answer shown in the UI bubble
  draft_email: string;  // full email-style draft shown only in "View all details"
}
