-- =====================================================================
-- ClubHub — Student Club & Organisation Management System
-- Database Schema (SQLite 3) — normalised to BCNF
--
-- Design notes
--   * Generalisation / specialisation #1: PERSON ⇒ STUDENT | FACULTY
--       (disjoint, total — every Person is exactly one of the two)
--   * Generalisation / specialisation #2: CLUB ⇒ TECHNICAL_CLUB |
--       CULTURAL_CLUB | SPORTS_CLUB  (disjoint, partial — Literary,
--       Social and Academic clubs have no extra attributes)
--   * Subtype rows share the supertype's primary key (PK = FK).
--   * Role-based access control lives in USER_ACCOUNT. "Club Head"
--       is NOT a stored role: it is derived from MEMBERSHIP.role so the
--       fact is recorded exactly once (no update anomaly).
--   * Every table's non-key attributes depend only on the whole key
--       and nothing but the key ⇒ BCNF. Derived values (member counts,
--       seats left, funding totals) are computed in views, never stored.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. PERSON  (supertype of Student and Faculty)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Person (
    person_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    email       TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%._%'),
    phone       TEXT CHECK (phone IS NULL OR length(phone) BETWEEN 10 AND 15)
);

-- ---------------------------------------------------------------------
-- 2. STUDENT  (subtype of Person)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Student (
    student_id  INTEGER PRIMARY KEY REFERENCES Person(person_id) ON DELETE CASCADE,
    roll_no     TEXT NOT NULL UNIQUE,
    branch      TEXT NOT NULL CHECK (branch IN ('CSE','IT','ECE','EE','ME','CE','BT','MAC','CSAI','CSDS')),
    year        INTEGER NOT NULL CHECK (year BETWEEN 1 AND 4)
);

-- ---------------------------------------------------------------------
-- 3. FACULTY  (subtype of Person)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Faculty (
    faculty_id  INTEGER PRIMARY KEY REFERENCES Person(person_id) ON DELETE CASCADE,
    department  TEXT NOT NULL,
    designation TEXT NOT NULL CHECK (designation IN ('Professor','Associate Professor','Assistant Professor','Lecturer'))
);

-- ---------------------------------------------------------------------
-- 4. USER_ACCOUNT  (login + role; Admin accounts have no Person)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS User_Account (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE CHECK (length(username) >= 3),
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('Admin','Student','Faculty')),
    person_id     INTEGER UNIQUE REFERENCES Person(person_id) ON DELETE CASCADE,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    -- Admins are not people in the directory; everyone else must be.
    CHECK ((role = 'Admin' AND person_id IS NULL) OR (role <> 'Admin' AND person_id IS NOT NULL))
);

-- ---------------------------------------------------------------------
-- 5. CLUB  (supertype)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Club (
    club_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    category      TEXT NOT NULL CHECK (category IN ('Technical','Cultural','Sports','Literary','Social','Academic')),
    tagline       TEXT,
    description   TEXT,
    room_no       TEXT,
    founded_year  INTEGER CHECK (founded_year IS NULL OR founded_year BETWEEN 1950 AND 2100),
    contact_email TEXT CHECK (contact_email IS NULL OR contact_email LIKE '%_@_%._%'),
    status        TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Inactive'))
);

-- ---------------------------------------------------------------------
-- 6–8. CLUB subtypes (partial, disjoint — discriminator = Club.category)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Technical_Club (
    club_id     INTEGER PRIMARY KEY REFERENCES Club(club_id) ON DELETE CASCADE,
    github_url  TEXT,
    tech_stack  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Cultural_Club (
    club_id     INTEGER PRIMARY KEY REFERENCES Club(club_id) ON DELETE CASCADE,
    art_form    TEXT NOT NULL CHECK (art_form IN ('Dance','Music','Drama','Fine Arts','Fashion','Photography','Film'))
);

CREATE TABLE IF NOT EXISTS Sports_Club (
    club_id     INTEGER PRIMARY KEY REFERENCES Club(club_id) ON DELETE CASCADE,
    sport       TEXT NOT NULL,
    coach_name  TEXT
);

-- ---------------------------------------------------------------------
-- 9. CLUB_ADVISOR  (M:N  Club ↔ Faculty)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Club_Advisor (
    club_id     INTEGER NOT NULL REFERENCES Club(club_id)       ON DELETE CASCADE,
    faculty_id  INTEGER NOT NULL REFERENCES Faculty(faculty_id) ON DELETE CASCADE,
    assigned_on TEXT NOT NULL DEFAULT (date('now')),
    PRIMARY KEY (club_id, faculty_id)
);

-- ---------------------------------------------------------------------
-- 10. MEMBERSHIP  (M:N  Student ↔ Club, with role)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Membership (
    student_id  INTEGER NOT NULL REFERENCES Student(student_id) ON DELETE CASCADE,
    club_id     INTEGER NOT NULL REFERENCES Club(club_id)       ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'Member'
                CHECK (role IN ('President','Vice President','Secretary','Treasurer','Core Member','Member')),
    joined_at   TEXT NOT NULL DEFAULT (date('now')),
    PRIMARY KEY (student_id, club_id)
);

-- ---------------------------------------------------------------------
-- 11. EVENT  (1:N  Club → Event)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Event (
    event_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id               INTEGER NOT NULL REFERENCES Club(club_id) ON DELETE CASCADE,
    title                 TEXT NOT NULL,
    event_type            TEXT NOT NULL CHECK (event_type IN ('Workshop','Webinar','Hackathon','Competition','Session','Cultural','Sports','Meetup')),
    description           TEXT,
    event_date            TEXT NOT NULL,               -- ISO 'YYYY-MM-DD HH:MM'
    registration_deadline TEXT,                        -- ISO date; NULL = until event starts
    venue                 TEXT NOT NULL,
    capacity              INTEGER NOT NULL CHECK (capacity > 0),
    status                TEXT NOT NULL DEFAULT 'Upcoming' CHECK (status IN ('Upcoming','Ongoing','Completed','Cancelled')),
    CHECK (registration_deadline IS NULL OR registration_deadline <= event_date)
);

-- ---------------------------------------------------------------------
-- 12. EVENT_REGISTRATION  (M:N  Student ↔ Event). Cancel = delete row.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Event_Registration (
    student_id    INTEGER NOT NULL REFERENCES Student(student_id) ON DELETE CASCADE,
    event_id      INTEGER NOT NULL REFERENCES Event(event_id)     ON DELETE CASCADE,
    registered_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (student_id, event_id)
);

-- ---------------------------------------------------------------------
-- 13. CLUB_FUNDING  (1:N  Club → Funding entries)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Club_Funding (
    funding_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id       INTEGER NOT NULL REFERENCES Club(club_id) ON DELETE CASCADE,
    source_type   TEXT NOT NULL CHECK (source_type IN ('College Grant','Sponsorship','Membership Fees','Event Revenue','Alumni Donation','Other')),
    sponsor_name  TEXT,
    amount        REAL NOT NULL CHECK (amount > 0),
    received_on   TEXT NOT NULL,
    academic_year TEXT NOT NULL CHECK (academic_year GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    remarks       TEXT
);

-- ---------------------------------------------------------------------
-- 14. CLUB_ASSET  (1:N  Club → physical inventory)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Club_Asset (
    asset_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id      INTEGER NOT NULL REFERENCES Club(club_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    asset_type   TEXT NOT NULL CHECK (asset_type IN ('Electronics','Instrument','Furniture','Sports Gear','Costume','Stationery','Other')),
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    condition    TEXT NOT NULL DEFAULT 'Good' CHECK (condition IN ('New','Good','Fair','Needs Repair','Retired')),
    acquired_on  TEXT,
    cost         REAL CHECK (cost IS NULL OR cost >= 0)
);

-- ---------------------------------------------------------------------
-- 15. CLUB_DOCUMENT  (1:N  Club → documents / links)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Club_Document (
    doc_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id      INTEGER NOT NULL REFERENCES Club(club_id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    doc_type     TEXT NOT NULL CHECK (doc_type IN ('Constitution','Minutes','Budget','Report','Media','Form','Other')),
    url          TEXT NOT NULL,
    visibility   TEXT NOT NULL DEFAULT 'Members' CHECK (visibility IN ('Public','Members','Private')),
    uploaded_on  TEXT NOT NULL DEFAULT (date('now'))
);

-- ---------------------------------------------------------------------
-- 16. ANNOUNCEMENT  (club notice or college-wide alert)
--     club_id NULL  ⇒ college-wide (Admin only)
--     priority 'Alert' ⇒ shown as a banner
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Announcement (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id         INTEGER REFERENCES Club(club_id) ON DELETE CASCADE,
    posted_by       INTEGER NOT NULL REFERENCES User_Account(user_id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'Normal' CHECK (priority IN ('Normal','Alert')),
    is_pinned       INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0,1)),
    posted_at       TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    expires_at      TEXT
);

-- =====================================================================
-- INDEXES  (foreign keys and the columns the UI filters on)
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_membership_club      ON Membership(club_id);
CREATE INDEX IF NOT EXISTS idx_event_club_date      ON Event(club_id, event_date);
CREATE INDEX IF NOT EXISTS idx_event_status_date    ON Event(status, event_date);
CREATE INDEX IF NOT EXISTS idx_registration_event   ON Event_Registration(event_id);
CREATE INDEX IF NOT EXISTS idx_funding_club_year    ON Club_Funding(club_id, academic_year);
CREATE INDEX IF NOT EXISTS idx_asset_club           ON Club_Asset(club_id);
CREATE INDEX IF NOT EXISTS idx_document_club        ON Club_Document(club_id);
CREATE INDEX IF NOT EXISTS idx_announcement_club    ON Announcement(club_id, posted_at);
CREATE INDEX IF NOT EXISTS idx_advisor_faculty      ON Club_Advisor(faculty_id);

-- =====================================================================
-- TRIGGERS  (rules a CHECK constraint cannot express)
-- =====================================================================

-- --- Disjointness of PERSON subtypes -----------------------------------
CREATE TRIGGER IF NOT EXISTS trg_student_disjoint
BEFORE INSERT ON Student
WHEN EXISTS (SELECT 1 FROM Faculty WHERE faculty_id = NEW.student_id)
BEGIN SELECT RAISE(ABORT, 'Person is already a Faculty member; cannot also be a Student'); END;

CREATE TRIGGER IF NOT EXISTS trg_faculty_disjoint
BEFORE INSERT ON Faculty
WHEN EXISTS (SELECT 1 FROM Student WHERE student_id = NEW.faculty_id)
BEGIN SELECT RAISE(ABORT, 'Person is already a Student; cannot also be Faculty'); END;

-- --- CLUB subtype must match the discriminator (Club.category) ---------
CREATE TRIGGER IF NOT EXISTS trg_technical_club_category
BEFORE INSERT ON Technical_Club
WHEN (SELECT category FROM Club WHERE club_id = NEW.club_id) <> 'Technical'
BEGIN SELECT RAISE(ABORT, 'Technical_Club row requires Club.category = Technical'); END;

CREATE TRIGGER IF NOT EXISTS trg_cultural_club_category
BEFORE INSERT ON Cultural_Club
WHEN (SELECT category FROM Club WHERE club_id = NEW.club_id) <> 'Cultural'
BEGIN SELECT RAISE(ABORT, 'Cultural_Club row requires Club.category = Cultural'); END;

CREATE TRIGGER IF NOT EXISTS trg_sports_club_category
BEFORE INSERT ON Sports_Club
WHEN (SELECT category FROM Club WHERE club_id = NEW.club_id) <> 'Sports'
BEGIN SELECT RAISE(ABORT, 'Sports_Club row requires Club.category = Sports'); END;

-- If a club changes category, its old subtype row is no longer valid.
CREATE TRIGGER IF NOT EXISTS trg_club_category_change
AFTER UPDATE OF category ON Club
WHEN OLD.category <> NEW.category
BEGIN
    DELETE FROM Technical_Club WHERE club_id = NEW.club_id AND NEW.category <> 'Technical';
    DELETE FROM Cultural_Club  WHERE club_id = NEW.club_id AND NEW.category <> 'Cultural';
    DELETE FROM Sports_Club    WHERE club_id = NEW.club_id AND NEW.category <> 'Sports';
END;

-- --- Account role must agree with the Person subtype -------------------
CREATE TRIGGER IF NOT EXISTS trg_account_role_matches_person
BEFORE INSERT ON User_Account
WHEN NEW.role = 'Student' AND NOT EXISTS (SELECT 1 FROM Student WHERE student_id = NEW.person_id)
  OR NEW.role = 'Faculty' AND NOT EXISTS (SELECT 1 FROM Faculty WHERE faculty_id = NEW.person_id)
BEGIN SELECT RAISE(ABORT, 'User_Account.role does not match the Person subtype'); END;

-- --- Event capacity ----------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_registration_capacity
BEFORE INSERT ON Event_Registration
WHEN (SELECT COUNT(*) FROM Event_Registration WHERE event_id = NEW.event_id)
     >= (SELECT capacity FROM Event WHERE event_id = NEW.event_id)
BEGIN SELECT RAISE(ABORT, 'Event is at full capacity'); END;

CREATE TRIGGER IF NOT EXISTS trg_registration_event_open
BEFORE INSERT ON Event_Registration
WHEN (SELECT status FROM Event WHERE event_id = NEW.event_id) <> 'Upcoming'
BEGIN SELECT RAISE(ABORT, 'Registrations are only accepted for Upcoming events'); END;

CREATE TRIGGER IF NOT EXISTS trg_event_capacity_floor
BEFORE UPDATE OF capacity ON Event
WHEN NEW.capacity < (SELECT COUNT(*) FROM Event_Registration WHERE event_id = NEW.event_id)
BEGIN SELECT RAISE(ABORT, 'Capacity cannot be lower than current registrations'); END;

-- --- Exactly one President per club ------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_one_president_insert
BEFORE INSERT ON Membership
WHEN NEW.role = 'President'
 AND EXISTS (SELECT 1 FROM Membership WHERE club_id = NEW.club_id AND role = 'President')
BEGIN SELECT RAISE(ABORT, 'This club already has a President'); END;

CREATE TRIGGER IF NOT EXISTS trg_one_president_update
BEFORE UPDATE OF role ON Membership
WHEN NEW.role = 'President'
 AND EXISTS (SELECT 1 FROM Membership
             WHERE club_id = NEW.club_id AND role = 'President' AND student_id <> NEW.student_id)
BEGIN SELECT RAISE(ABORT, 'This club already has a President'); END;

-- --- College-wide announcements can only be posted by Admins -----------
CREATE TRIGGER IF NOT EXISTS trg_collegewide_announcement_admin_only
BEFORE INSERT ON Announcement
WHEN NEW.club_id IS NULL
 AND (SELECT role FROM User_Account WHERE user_id = NEW.posted_by) <> 'Admin'
BEGIN SELECT RAISE(ABORT, 'Only Admins can post college-wide announcements'); END;

-- =====================================================================
-- VIEWS  (derived data — computed, never stored)
-- =====================================================================
CREATE VIEW IF NOT EXISTS v_club_summary AS
SELECT c.club_id, c.name, c.category, c.tagline, c.status, c.room_no, c.founded_year,
       (SELECT COUNT(*) FROM Membership m WHERE m.club_id = c.club_id)                          AS member_count,
       (SELECT COUNT(*) FROM Event e WHERE e.club_id = c.club_id AND e.status = 'Upcoming')      AS upcoming_events,
       (SELECT COALESCE(SUM(f.amount),0) FROM Club_Funding f WHERE f.club_id = c.club_id)        AS total_funding,
       (SELECT p.name FROM Membership m JOIN Person p ON p.person_id = m.student_id
         WHERE m.club_id = c.club_id AND m.role = 'President')                                   AS president_name
FROM Club c;

CREATE VIEW IF NOT EXISTS v_event_seats AS
SELECT e.*, c.name AS club_name, c.category AS club_category,
       (SELECT COUNT(*) FROM Event_Registration r WHERE r.event_id = e.event_id) AS registered,
       e.capacity - (SELECT COUNT(*) FROM Event_Registration r WHERE r.event_id = e.event_id) AS seats_left
FROM Event e JOIN Club c ON c.club_id = e.club_id;

CREATE VIEW IF NOT EXISTS v_club_funding_by_year AS
SELECT club_id, academic_year, source_type, SUM(amount) AS total, COUNT(*) AS entries
FROM Club_Funding
GROUP BY club_id, academic_year, source_type;
