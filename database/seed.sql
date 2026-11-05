-- =====================================================================
-- ClubHub seed data. User_Account rows are created by init_db.py so that
-- passwords are hashed with werkzeug rather than stored in plain text.
-- =====================================================================

-- ---------- PERSON (1–14 students, 15–19 faculty) ---------------------
INSERT INTO Person (person_id, name, email, phone) VALUES
 (1,  'Aarav Mehta',      'aarav.mehta@nsut.ac.in',     '9810000001'),
 (2,  'Diya Sharma',      'diya.sharma@nsut.ac.in',     '9810000002'),
 (3,  'Kabir Anand',      'kabir.anand@nsut.ac.in',     '9810000003'),
 (4,  'Ishita Verma',     'ishita.verma@nsut.ac.in',    '9810000004'),
 (5,  'Rohan Gupta',      'rohan.gupta@nsut.ac.in',     '9810000005'),
 (6,  'Sneha Iyer',       'sneha.iyer@nsut.ac.in',      '9810000006'),
 (7,  'Arjun Malhotra',   'arjun.malhotra@nsut.ac.in',  '9810000007'),
 (8,  'Priya Nair',       'priya.nair@nsut.ac.in',      '9810000008'),
 (9,  'Vikram Singh',     'vikram.singh@nsut.ac.in',    '9810000009'),
 (10, 'Ananya Bose',      'ananya.bose@nsut.ac.in',     '9810000010'),
 (11, 'Dev Kapoor',       'dev.kapoor@nsut.ac.in',      '9810000011'),
 (12, 'Meera Reddy',      'meera.reddy@nsut.ac.in',     '9810000012'),
 (13, 'Yash Chawla',      'yash.chawla@nsut.ac.in',     '9810000013'),
 (14, 'Tanvi Joshi',      'tanvi.joshi@nsut.ac.in',     '9810000014'),
 (15, 'Dr. Neelam Sinha', 'neelam.sinha@nsut.ac.in',    '9870000001'),
 (16, 'Dr. Rajesh Kumar', 'rajesh.kumar@nsut.ac.in',    '9870000002'),
 (17, 'Dr. Pooja Bhatt',  'pooja.bhatt@nsut.ac.in',     '9870000003'),
 (18, 'Dr. Amit Saxena',  'amit.saxena@nsut.ac.in',     '9870000004'),
 (19, 'Dr. Farah Khan',   'farah.khan@nsut.ac.in',      '9870000005');

-- ---------- STUDENT ----------------------------------------------------
INSERT INTO Student (student_id, roll_no, branch, year) VALUES
 (1,  '2023UCS1001', 'CSE',  3),
 (2,  '2023UIT1042', 'IT',   3),
 (3,  '2022UEC1107', 'ECE',  4),
 (4,  '2024UCS1210', 'CSE',  2),
 (5,  '2024UME1033', 'ME',   2),
 (6,  '2023UCD1018', 'CSDS', 3),
 (7,  '2022UEE1051', 'EE',   4),
 (8,  '2025UCS1302', 'CSE',  1),
 (9,  '2023UCE1077', 'CE',   3),
 (10, '2024UBT1009', 'BT',   2),
 (11, '2025UIT1120', 'IT',   1),
 (12, '2023UCA1064', 'CSAI', 3),
 (13, '2024UEC1145', 'ECE',  2),
 (14, '2025UMA1011', 'MAC',  1);

-- ---------- FACULTY ----------------------------------------------------
INSERT INTO Faculty (faculty_id, department, designation) VALUES
 (15, 'Computer Science & Engineering', 'Associate Professor'),
 (16, 'Electronics & Communication',    'Professor'),
 (17, 'Humanities & Social Sciences',   'Assistant Professor'),
 (18, 'Mechanical Engineering',         'Professor'),
 (19, 'Management Studies',             'Assistant Professor');

-- ---------- CLUB (supertype) --------------------------------------------
INSERT INTO Club (club_id, name, category, tagline, description, room_no, founded_year, contact_email, status) VALUES
 (1, 'ByteForge',          'Technical', 'Build. Break. Ship.',
     'The campus developer community. Weekly build nights, open-source sprints, and the annual 36-hour hackathon HackForge.',
     'Lab 204, Block 5', 2016, 'byteforge@nsut.ac.in', 'Active'),
 (2, 'Mudra Dance Society','Cultural',  'Every beat has a story.',
     'Classical, contemporary and street dance crews that represent the college at inter-university fests across Delhi.',
     'Auditorium Annex',  2011, 'mudra@nsut.ac.in', 'Active'),
 (3, 'Ashwa Athletics',    'Sports',    'Faster. Higher. Together.',
     'Track and field squad. Trains five mornings a week and hosts the annual Ashwa Open on the main ground.',
     'Sports Complex',    2008, 'ashwa@nsut.ac.in', 'Active'),
 (4, 'Inklings',           'Literary',  'Words that stay.',
     'Poetry slams, debate league, and the quarterly campus zine "Marginalia".',
     'Room 112, Block 2', 2014, 'inklings@nsut.ac.in', 'Active'),
 (5, 'Udaan',              'Social',    'Small acts, wide wings.',
     'Community outreach: weekend teaching at nearby government schools, blood-donation camps and the winter clothing drive.',
     'Room 018, Block 1', 2012, 'udaan@nsut.ac.in', 'Active'),
 (6, 'Quant Cell',         'Academic',  'Numbers, markets, models.',
     'Finance and analytics society. Runs the mock-trading league and speaker sessions with alumni in quant and consulting.',
     'Seminar Hall B',    2019, 'quantcell@nsut.ac.in', 'Active');

-- ---------- CLUB subtypes -----------------------------------------------
INSERT INTO Technical_Club (club_id, github_url, tech_stack) VALUES
 (1, 'https://github.com/byteforge-nsut', 'Python, Rust, React, PostgreSQL');
INSERT INTO Cultural_Club (club_id, art_form) VALUES
 (2, 'Dance');
INSERT INTO Sports_Club (club_id, sport, coach_name) VALUES
 (3, 'Athletics', 'Coach Harbhajan Lal');

-- ---------- CLUB_ADVISOR ------------------------------------------------
INSERT INTO Club_Advisor (club_id, faculty_id, assigned_on) VALUES
 (1, 15, '2023-08-01'),
 (1, 16, '2024-08-01'),
 (2, 17, '2022-08-01'),
 (3, 18, '2021-08-01'),
 (4, 17, '2023-08-01'),
 (5, 19, '2024-08-01'),
 (6, 19, '2023-08-01');

-- ---------- MEMBERSHIP --------------------------------------------------
INSERT INTO Membership (student_id, club_id, role, joined_at) VALUES
 (1, 1, 'President',      '2023-09-05'),
 (6, 1, 'Vice President', '2023-09-05'),
 (4, 1, 'Core Member',    '2024-09-10'),
 (8, 1, 'Member',         '2025-09-12'),
 (12,1, 'Secretary',      '2023-09-20'),
 (11,1, 'Member',         '2025-09-15'),
 (2, 2, 'President',      '2023-09-01'),
 (10,2, 'Treasurer',      '2024-09-08'),
 (14,2, 'Member',         '2025-09-10'),
 (4, 2, 'Member',         '2024-10-01'),
 (3, 3, 'President',      '2022-09-02'),
 (5, 3, 'Vice President', '2024-09-02'),
 (9, 3, 'Core Member',    '2023-09-15'),
 (13,3, 'Member',         '2024-09-20'),
 (7, 4, 'President',      '2022-09-10'),
 (12,4, 'Core Member',    '2023-10-01'),
 (14,4, 'Member',         '2025-09-18'),
 (9, 5, 'President',      '2023-09-12'),
 (10,5, 'Secretary',      '2024-09-14'),
 (8, 5, 'Member',         '2025-09-20'),
 (6, 6, 'President',      '2023-09-07'),
 (1, 6, 'Core Member',    '2023-09-30'),
 (13,6, 'Member',         '2024-10-05'),
 (11,6, 'Member',         '2025-09-22');

-- ---------- EVENT -------------------------------------------------------
INSERT INTO Event (event_id, club_id, title, event_type, description, event_date, registration_deadline, venue, capacity, status) VALUES
 (1, 1, 'HackForge 2026',                 'Hackathon',   '36-hour build sprint. Teams of up to four. Tracks: fintech, health, campus tools.',   '2026-11-21 09:00', '2026-11-18', 'Lab 204 & 205, Block 5',  120, 'Upcoming'),
 (2, 1, 'Intro to Rust — Build a CLI',     'Workshop',    'Hands-on: cargo, ownership, and a working CLI tool by the end of the session.',       '2026-11-12 17:00', '2026-11-11', 'Lab 204, Block 5',         40, 'Upcoming'),
 (3, 1, 'Open Source Office Hours',        'Meetup',      'Bring your first PR. Mentors from senior years help you land it.',                    '2026-10-15 17:30', NULL,         'Lab 204, Block 5',         30, 'Upcoming'),
 (4, 2, 'Nritya Utsav Auditions',          'Cultural',    'Open auditions for the inter-college contemporary crew.',                             '2026-11-14 15:00', '2026-11-13', 'Auditorium Annex',         60, 'Upcoming'),
 (5, 2, 'Choreography Lab: Hip-hop basics','Workshop',    'Beginner-friendly session with the street crew leads.',                               '2026-11-28 16:00', '2026-11-27', 'Auditorium Annex',         35, 'Upcoming'),
 (6, 3, 'Ashwa Open 2026',                 'Sports',      '100m, 400m, 1500m, long jump and relay. Open to all years.',                          '2026-12-05 07:00', '2026-12-01', 'Main Ground',             150, 'Upcoming'),
 (7, 4, 'Slam Night: Winter Edition',      'Competition', 'Three-minute spoken-word rounds. Audience votes the final.',                          '2026-11-19 18:30', '2026-11-18', 'Room 112, Block 2',        80, 'Upcoming'),
 (8, 5, 'Blood Donation Camp',             'Session',     'In partnership with the district blood bank. Bring your ID.',                         '2026-11-10 10:00', '2026-11-09', 'Block 1 Foyer',           200, 'Upcoming'),
 (9, 6, 'Quant Careers: Alumni Panel',     'Webinar',     'Alumni at trading firms and consultancies on how they got there. Online, link on registration.', '2026-11-16 19:00', '2026-11-16', 'Online (Google Meet)', 300, 'Upcoming'),
 (10,6, 'Mock Trading League — Round 1',   'Competition', 'Paper-trade a fixed portfolio over one week. Leaderboard updates daily.',             '2026-10-20 18:00', NULL,         'Seminar Hall B',           50, 'Upcoming'),
 (11,1, 'Git Workshop (cancelled)',        'Workshop',    'Rescheduled into Open Source Office Hours.',                                          '2026-10-01 17:00', NULL,         'Lab 204, Block 5',         40, 'Upcoming');

-- ---------- EVENT_REGISTRATION --------------------------------------------
INSERT INTO Event_Registration (student_id, event_id, registered_at) VALUES
 (4, 1, '2026-11-01 10:12:00'), (8, 1, '2026-11-01 11:40:00'), (11,1, '2026-11-02 09:05:00'),
 (12,1, '2026-11-02 14:22:00'), (6, 1, '2026-11-03 08:30:00'), (13,1, '2026-11-03 19:45:00'),
 (2, 1, '2026-11-04 12:00:00'),
 (8, 2, '2026-11-02 10:00:00'), (11,2, '2026-11-02 10:05:00'), (4, 2, '2026-11-03 16:40:00'),
 (14,4, '2026-11-01 09:00:00'), (4, 4, '2026-11-02 09:30:00'), (10,4, '2026-11-02 09:45:00'),
 (5, 6, '2026-11-03 07:00:00'), (9, 6, '2026-11-03 07:10:00'), (13,6, '2026-11-03 07:30:00'), (3, 6, '2026-11-03 08:00:00'),
 (12,7, '2026-11-02 20:00:00'), (14,7, '2026-11-02 20:15:00'), (7, 7, '2026-11-02 21:00:00'),
 (8, 8, '2026-11-01 08:00:00'), (10,8, '2026-11-01 08:10:00'), (9, 8, '2026-11-01 08:20:00'), (1, 8, '2026-11-01 09:00:00'),
 (1, 9, '2026-11-04 10:00:00'), (6, 9, '2026-11-04 10:05:00'), (13,9, '2026-11-04 10:30:00'), (11,9, '2026-11-04 11:00:00'),
 (1, 3, '2026-10-10 10:00:00'), (4, 3, '2026-10-10 10:30:00'),
 (6, 10,'2026-10-15 10:00:00'), (1, 10,'2026-10-15 10:30:00'), (13,10,'2026-10-16 09:00:00');

-- Past events: registrations happened while they were Upcoming; now close them.
UPDATE Event SET status = 'Completed' WHERE event_id IN (3, 10);
UPDATE Event SET status = 'Cancelled' WHERE event_id = 11;

-- ---------- CLUB_FUNDING ------------------------------------------------
INSERT INTO Club_Funding (club_id, source_type, sponsor_name, amount, received_on, academic_year, remarks) VALUES
 (1, 'College Grant',   'Dean of Student Welfare',   60000, '2026-08-05', '2026-27', 'Annual technical society grant'),
 (1, 'Sponsorship',     'DevTools Inc.',             45000, '2026-10-20', '2026-27', 'HackForge title sponsor'),
 (1, 'Sponsorship',     'CloudNine Hosting',         15000, '2026-10-28', '2026-27', 'Credits + cash for HackForge'),
 (2, 'College Grant',   'Dean of Student Welfare',   40000, '2026-08-05', '2026-27', 'Annual cultural grant'),
 (2, 'Event Revenue',   NULL,                        12500, '2026-03-18', '2025-26', 'Nritya Utsav ticket sales'),
 (3, 'College Grant',   'Sports Council',            75000, '2026-08-05', '2026-27', 'Equipment and travel'),
 (3, 'Sponsorship',     'StrideWear',                20000, '2026-11-01', '2026-27', 'Ashwa Open kit sponsor'),
 (4, 'College Grant',   'Dean of Student Welfare',   15000, '2026-08-05', '2026-27', 'Zine printing'),
 (5, 'Alumni Donation', 'Class of 2015',             30000, '2026-09-12', '2026-27', 'Winter clothing drive'),
 (5, 'College Grant',   'Dean of Student Welfare',   20000, '2026-08-05', '2026-27', NULL),
 (6, 'Sponsorship',     'Axis Quant Partners',       25000, '2026-09-30', '2026-27', 'Mock trading league prizes'),
 (6, 'Membership Fees', NULL,                         8000, '2026-09-01', '2026-27', '40 members x Rs 200');

-- ---------- CLUB_ASSET --------------------------------------------------
INSERT INTO Club_Asset (club_id, name, asset_type, quantity, condition, acquired_on, cost) VALUES
 (1, 'Raspberry Pi 5 kits',       'Electronics', 10, 'Good',         '2025-02-10', 65000),
 (1, 'Epson projector',           'Electronics',  1, 'Fair',         '2021-08-15', 42000),
 (1, 'Whiteboard (mobile)',       'Furniture',    2, 'Good',         '2023-01-20',  9000),
 (2, 'JBL PartyBox speaker',      'Electronics',  2, 'Good',         '2024-09-01', 56000),
 (2, 'Mirror panels (6 ft)',      'Furniture',    8, 'Good',         '2022-07-12', 32000),
 (2, 'Contemporary costume set',  'Costume',     20, 'Fair',         '2023-11-05', 40000),
 (3, 'Starting blocks',           'Sports Gear',  8, 'Good',         '2023-06-01', 24000),
 (3, 'Hurdles (adjustable)',      'Sports Gear', 12, 'Needs Repair', '2019-03-14', 18000),
 (3, 'Stopwatches',               'Electronics',  6, 'Good',         '2024-01-09',  7200),
 (4, 'Portable PA system',        'Electronics',  1, 'Good',         '2024-02-22', 15000),
 (5, 'Folding tables',            'Furniture',    6, 'Good',         '2022-10-30', 12000),
 (6, 'Bloomberg-style ticker display','Electronics',1,'New',         '2026-09-15', 28000);

-- ---------- CLUB_DOCUMENT -----------------------------------------------
INSERT INTO Club_Document (club_id, title, doc_type, url, visibility, uploaded_on) VALUES
 (1, 'ByteForge Constitution (2024 rev.)', 'Constitution', 'https://drive.google.com/byteforge/constitution', 'Public',  '2024-08-20'),
 (1, 'HackForge 2026 Budget',              'Budget',       'https://drive.google.com/byteforge/hackforge-budget', 'Private', '2026-10-05'),
 (1, 'Core meeting minutes — Oct 2026',    'Minutes',      'https://drive.google.com/byteforge/minutes-oct26', 'Members', '2026-10-29'),
 (2, 'Mudra Constitution',                 'Constitution', 'https://drive.google.com/mudra/constitution', 'Public',  '2022-09-01'),
 (2, 'Nritya Utsav 2026 highlights',       'Media',        'https://drive.google.com/mudra/nritya-2026', 'Public',  '2026-03-25'),
 (3, 'Ashwa Open entry form',              'Form',         'https://forms.gle/ashwa-open-2026', 'Public',  '2026-11-01'),
 (3, 'Annual report 2025-26',              'Report',       'https://drive.google.com/ashwa/report-2526', 'Members', '2026-07-30'),
 (5, 'School outreach schedule',           'Other',        'https://drive.google.com/udaan/schedule', 'Members', '2026-09-20'),
 (6, 'Mock trading league rulebook',       'Other',        'https://drive.google.com/quant/rulebook', 'Public',  '2026-10-10');

-- Announcements are inserted by init_db.py (they need posted_by user ids).
