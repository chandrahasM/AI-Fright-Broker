-- Goodlane Freight Broker Inbox Assistant
-- Run this in Supabase SQL Editor before seed.sql

CREATE TABLE IF NOT EXISTS carriers (
    mc_number                    TEXT PRIMARY KEY,
    dot_number                   TEXT,
    company_name                 TEXT,
    primary_contact              TEXT,
    email                        TEXT,
    phone                        TEXT,
    address                      TEXT,
    equipment_types              JSONB DEFAULT '[]',   -- e.g. ["Box Truck", "Sprinter Van"]
    preferred_lanes              JSONB DEFAULT '[]',   -- e.g. ["PA-NJ", "PA-DE"]
    home_base_zip                TEXT,
    factoring_company            TEXT,
    payment_terms_preference     TEXT DEFAULT 'standard', -- standard | factored | quick_pay
    reliability_score            FLOAT,
    loads_completed_with_goodlane INTEGER DEFAULT 0,
    avg_response_time_hours      FLOAT,
    insurance_expiry             DATE,
    authority_status             TEXT,
    safety_rating                TEXT,
    notes                        TEXT,
    onboarded                    BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS loads (
    load_id           TEXT PRIMARY KEY,
    origin_city       TEXT,
    origin_state      TEXT,
    origin_zip        TEXT,
    destination_city  TEXT,
    destination_state TEXT,
    destination_zip   TEXT,
    distance_miles    INTEGER,
    equipment_type    TEXT,
    weight_lbs        INTEGER,
    pickup_date       DATE,
    pickup_window     TEXT,
    delivery_date     DATE,
    offered_rate_usd  FLOAT,
    status            TEXT DEFAULT 'open',
    shipper_name      TEXT,
    internal_notes    TEXT
);

CREATE TABLE IF NOT EXISTS emails (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id            TEXT UNIQUE NOT NULL,
    from_name           TEXT,
    from_email          TEXT,
    to_email            TEXT,
    subject             TEXT,
    body                TEXT,
    mc_number           TEXT,
    load_reference      TEXT,
    equipment_mentioned TEXT,
    rate_quoted_usd     FLOAT,
    intent              TEXT,
    timestamp           TIMESTAMP DEFAULT NOW(),
    processing_status   TEXT DEFAULT 'pending'
    -- processing_status: pending | processed | needs_review
);

CREATE TABLE IF NOT EXISTS extracted_interactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id            TEXT NOT NULL,
    carrier_name        TEXT,
    carrier_mc          TEXT,
    load_id             TEXT,
    equipment_type      TEXT,
    quoted_rate         FLOAT,
    intent              TEXT,
    availability_status BOOLEAN,
    confidence_score    FLOAT,
    needs_review        BOOLEAN DEFAULT FALSE,
    questions_asked     JSONB DEFAULT '[]',
    missing_fields      JSONB DEFAULT '[]',
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS draft_responses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id     TEXT NOT NULL,
    draft_text   TEXT,
    draft_status TEXT DEFAULT 'drafted',
    -- draft_status: drafted | approved | rejected | sent
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rate_history (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start        DATE NOT NULL,          -- Monday of the week this data covers
    origin_state      TEXT NOT NULL,          -- two-letter state code, e.g. 'PA'
    destination_state TEXT NOT NULL,          -- two-letter state code, e.g. 'MD'
    equipment_type    TEXT NOT NULL,          -- e.g. 'Box Truck', 'Sprinter Van'
    avg_rate          FLOAT,                  -- avg rate per mile ($/mile) for the week
    min_rate          FLOAT,                  -- lowest rate per mile observed
    max_rate          FLOAT,                  -- highest rate per mile observed
    load_volume       INTEGER,                -- number of loads on this lane that week
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS voice_calls (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id           TEXT UNIQUE NOT NULL,      -- e.g. "VC-20260617-A1B2"
    file_name         TEXT NOT NULL,             -- original uploaded file name
    storage_path      TEXT NOT NULL,             -- path in Supabase Storage bucket
    caller_name       TEXT,
    caller_phone      TEXT,
    mc_number         TEXT,
    duration_seconds  INTEGER,
    transcript        TEXT,                      -- populated after Whisper transcription
    processing_status TEXT DEFAULT 'pending',    -- pending | processed | needs_review
    timestamp         TIMESTAMP DEFAULT NOW()
);

-- Indexes for common lookup patterns
CREATE INDEX IF NOT EXISTS idx_emails_processing_status ON emails(processing_status);
CREATE INDEX IF NOT EXISTS idx_extracted_interactions_email_id ON extracted_interactions(email_id);
CREATE INDEX IF NOT EXISTS idx_draft_responses_email_id ON draft_responses(email_id);
CREATE INDEX IF NOT EXISTS idx_draft_responses_status ON draft_responses(draft_status);
CREATE INDEX IF NOT EXISTS idx_rate_history_lane ON rate_history(origin_state, destination_state);
CREATE INDEX IF NOT EXISTS idx_rate_history_week ON rate_history(week_start DESC);
CREATE INDEX IF NOT EXISTS idx_rate_history_equipment ON rate_history(equipment_type);
CREATE INDEX IF NOT EXISTS idx_voice_calls_status ON voice_calls(processing_status);
