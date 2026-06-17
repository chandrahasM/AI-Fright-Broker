-- ============================================================
-- Carriers — Full roster (48 records)
--
-- FIXES APPLIED vs source JSON:
--   1. Two records had null mc_number (invalid — mc_number is PRIMARY KEY).
--      Assigned placeholder IDs:
--        'PENDING_HKR'       → HKR LOGISTICS LLC (MC# not yet verified)
--        'PENDING_BLUEEAGLE' → BLUE EAGLE LOGISTICS (MC# not yet provided)
--      Replace these once real MC numbers are confirmed.
--
--   2. HUSSEIN'S TRUCKING — apostrophe escaped as '' (SQL standard).
--
--   3. LAKESIDE FREIGHT LLC — preferred_lanes had duplicate "OH-PA".
--      Deduplicated to ["OH-PA","PA-OH"].
--
--   4. equipment_types and preferred_lanes cast to JSONB-compatible
--      JSON string literals.
-- ============================================================

INSERT INTO carriers (
    mc_number, dot_number, company_name, primary_contact, email, phone, address,
    equipment_types, preferred_lanes, home_base_zip,
    factoring_company, payment_terms_preference,
    reliability_score, loads_completed_with_goodlane, avg_response_time_hours,
    insurance_expiry, authority_status, safety_rating, notes, onboarded
) VALUES

('776491', '2273558', 'SMR TRUCKING INC', 'Rummy Singh', 'rummy@smrtrucking.com', NULL, '1600 Uhler Road, Easton, PA 18045',
 '["Box Truck"]', '["PA-NJ","PA-DE"]', '18045',
 NULL, 'standard', 4.2, 3, 1.2, '2027-03-15', 'ACTIVE', 'Satisfactory',
 'Responds quickly. Completed 29372289 (Reading-Wilmington) 5/20.', TRUE),

('538772', '1188521', 'CHAHAL TRUCKING INC', NULL, 'chahaltrucking@gmail.com', '(610) 438-0512', 'Easton, PA 18045',
 '["Box Truck","Sprinter Van"]', '["PA-NJ"]', '18045',
 'Triumph Business Capital', 'factored', 3.8, 1, 0.5, '2026-11-30', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('1592228', NULL, NULL, 'John', 'john.dispatchawl@gmail.com', '423-823-0799', NULL,
 '[]', '[]', NULL,
 'RTS Financial', 'factored', NULL, 0, 0.2, NULL, 'ACTIVE', NULL,
 'New contact. Company name unknown. Communicates via WhatsApp.', FALSE),

('1480355', NULL, 'DEMIX TRANSPORT', 'Lilly Morgan', 'lilly@demixtransport.com', NULL, NULL,
 '["Sprinter Van","Box Truck"]', '["PA-NJ","NJ-NY"]', NULL,
 'RTS Financial', 'factored', 4.5, 2, 0.8, '2027-01-20', 'ACTIVE', 'Satisfactory',
 'Good communicator. CC adam@demixtransport.com on all correspondence.', TRUE),

-- PLACEHOLDER: MC# not yet verified — update mc_number once confirmed
('PENDING_HKR', NULL, 'HKR LOGISTICS LLC', 'Gagandeep Singh', 'hkrlogisticsllc@gmail.com', '484-541-2490', NULL,
 '["Box Truck"]', '["PA-NJ"]', NULL,
 NULL, 'direct', NULL, 0, NULL, NULL, NULL, NULL,
 'MC# not yet verified. Does not factor.', FALSE),

('68333', '3084097', 'G2 LOGISTICS INC', 'Reed Barlus', 'reed.g2transportation@gmail.com', '(630) 415-2622 ext 207', '1615 S [unknown], IL',
 '["Box Truck","Flatbed"]', '["PA-NJ","NJ-NY","PA-PA"]', NULL,
 NULL, 'standard', 4.0, 0, 1.5, '2026-08-10', 'ACTIVE', 'Satisfactory',
 'Illinois-based but active in PA/NJ corridor', FALSE),

('166960', NULL, 'LANDSTAR RANGER INC', 'Marie Vale', 'marie@bbkagent.com', '(929) 279-1065 ext 370', 'Brooklyn, NY',
 '["Box Truck","Sprinter Van","Flatbed"]', '["NJ-NY","PA-NJ","NY-CT"]', '11201',
 NULL, 'standard', 4.7, 0, 2.1, '2027-06-01', 'ACTIVE', 'Satisfactory',
 'Marie is a Landstar agent (BBK Agency), not the carrier directly.', FALSE),

-- NOTE: apostrophe in company name escaped as ''
('1510341', NULL, 'HUSSEIN''S TRUCKING', 'Marcus Duffy', 'marcus.husseinstrucking@gmail.com', NULL, NULL,
 '["Box Truck"]', '["PA-NJ"]', NULL,
 NULL, 'unknown', NULL, 0, 0.3, NULL, 'ACTIVE', NULL,
 'Asked about payment terms without providing factoring info. Follow up needed.', FALSE),

('945231', '3412987', 'Eagle Express LLC', 'Dave Kowalski', 'dispatch@eagleexpressllc.net', '717-555-0142', '440 Commerce Dr, Harrisburg, PA 17101',
 '["Box Truck","Flatbed"]', '["PA-PA","PA-MD","PA-NJ"]', '17101',
 'OTR Solutions', 'factored', 4.8, 7, 0.9, '2027-02-28', 'ACTIVE', 'Satisfactory',
 'Very reliable. Prefers flatbed but runs box truck when empty. Do not offer below $280 on short PA hauls.', TRUE),

('712843', '2987341', 'Blue Ridge Transport LLC', 'Carlos Mendez', 'cmendez@blueridgetransport.com', '610-555-0093', 'Bethlehem, PA 18015',
 '["Sprinter Van","Box Truck"]', '["PA-NJ","NJ-NY","PA-PA"]', '18015',
 'RTS Financial', 'factored', 3.9, 4, 1.1, '2026-05-15', 'ACTIVE', 'Satisfactory',
 'INSURANCE EXPIRED - do not book until updated cert received.', TRUE),

('1023456', '3198432', 'Prime Horizon Logistics', 'Anya Volkov', 'anya@primehorizonlogistics.com', '201-555-0178', 'Newark, NJ 07102',
 '["Box Truck","Refrigerated"]', '["NJ-NY","NJ-CT","NJ-MD"]', '07102',
 NULL, 'direct', 4.6, 5, 1.7, '2027-04-30', 'ACTIVE', 'Satisfactory',
 'One of few local reefer options. Rate floor ~$450 on NJ-NY.', TRUE),

('887642', '3301234', 'Sunrise Carriers Inc', 'Tony Ferrara', 'tony.ferrara@sunrisecarriers.com', '215-555-0261', 'Philadelphia, PA 19146',
 '["Box Truck"]', '["PA-NJ","PA-NY","PA-DE"]', '19146',
 'Triumph Business Capital', 'factored', 4.1, 2, 2.3, '2026-12-01', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('1198743', NULL, 'Mountain State Transport', 'Rob Galloway', 'rob@mountainstatetransport.net', '412-555-0344', 'Pittsburgh, PA 15219',
 '["Flatbed","Box Truck"]', '["PA-PA","PA-OH"]', '15219',
 NULL, 'quick_pay', 3.5, 1, 3.2, '2027-01-15', 'CONDITIONAL', 'Conditional',
 'CONDITIONAL authority - verify before booking any load.', FALSE),

('1345678', '3456789', 'Liberty Freight Solutions LLC', 'Simone Archer', 'simone@libertyfreightsolutions.com', '856-555-0412', 'Camden, NJ 08103',
 '["Box Truck","Sprinter Van"]', '["NJ-PA","NJ-MD","NJ-NY"]', '08103',
 'OTR Solutions', 'factored', 4.9, 9, 0.6, '2027-03-01', 'ACTIVE', 'Satisfactory',
 'Most reliable carrier in NJ corridor. Preferred vendor.', TRUE),

('1123456', '3234567', 'Northeast Cargo LLC', 'Wei Zhang', 'wzhang@northeastcargo.com', '212-555-0589', 'New York, NY 10001',
 '["Box Truck"]', '["NY-CT","NY-NJ","NY-MA"]', '10001',
 NULL, 'direct', 4.3, 3, 1.9, '2026-10-15', 'ACTIVE', 'Satisfactory',
 'Only runs NY metro and New England. Minimum $350 on any load.', TRUE),

('234891', '1987234', 'Keystone Freight LLC', 'Mike Harrington', 'dispatch@keystonefreightllc.com', '215-555-0301', 'Philadelphia, PA 19103',
 '["Box Truck","Flatbed"]', '["PA-NJ","PA-DE","PA-MD"]', '19103',
 NULL, 'standard', 4.4, 6, 1.3, '2027-01-31', 'ACTIVE', 'Satisfactory',
 'Solid PA-area carrier. Prefers morning pickups.', TRUE),

('891234', '2341567', 'TRI-STAR TRANSPORT INC', 'Ivan Sokolowski', 'ivan.tristar@gmail.com', '610-555-0412', 'Bethlehem, PA 18015',
 '["Box Truck"]', '["PA-NJ","PA-NY"]', '18015',
 'RTS Financial', 'factored', 3.7, 2, 2.1, '2027-05-15', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('345678', '2876543', 'Garden State Express LLC', 'Patricia Ramos', 'pramos@gardenstatexpress.com', '856-555-0123', 'Cherry Hill, NJ 08002',
 '["Sprinter Van","Box Truck"]', '["NJ-NY","NJ-PA","NJ-DE"]', '08002',
 NULL, 'direct', 4.6, 8, 0.7, '2027-08-31', 'ACTIVE', 'Satisfactory',
 'Very responsive. Preferred for NJ metro runs.', TRUE),

('567234', NULL, 'ATLANTIC CARRIERS INC', 'Desmond Okafor', 'desmond@atlanticcarriersinc.com', '973-555-0654', 'Newark, NJ 07102',
 '["Box Truck","Refrigerated"]', '["NJ-NY","NJ-CT","NJ-MD"]', '07102',
 'Triumph Business Capital', 'factored', 4.1, 3, 1.4, '2026-09-30', 'ACTIVE', 'Satisfactory',
 'DOT# not yet confirmed.', TRUE),

('723891', '3156789', 'Ridgeline Transport LLC', 'Shaun McIntyre', 'shaun.ridgeline@gmail.com', NULL, 'York, PA 17401',
 '["Flatbed","Box Truck"]', '["PA-MD","PA-PA","PA-DE"]', '17401',
 NULL, 'quick_pay', 3.9, 1, 3.0, '2027-02-28', 'ACTIVE', 'Satisfactory',
 'Slow responder. Good for flatbed when no one else available.', TRUE),

('456789', '2654321', 'VELOCITY FREIGHT INC', 'Jason Tran', 'jtran@velocityfreight.net', '201-555-0789', 'Jersey City, NJ 07302',
 '["Sprinter Van"]', '["NJ-NY","NY-CT"]', '07302',
 'OTR Solutions', 'factored', 4.8, 11, 0.4, '2027-06-30', 'ACTIVE', 'Satisfactory',
 'Best sprinter option in NJ-NY corridor. Rate floor $175.', TRUE),

('678901', '2901234', 'Chesapeake Haulers LLC', 'Robert Nguyen', 'robert@chesapeakehaulers.com', '410-555-0234', 'Baltimore, MD 21201',
 '["Box Truck","Refrigerated"]', '["MD-PA","MD-NJ"]', '21201',
 NULL, 'standard', 4.3, 4, 1.8, '2027-03-31', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('789012', NULL, 'QUICK SHIFT LOGISTICS', 'Amara Diallo', 'amara.quickshift@gmail.com', '718-555-0567', 'Brooklyn, NY 11201',
 '["Sprinter Van","Box Truck"]', '["NY-NJ","NY-CT","NY-PA"]', '11201',
 'TCI Business Capital', 'factored', 3.6, 2, 0.9, '2026-08-15', 'ACTIVE', 'Satisfactory',
 'Insurance expiry coming up - follow up in July.', TRUE),

('901234', '3278901', 'Penn Valley Transport LLC', 'Luis Estrada', 'luis@pennvalleytransport.com', '215-555-0678', 'Philadelphia, PA 19146',
 '["Box Truck"]', '["PA-NJ","PA-DE","PA-MD"]', '19146',
 NULL, 'direct', 4.5, 7, 1.1, '2027-04-15', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('234567', '2543219', 'IRON HORSE FREIGHT LLC', 'Dale Buchanan', 'dale.ironhorse@yahoo.com', '412-555-0345', 'Pittsburgh, PA 15219',
 '["Flatbed","Box Truck"]', '["PA-OH","PA-PA"]', '15219',
 'Porter Capital', 'factored', 4.0, 3, 2.2, '2027-07-31', 'ACTIVE', 'Satisfactory',
 'Western PA specialist. Rate floor $300 on flatbed.', TRUE),

('345891', '3109876', 'Coastal Express Transport LLC', 'Angela Kim', 'akim@coastalexpresstransport.com', NULL, 'Elizabeth, NJ 07201',
 '["Refrigerated"]', '["NJ-NY","NJ-CT","NJ-MD"]', '07201',
 NULL, 'direct', 4.7, 5, 1.6, '2027-01-31', 'ACTIVE', 'Satisfactory',
 'Best reefer option in NJ besides Prime Horizon. Temp logs provided.', TRUE),

('456012', '2789456', 'SUMMIT RIDGE CARRIERS INC', 'Frank Kowalczyk', 'frank.summitridge@gmail.com', '570-555-0456', 'Scranton, PA 18501',
 '["Box Truck","Flatbed"]', '["PA-NJ","PA-NY","PA-PA"]', '18501',
 'RTS Financial', 'factored', 3.8, 2, 2.8, '2026-11-15', 'ACTIVE', 'Satisfactory',
 'NEPA area. Slow responder.', TRUE),

('567123', '2890567', 'Metro Delivery Solutions LLC', 'Vincent Caruso', 'vcaruso@metrodeliverysolutions.com', '212-555-0901', 'New York, NY 10001',
 '["Sprinter Van"]', '["NY-NJ","NY-CT","NY-PA"]', '10001',
 NULL, 'direct', 4.2, 4, 1.0, '2027-05-31', 'ACTIVE', 'Satisfactory',
 'NYC metro only. Minimum $200 on any load.', TRUE),

('678234', NULL, NULL, 'Mohammed Al-Rashid', 'mohammed.dispatch99@gmail.com', '908-555-0654', NULL,
 '["Box Truck"]', '["NJ-PA","NJ-NY"]', NULL,
 'Apex Capital', 'factored', NULL, 0, 0.3, NULL, 'ACTIVE', NULL,
 'Company name not confirmed. Very fast responder. MC# verified, DOT not on file.', FALSE),

-- PLACEHOLDER: MC# not yet provided — update mc_number once confirmed
('PENDING_BLUEEAGLE', NULL, 'BLUE EAGLE LOGISTICS', 'Tariq Hassan', 'tariq.blueeagle@gmail.com', '267-555-0789', 'Philadelphia, PA 19103',
 '["Box Truck","Sprinter Van"]', '["PA-NJ","PA-DE"]', '19103',
 NULL, 'unknown', NULL, 0, NULL, NULL, NULL, NULL,
 'MC# not yet provided. Do not book until verified.', FALSE),

('321654', '2765432', 'Route One Transport Inc', 'Sandra Pellegrino', 'sandra@routeonetransport.com', '856-555-0901', 'Woodbridge, NJ 07095',
 '["Box Truck","Flatbed"]', '["NJ-PA","NJ-NY","NJ-MD"]', '07095',
 'OTR Solutions', 'factored', 4.4, 5, 1.2, '2027-09-30', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('543210', '3012345', 'HORIZON LINE CARRIERS LLC', 'Kevin Doherty', 'kdoherty@horizonlinecarriers.com', '203-555-0123', 'Bridgeport, CT 06601',
 '["Box Truck"]', '["CT-NY","CT-NJ","CT-MA"]', '06601',
 NULL, 'direct', 4.1, 2, 1.9, '2027-02-28', 'ACTIVE', 'Satisfactory',
 'CT/New England specialist.', TRUE),

('765432', '3198765', 'Valley Run Freight LLC', 'Hector Morales', 'hector.valleyrun@gmail.com', '717-555-0234', 'Lancaster, PA 17601',
 '["Box Truck","Sprinter Van"]', '["PA-NJ","PA-DE","PA-MD"]', '17601',
 'RTS Financial', 'factored', 3.5, 1, 2.4, '2027-06-15', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('876543', NULL, 'Capital City Transport', 'Diane Worthington', 'diane@capitalcitytransport.net', '301-555-0345', 'Rockville, MD 20850',
 '["Refrigerated","Box Truck"]', '["MD-PA","MD-NJ","MD-VA"]', '20850',
 NULL, 'standard', 4.6, 6, 1.5, '2027-08-31', 'ACTIVE', 'Satisfactory',
 'Strong reefer option south of PA. CC billing@capitalcitytransport.net on invoices.', TRUE),

('987654', '3276543', 'CLEARVIEW HAULING INC', 'Thomas Pietrzak', 'thomas.clearview@gmail.com', '484-555-0456', 'Allentown, PA 18101',
 '["Box Truck"]', '["PA-NJ","PA-PA","PA-NY"]', '18101',
 'Triumph Business Capital', 'factored', 4.0, 3, 1.7, '2026-12-31', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('109876', '3354321', 'Sharp Arrow Logistics LLC', 'Nkechi Adeyemi', 'nkechi@sharparrowlogistics.com', '201-555-0567', 'Paterson, NJ 07501',
 '["Box Truck","Flatbed"]', '["NJ-NY","NJ-PA","NJ-CT"]', '07501',
 NULL, 'direct', 4.5, 7, 0.8, '2027-07-15', 'ACTIVE', 'Satisfactory',
 'Reliable NJ carrier. Good for flatbed corridor work.', TRUE),

('219876', NULL, 'TRADEWIND TRANSPORT INC', 'Baraka Mwangi', 'baraka.tradewind@gmail.com', NULL, 'Queens, NY 11101',
 '["Sprinter Van","Box Truck"]', '["NY-NJ","NY-CT"]', '11101',
 'TCI Business Capital', 'factored', 3.4, 1, 1.3, '2026-07-31', 'ACTIVE', 'Satisfactory',
 'INSURANCE NEARING EXPIRY. Do not book past July without updated cert.', TRUE),

('330987', '3412098', 'Birch Hill Carriers LLC', 'Colleen Fitzgerald', 'colleen@birchhillcarriers.com', '413-555-0678', 'Springfield, MA 01101',
 '["Box Truck","Refrigerated"]', '["MA-CT","MA-NY","MA-NH"]', '01101',
 NULL, 'standard', 4.2, 2, 2.0, '2027-10-31', 'ACTIVE', 'Satisfactory',
 'New England specialist. Rarely goes below Hartford.', TRUE),

-- NOTE: duplicate "OH-PA" removed from preferred_lanes
('441098', '3523209', 'LAKESIDE FREIGHT LLC', 'Omar Washington', 'omar@lakesidefreight.net', '216-555-0789', 'Cleveland, OH 44101',
 '["Flatbed","Box Truck"]', '["OH-PA","PA-OH"]', '44101',
 'Porter Capital', 'factored', 4.1, 2, 2.6, '2027-04-30', 'ACTIVE', 'Satisfactory',
 'Ohio-based. Good for PA-OH corridor flatbed work.', TRUE),

('552109', NULL, 'Premier Road Transport', 'Adriana Castillo', 'adriana.premier@gmail.com', '973-555-0890', 'Elizabeth, NJ 07201',
 '["Box Truck"]', '["NJ-NY","NJ-PA"]', '07201',
 NULL, 'direct', NULL, 0, 0.6, '2027-03-31', 'ACTIVE', NULL,
 'New contact. Fast responder. Safety rating not yet on file.', FALSE),

('663210', '3634320', 'CROSSROADS TRANSPORT INC', 'Gene Palumbo', 'gene@crossroadstransport.net', '215-555-0012', 'Philadelphia, PA 19103',
 '["Box Truck","Flatbed"]', '["PA-NJ","PA-MD","PA-DE"]', '19103',
 'RTS Financial', 'factored', 4.3, 5, 1.4, '2027-11-30', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('774321', '3745431', 'Northbound Express LLC', 'Priyanka Mehta', 'pmehta@northboundexpress.com', '201-555-0234', 'Jersey City, NJ 07302',
 '["Sprinter Van","Box Truck"]', '["NJ-NY","NY-CT","NJ-CT"]', '07302',
 'OTR Solutions', 'factored', 4.6, 9, 0.5, '2027-12-31', 'ACTIVE', 'Satisfactory',
 'Top sprinter van option in NJ-NY. High volume, good communication.', TRUE),

('885432', NULL, 'FRONTIER HAULING LLC', 'Clint Beauregard', 'clint.frontier@gmail.com', '724-555-0345', 'Pittsburgh, PA 15219',
 '["Flatbed"]', '["PA-OH","PA-WV","PA-PA"]', '15219',
 NULL, 'quick_pay', 3.8, 1, 3.5, '2027-01-31', 'CONDITIONAL', 'Conditional',
 'CONDITIONAL authority. Verify with FMCSA before every booking.', FALSE),

('996543', '3856542', 'Red Oak Freight Solutions', 'Fatima Diarra', 'fatima@redoakfreight.com', '302-555-0456', 'Wilmington, DE 19801',
 '["Box Truck","Sprinter Van"]', '["DE-PA","DE-NJ","DE-MD"]', '19801',
 NULL, 'standard', 4.4, 4, 1.1, '2027-06-30', 'ACTIVE', 'Satisfactory',
 'Good DE-area carrier. Good for return runs from Wilmington.', TRUE),

('107654', NULL, 'PINNACLE FREIGHT INC', 'Raj Patel', 'raj.pinnaclefreight@gmail.com', '908-555-0567', 'Woodbridge, NJ 07095',
 '["Box Truck"]', '["NJ-PA","NJ-NY","NJ-DE"]', '07095',
 'Apex Capital', 'factored', 3.9, 2, 1.6, '2027-09-15', 'ACTIVE', 'Satisfactory',
 NULL, TRUE),

('218765', '3967653', 'Tidewater Carriers Inc', 'William Osei', 'wosei@tidewatercarriers.com', '410-555-0678', 'Annapolis, MD 21401',
 '["Refrigerated","Box Truck"]', '["MD-PA","MD-NJ","MD-VA"]', '21401',
 NULL, 'standard', 4.5, 3, 1.9, '2027-05-31', 'ACTIVE', 'Satisfactory',
 'Good reefer option for MD/VA runs.', TRUE),

('329876', NULL, NULL, 'Benny', 'bennytrucks88@hotmail.com', '610-555-0789', NULL,
 '["Box Truck"]', '[]', NULL,
 NULL, 'unknown', NULL, 0, 0.2, NULL, NULL, NULL,
 'Unknown carrier. Reached out cold. No company name, no MC#, no insurance on file. Do not book.', FALSE),

('440987', '4078764', 'SWIFT LANE TRANSPORT LLC', 'Denise Johansson', 'denise@swiftlanetransport.com', '215-555-0890', 'Philadelphia, PA 19146',
 '["Box Truck","Sprinter Van"]', '["PA-NJ","PA-DE","PA-NY"]', '19146',
 'Triumph Business Capital', 'factored', 4.1, 3, 1.3, '2027-03-15', 'ACTIVE', 'Satisfactory',
 NULL, TRUE)

ON CONFLICT (mc_number) DO NOTHING;
