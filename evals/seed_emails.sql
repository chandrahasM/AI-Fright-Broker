-- Eval starter emails — run in Supabase SQL Editor before email evals.
-- Requires loads 29000873 and 29001048 to exist (see database/seed.sql).
-- ON CONFLICT resets processing_status to pending so evals can re-run.

INSERT INTO emails (
    email_id, from_name, from_email, to_email, subject, body,
    mc_number, load_reference, equipment_mentioned, rate_quoted_usd, intent,
    timestamp, processing_status
)
VALUES
    (
        'CE0229',
        'Nkechi Adeyemi', 'nkechi@sharparrowlogistics.com', 'dispatch@goodlanelogistics.com',
        'Confirmed – Load #29000873',
        E'Agreed on $375. Driver confirmed for 2026-05-02. Please send all load details to this email.\n\nThanks,\nNkechi',
        '109876', '29000873', 'Box Truck', NULL, 'confirm',
        '2026-04-27T02:00:00Z', 'pending'
    ),
    (
        'CE0255',
        'Rob Galloway', 'rob@mountainstatetransport.net', 'dispatch@goodlanelogistics.com',
        'Flatbed available – Reading to Columbus',
        'Can do. What''s the all-in?',
        '1198743', '29001048', 'Flatbed', NULL, 'terse',
        '2026-04-09T21:00:00Z', 'pending'
    ),
    (
        'CE0253',
        'Marie Vale', 'marie@bbkagent.com', 'dispatch@goodlanelogistics.com',
        'Flatbed available – Reading to Columbus',
        'Can do. What''s the all-in?',
        '166960', '29001048', 'Box Truck', NULL, 'terse',
        '2026-04-08T13:00:00Z', 'pending'
    ),
    (
        'CE0233',
        'Baraka Mwangi', 'baraka.tradewind@gmail.com', 'dispatch@goodlanelogistics.com',
        'Following up – load #29000873',
        E'We''re available. Rate?',
        '219876', '29000873', 'Sprinter Van', NULL, 'inquiry',
        '2026-04-26T21:00:00Z', 'pending'
    )
ON CONFLICT (email_id) DO UPDATE SET
    from_name           = EXCLUDED.from_name,
    from_email          = EXCLUDED.from_email,
    to_email            = EXCLUDED.to_email,
    subject             = EXCLUDED.subject,
    body                = EXCLUDED.body,
    mc_number           = EXCLUDED.mc_number,
    load_reference      = EXCLUDED.load_reference,
    equipment_mentioned = EXCLUDED.equipment_mentioned,
    rate_quoted_usd     = EXCLUDED.rate_quoted_usd,
    intent              = EXCLUDED.intent,
    timestamp           = EXCLUDED.timestamp,
    processing_status   = 'pending';
