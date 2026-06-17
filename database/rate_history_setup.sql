-- ============================================================
-- rate_history — weekly per-mile rate data by lane + equipment
--
-- avg_rate / min_rate / max_rate are $/mile (not total USD).
-- week_start is the Monday of each reporting week.
-- Run this in Supabase SQL Editor.
-- ============================================================

CREATE TABLE IF NOT EXISTS rate_history (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start        DATE NOT NULL,
    origin_state      TEXT NOT NULL,
    destination_state TEXT NOT NULL,
    equipment_type    TEXT NOT NULL,
    avg_rate          FLOAT,
    min_rate          FLOAT,
    max_rate          FLOAT,
    load_volume       INTEGER,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_history_lane      ON rate_history(origin_state, destination_state);
CREATE INDEX IF NOT EXISTS idx_rate_history_week      ON rate_history(week_start DESC);
CREATE INDEX IF NOT EXISTS idx_rate_history_equipment ON rate_history(equipment_type);

-- ============================================================
-- Seed data (from your existing rate data — PA→MD, Box Truck)
-- ============================================================

INSERT INTO rate_history (week_start, origin_state, destination_state, equipment_type, avg_rate, min_rate, max_rate, load_volume)
VALUES
    ('2025-12-01', 'PA', 'MD', 'Box Truck', 5.01, 4.41, 5.91, 7),
    ('2025-12-08', 'PA', 'MD', 'Box Truck', 4.90, 4.31, 5.78, 15),
    ('2025-12-15', 'PA', 'MD', 'Box Truck', 4.51, 3.97, 5.32, 8),
    ('2025-12-22', 'PA', 'MD', 'Box Truck', 4.45, 3.92, 5.25, 15)
ON CONFLICT DO NOTHING;
