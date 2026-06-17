-- Seed data for Goodlane Freight Broker Inbox Assistant
-- Run after schema.sql

-- ============================================================
-- Carriers
-- ============================================================
INSERT INTO carriers (
    mc_number, dot_number, company_name, primary_contact, email, phone, address,
    equipment_types, preferred_lanes, home_base_zip,
    factoring_company, payment_terms_preference,
    reliability_score, loads_completed_with_goodlane, avg_response_time_hours,
    insurance_expiry, authority_status, safety_rating, notes, onboarded
)
VALUES
    -- Email seed carriers (MC numbers referenced in emails CE0042–CE0051)
    (
        '774321', '2019341', 'Priyanka Transport LLC', 'Priya Sharma',
        'priyanka@ptransport.com', '(484) 555-2001',
        '821 Stefko Blvd, Bethlehem, PA 18017',
        '["Sprinter Van", "Box Truck"]', '["PA-NJ", "PA-NY"]', '18017',
        NULL, 'standard',
        4.2, 7, 0.8,
        '2027-03-15', 'ACTIVE', 'Satisfactory',
        'Reliable on short PA-NJ runs. Prefers morning pickups.', TRUE
    ),
    (
        '882910', '1654320', 'Blue Ridge Haulers', 'Marcus Webb',
        'ops@blueridgehaulers.com', '(856) 555-3002',
        '412 Market St, Camden, NJ 08102',
        '["Box Truck"]', '["NJ-NY", "NJ-PA"]', '08102',
        'OTR Capital', 'factored',
        3.8, 4, 2.1,
        '2026-11-30', 'ACTIVE', 'Satisfactory',
        'Occasionally slow to confirm. Uses factoring — verify pay setup before booking.', TRUE
    ),
    (
        '991234', '2301887', 'FastLane Freight Inc', 'Tony Ricci',
        'dispatch@fastlane.com', '(215) 555-4003',
        '5550 Grays Ave, Philadelphia, PA 19143',
        '["Box Truck", "Flatbed"]', '["PA-MD", "PA-NJ", "PA-NY"]', '19143',
        NULL, 'standard',
        4.7, 12, 0.4,
        '2027-06-01', 'ACTIVE', 'Satisfactory',
        'Top performer. Books quickly and shows on time consistently.', TRUE
    ),
    (
        '445567', '1889023', 'Sunrise Logistics', 'Linda Torres',
        'hello@sunriselog.com', '(973) 555-5004',
        '88 Commerce Dr, Newark, NJ 07102',
        '["Box Truck", "Sprinter Van"]', '["NJ-PA", "NJ-NY"]', '07102',
        NULL, 'standard',
        2.9, 1, 4.5,
        '2025-12-31', 'INACTIVE', 'Conditional',
        'Insurance expired — do not dispatch until renewed. Partnership inquiry only.', FALSE
    ),
    (
        '663389', '2145670', 'Midwest Express Carriers', 'James Kowalski',
        'midwest@mexpress.com', '(609) 555-6005',
        '230 Broad St, Trenton, NJ 08608',
        '["Flatbed", "Sprinter Van"]', '["NJ-MD", "NJ-PA", "NJ-CT"]', '08608',
        'Triumph Business Capital', 'factored',
        4.0, 5, 1.6,
        '2027-09-20', 'ACTIVE', 'Satisfactory',
        NULL, TRUE
    ),

    -- Real carriers from Goodlane network
    (
        '776491', '2273558', 'SMR TRUCKING INC', 'Rummy Singh',
        'rummy@smrtrucking.com', NULL,
        '1600 Uhler Road, Easton, PA 18045',
        '["Box Truck"]', '["PA-NJ", "PA-DE"]', '18045',
        NULL, 'standard',
        4.2, 3, 1.2,
        '2027-03-15', 'ACTIVE', 'Satisfactory',
        'Responds quickly. Completed 29372289 (Reading-Wilmington) 5/20.', TRUE
    ),
    (
        '538772', '1188521', 'CHAHAL TRUCKING INC', NULL,
        'chahaltrucking@gmail.com', '(610) 438-0512',
        'Easton, PA 18045',
        '["Box Truck", "Sprinter Van"]', '["PA-NJ"]', '18045',
        'Triumph Business Capital', 'factored',
        3.8, 1, 0.5,
        '2026-11-30', 'ACTIVE', 'Satisfactory',
        NULL, TRUE
    )

ON CONFLICT (mc_number) DO NOTHING;

-- ============================================================
-- Loads  (sourced from actual Goodlane load board)
-- ============================================================
INSERT INTO loads (load_id, origin_city, origin_state, origin_zip, destination_city, destination_state, destination_zip, distance_miles, equipment_type, weight_lbs, pickup_date, pickup_window, delivery_date, offered_rate_usd, status, shipper_name, internal_notes)
VALUES
    -- Referenced by email CE0042 (counter offer at $280 vs posted $240)
    ('29372312', 'Bethlehem',    'PA', '18015', 'Camden',      'NJ', '08103', 71,  'Sprinter Van', NULL,  '2026-05-20', '09:00-12:00', '2026-05-21', 240.00, 'open',      'Jumpstart Athletics', NULL),

    -- Referenced by email CE0045 (load question — pickup address, lumper fee)
    ('29372490', 'Harrisburg',   'PA', '15219', 'Baltimore',   'MD', '21201', 195, 'Flatbed',      18000, '2026-05-26', '07:00',       NULL,         950.00, 'open',      NULL,                  'oversized?? confirm before dispatching'),

    -- Referenced by email CE0046 (booking interest)
    ('29372515', 'New York',     'NY', '10001', 'Boston',      'MA', '02101', 220, 'Box Truck',    5200,  '2026-05-27', '06:00',       '2026-05-28', 875.00, 'open',      NULL,                  NULL),

    -- Referenced by email CE0048 (counter offer $350 vs posted rate)
    ('29372450', 'Philadelphia', 'PA', '19146', 'New York',    'NY', '10001', 97,  'Box Truck',    4100,  '2026-05-23', '08:00-12:00', '2026-05-23', 320.00, 'open',      'Jumpstart Athletics', 'needs liftgate'),

    -- Referenced by email CE0051 (rate check — $275 seems low)
    ('29372394', 'Easton',       'PA', '18045', 'Trenton',     'NJ', '08619', 54,  'Box Truck',    NULL,  '2026-05-20', '08:00-17:00', NULL,         275.00, 'open',      NULL,                  'office materials, no dock'),

    -- Additional loads for realistic board volume
    ('29372360', 'Reading',      'PA', '19601', 'Wilmington',  'DE', '19801', 82,  'Box Truck',    2800,  '2026-05-20', '09:00-12:00', '2026-05-20', 310.00, 'delivered', 'Goodlane Internal',   'completed - carrier showed early'),
    ('29372399', 'Allentown',    'PA', '18101', 'Philadelphia','PA', '19103', 60,  'Box Truck',    3200,  '2026-05-22', '07:00-15:00', NULL,         250.00, 'open',      'Goodlane Internal',   'fragile - handle with care'),
    ('29372421', 'Trenton',      'NJ', '08609', 'Newark',      'NJ', '07102', 45,  'Box Truck',    NULL,  '2026-05-22', '10:00',       NULL,         220.00, 'open',      NULL,                  'time window TBD by shipper'),
    ('29372501', 'Camden',       'NJ', '08103', 'Baltimore',   'MD', '21201', 115, 'Refrigerated', 8500,  '2026-05-25', NULL,          NULL,         520.00, 'open',      NULL,                  'temp controlled 34-38°F'),
    ('29000138', 'Camden',       'NJ', '08103', 'Yonkers',     'NY', '10701', 206, 'Box Truck',    15219, '2026-09-12', '09:00-12:00', NULL,         460.00, 'open',      'Iron Bridge Mfg',     NULL),
    ('29000279', 'Harrisburg',   'PA', '17101', 'Trenton',     'NJ', '07201', 200, 'Sprinter Van', 19418, '2026-03-25', '07:00-14:00', '2026-03-27', 365.00, 'delivered', 'Goodlane Building Materials', 'temp controlled 35-40°F'),
    ('29000392', 'Trenton',      'NJ', '08619', 'Brooklyn',    'NY', '11201', 137, 'Flatbed',      12454, '2026-03-21', '06:00',       '2026-03-22', 525.00, 'delivered', 'Republic Building Materials',  'hazmat class 3 - verify carrier cert'),
    ('29000496', 'Wilmington',   'DE', '19801', 'Newark',      'NJ', '07201', 102, 'Sprinter Van', 21471, '2026-05-11', '06:00-12:00', '2026-05-11', 420.00, 'delivered', 'Northeast Distribution', NULL),
    ('29000604', 'Harrisburg',   'PA', '17101', 'Dover',       'DE', '17401', 185, 'Box Truck',    21977, '2026-05-03', '09:00-12:00', '2026-05-04', 745.00, 'covered',   'Cardinal Foods',      NULL),
    ('29000660', 'Albany',       'NY', '17401', 'York',        'PA', '17401', 189, 'Box Truck',    NULL,  '2026-03-18', '08:00-17:00', NULL,         635.00, 'open',      NULL,                  NULL)

ON CONFLICT (load_id) DO NOTHING;

-- ============================================================
-- Emails (10 test emails covering all 7 intents)
-- Load references updated to match real loads above
-- ============================================================
INSERT INTO emails (email_id, from_name, from_email, to_email, subject, body, mc_number, load_reference, equipment_mentioned, rate_quoted_usd, intent, processing_status)
VALUES
    -- 1. counter_offer — carrier counters $240 posted rate on 29372312
    ('CE0042',
     'Priya Sharma', 'priyanka@ptransport.com', 'dispatch@goodlanelogistics.com',
     'Load #29372312 availability',
     'Hi team, we can do this load but not at $240. Our floor on this lane is $280. Please let us know if that works.',
     '774321', '29372312', 'Sprinter Van', 280.00, NULL,
     'pending'),

    -- 2. rate_quote — asking about NJ to NY rates, no specific load
    ('CE0043',
     'Marcus Webb', 'ops@blueridgehaulers.com', 'dispatch@goodlanelogistics.com',
     'Rate inquiry NJ to NY Box Truck',
     'Hello, we have box trucks running out of Camden NJ toward New York. What rates are you offering for this lane this week?',
     '882910', NULL, 'Box Truck', NULL, NULL,
     'pending'),

    -- 3. availability — flatbed available in PA
    ('CE0044',
     'Tony Ricci', 'dispatch@fastlane.com', 'dispatch@goodlanelogistics.com',
     'Flatbed available Harrisburg PA area',
     'Good morning. We have a flatbed available in Harrisburg PA area starting May 26th. Do you have any loads going to Maryland? MC# 991234.',
     '991234', NULL, 'Flatbed', NULL, NULL,
     'pending'),

    -- 4. load_question — asking about pickup address and lumper on 29372490
    ('CE0045',
     'James Kowalski', 'midwest@mexpress.com', 'dispatch@goodlanelogistics.com',
     'Question about load 29372490',
     'Hi, we saw load 29372490 on the board. Can you confirm the exact pickup address in Harrisburg and whether there is a lumper fee at delivery in Baltimore? MC 663389.',
     '663389', '29372490', 'Flatbed', NULL, NULL,
     'pending'),

    -- 5. booking_interest — wants to book 29372515
    ('CE0046',
     'Tony Ricci', 'dispatch@fastlane.com', 'dispatch@goodlanelogistics.com',
     'Interested in load 29372515',
     'Hello Goodlane team, we want to book load 29372515. Our box truck is available and we are comfortable with the posted rate. How do we confirm? MC 991234.',
     '991234', '29372515', 'Box Truck', NULL, NULL,
     'pending'),

    -- 6. information_request — missing MC number
    ('CE0047',
     'Sarah Kim', 'newcarrier@gmail.com', 'dispatch@goodlanelogistics.com',
     'How do I get set up as a carrier?',
     'Hi there, I am a new carrier and I would like to know what I need to do to start hauling loads for Goodlane. What documents do you need?',
     NULL, NULL, NULL, NULL, NULL,
     'pending'),

    -- 7. counter_offer with question on 29372450
    ('CE0048',
     'Marcus Webb', 'ops@blueridgehaulers.com', 'dispatch@goodlanelogistics.com',
     'Re: Load 29372450 counter',
     'We can do load 29372450 Philadelphia to New York. Our rate is $350 for the box truck. Also, is there a TONU policy if the load gets cancelled? MC 882910.',
     '882910', '29372450', 'Box Truck', 350.00, NULL,
     'pending'),

    -- 8. general_inquiry — partnership outreach
    ('CE0049',
     'Linda Torres', 'hello@sunriselog.com', 'dispatch@goodlanelogistics.com',
     'General carrier partnership inquiry',
     'Hi Goodlane, Sunrise Logistics is looking to expand our carrier partnerships. We run NJ and PA lanes with box trucks and sprinter vans. Would love to connect.',
     '445567', NULL, 'Box Truck', NULL, NULL,
     'pending'),

    -- 9. availability — sprinter van available in NJ
    ('CE0050',
     'James Kowalski', 'midwest@mexpress.com', 'dispatch@goodlanelogistics.com',
     'Sprinter Van available Camden NJ',
     'We have a sprinter van available in Camden NJ this Friday. Looking for loads heading north toward New York or Connecticut. MC 663389.',
     '663389', NULL, 'Sprinter Van', NULL, NULL,
     'pending'),

    -- 10. rate_quote — questioning posted rate on 29372394
    ('CE0051',
     'Priya Sharma', 'priyanka@ptransport.com', 'dispatch@goodlanelogistics.com',
     'Rate check load 29372394',
     'Hi, checking on load 29372394 Easton PA to Trenton NJ. The posted rate of $275 seems low for a box truck on this run. Is there any flexibility? MC 774321.',
     '774321', '29372394', 'Box Truck', NULL, NULL,
     'pending')

ON CONFLICT (email_id) DO NOTHING;
