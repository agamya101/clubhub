-- =====================================================================
-- ClubHub — Student Club & Organisation Management System
-- Database Schema (MySQL 8 / MariaDB 10.4+, as shipped with XAMPP)
-- Normalised to BCNF.
--
-- Import: phpMyAdmin → Import → this file   or   python database/init_db.py
--
-- Design notes
--   * Generalisation / specialisation #1: PERSON ⇒ STUDENT | FACULTY
--       (disjoint, total — every Person is exactly one of the two)
--   * Generalisation / specialisation #2: CLUB ⇒ TECHNICAL_CLUB |
--       CULTURAL_CLUB | SPORTS_CLUB  (disjoint, partial)
--   * Subtype rows share the supertype's primary key (PK = FK).
--   * "Club Head" is NOT a stored role: derived from MEMBERSHIP.role.
--   * Derived values (member counts, seats left, funding totals) are
--       computed in views, never stored.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS clubhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE clubhub;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW  IF EXISTS v_club_funding_by_year, v_event_seats, v_club_summary;
DROP TABLE IF EXISTS Announcement, Club_Document, Club_Asset, Club_Funding, Event_Registration, Event,
                     Membership, Club_Advisor, Sports_Club, Cultural_Club, Technical_Club, Club,
                     User_Account, Faculty, Student, Person;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- 1. PERSON  (supertype of Student and Faculty)
-- ---------------------------------------------------------------------
CREATE TABLE Person (
    person_id   INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    phone       VARCHAR(15),
    CONSTRAINT chk_person_name  CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_person_email CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_person_phone CHECK (phone IS NULL OR CHAR_LENGTH(phone) BETWEEN 10 AND 15)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. STUDENT  (subtype of Person)
-- ---------------------------------------------------------------------
CREATE TABLE Student (
    student_id  INT PRIMARY KEY,
    roll_no     VARCHAR(20) NOT NULL UNIQUE,
    branch      ENUM('CSE','IT','ECE','EE','ME','CE','BT','MAC','CSAI','CSDS') NOT NULL,
    year        TINYINT NOT NULL,
    CONSTRAINT fk_student_person FOREIGN KEY (student_id) REFERENCES Person(person_id) ON DELETE CASCADE,
    CONSTRAINT chk_student_year CHECK (year BETWEEN 1 AND 4)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. FACULTY  (subtype of Person)
-- ---------------------------------------------------------------------
CREATE TABLE Faculty (
    faculty_id  INT PRIMARY KEY,
    department  VARCHAR(100) NOT NULL,
    designation ENUM('Professor','Associate Professor','Assistant Professor','Lecturer') NOT NULL,
    CONSTRAINT fk_faculty_person FOREIGN KEY (faculty_id) REFERENCES Person(person_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. USER_ACCOUNT  (login + role; Admin accounts have no Person)
-- ---------------------------------------------------------------------
CREATE TABLE User_Account (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('Admin','Student','Faculty') NOT NULL,
    person_id     INT NULL UNIQUE,
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account_person FOREIGN KEY (person_id) REFERENCES Person(person_id) ON DELETE CASCADE,
    CONSTRAINT chk_username_len CHECK (CHAR_LENGTH(username) >= 3),
    CONSTRAINT chk_admin_no_person CHECK ((role = 'Admin' AND person_id IS NULL) OR (role <> 'Admin' AND person_id IS NOT NULL))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. CLUB  (supertype)
-- ---------------------------------------------------------------------
CREATE TABLE Club (
    club_id       INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL UNIQUE,
    category      ENUM('Technical','Cultural','Sports','Literary','Social','Academic') NOT NULL,
    tagline       VARCHAR(120),
    description   TEXT,
    room_no       VARCHAR(40),
    founded_year  SMALLINT,
    contact_email VARCHAR(120),
    status        ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
    CONSTRAINT chk_club_year  CHECK (founded_year IS NULL OR founded_year BETWEEN 1950 AND 2100),
    CONSTRAINT chk_club_email CHECK (contact_email IS NULL OR contact_email LIKE '%_@_%._%')
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6–8. CLUB subtypes (partial, disjoint — discriminator = Club.category)
-- ---------------------------------------------------------------------
CREATE TABLE Technical_Club (
    club_id     INT PRIMARY KEY,
    github_url  VARCHAR(200),
    tech_stack  VARCHAR(200) NOT NULL,
    CONSTRAINT fk_tech_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Cultural_Club (
    club_id     INT PRIMARY KEY,
    art_form    ENUM('Dance','Music','Drama','Fine Arts','Fashion','Photography','Film') NOT NULL,
    CONSTRAINT fk_cult_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE Sports_Club (
    club_id     INT PRIMARY KEY,
    sport       VARCHAR(60) NOT NULL,
    coach_name  VARCHAR(100),
    CONSTRAINT fk_sport_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. CLUB_ADVISOR  (M:N  Club ↔ Faculty)
-- ---------------------------------------------------------------------
CREATE TABLE Club_Advisor (
    club_id     INT NOT NULL,
    faculty_id  INT NOT NULL,
    assigned_on DATE NOT NULL DEFAULT (CURRENT_DATE),
    PRIMARY KEY (club_id, faculty_id),
    CONSTRAINT fk_advisor_club    FOREIGN KEY (club_id)    REFERENCES Club(club_id)       ON DELETE CASCADE,
    CONSTRAINT fk_advisor_faculty FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. MEMBERSHIP  (M:N  Student ↔ Club, with role)
-- ---------------------------------------------------------------------
CREATE TABLE Membership (
    student_id  INT NOT NULL,
    club_id     INT NOT NULL,
    role        ENUM('President','Vice President','Secretary','Treasurer','Core Member','Member') NOT NULL DEFAULT 'Member',
    joined_at   DATE NOT NULL DEFAULT (CURRENT_DATE),
    PRIMARY KEY (student_id, club_id),
    CONSTRAINT fk_member_student FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_member_club    FOREIGN KEY (club_id)    REFERENCES Club(club_id)       ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11. EVENT  (1:N  Club → Event)
-- ---------------------------------------------------------------------
CREATE TABLE Event (
    event_id              INT AUTO_INCREMENT PRIMARY KEY,
    club_id               INT NOT NULL,
    title                 VARCHAR(150) NOT NULL,
    event_type            ENUM('Workshop','Webinar','Hackathon','Competition','Session','Cultural','Sports','Meetup') NOT NULL,
    description           TEXT,
    event_date            DATETIME NOT NULL,
    registration_deadline DATE NULL,
    venue                 VARCHAR(120) NOT NULL,
    capacity              INT NOT NULL,
    status                ENUM('Upcoming','Ongoing','Completed','Cancelled') NOT NULL DEFAULT 'Upcoming',
    CONSTRAINT fk_event_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE,
    CONSTRAINT chk_event_capacity CHECK (capacity > 0),
    CONSTRAINT chk_event_deadline CHECK (registration_deadline IS NULL OR registration_deadline <= DATE(event_date))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 12. EVENT_REGISTRATION  (M:N  Student ↔ Event). Cancel = delete row.
-- ---------------------------------------------------------------------
CREATE TABLE Event_Registration (
    student_id    INT NOT NULL,
    event_id      INT NOT NULL,
    registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, event_id),
    CONSTRAINT fk_reg_student FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_reg_event   FOREIGN KEY (event_id)   REFERENCES Event(event_id)     ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 13. CLUB_FUNDING  (1:N  Club → Funding entries)
-- ---------------------------------------------------------------------
CREATE TABLE Club_Funding (
    funding_id    INT AUTO_INCREMENT PRIMARY KEY,
    club_id       INT NOT NULL,
    source_type   ENUM('College Grant','Sponsorship','Membership Fees','Event Revenue','Alumni Donation','Other') NOT NULL,
    sponsor_name  VARCHAR(120),
    amount        DECIMAL(12,2) NOT NULL,
    received_on   DATE NOT NULL,
    academic_year CHAR(7) NOT NULL,
    remarks       VARCHAR(255),
    CONSTRAINT fk_funding_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE,
    CONSTRAINT chk_funding_amount CHECK (amount > 0),
    CONSTRAINT chk_funding_year   CHECK (academic_year REGEXP '^[0-9]{4}-[0-9]{2}$')
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 14. CLUB_ASSET  (1:N  Club → physical inventory)
-- ---------------------------------------------------------------------
CREATE TABLE Club_Asset (
    asset_id     INT AUTO_INCREMENT PRIMARY KEY,
    club_id      INT NOT NULL,
    name         VARCHAR(120) NOT NULL,
    asset_type   ENUM('Electronics','Instrument','Furniture','Sports Gear','Costume','Stationery','Other') NOT NULL,
    quantity     INT NOT NULL,
    item_condition ENUM('New','Good','Fair','Needs Repair','Retired') NOT NULL DEFAULT 'Good',
    acquired_on  DATE,
    cost         DECIMAL(12,2),
    CONSTRAINT fk_asset_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE,
    CONSTRAINT chk_asset_qty  CHECK (quantity > 0),
    CONSTRAINT chk_asset_cost CHECK (cost IS NULL OR cost >= 0)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 15. CLUB_DOCUMENT  (1:N  Club → documents / links)
-- ---------------------------------------------------------------------
CREATE TABLE Club_Document (
    doc_id       INT AUTO_INCREMENT PRIMARY KEY,
    club_id      INT NOT NULL,
    title        VARCHAR(150) NOT NULL,
    doc_type     ENUM('Constitution','Minutes','Budget','Report','Media','Form','Other') NOT NULL,
    url          VARCHAR(300) NOT NULL,
    visibility   ENUM('Public','Members','Private') NOT NULL DEFAULT 'Members',
    uploaded_on  DATE NOT NULL DEFAULT (CURRENT_DATE),
    CONSTRAINT fk_doc_club FOREIGN KEY (club_id) REFERENCES Club(club_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 16. ANNOUNCEMENT  (club notice or college-wide alert)
-- ---------------------------------------------------------------------
CREATE TABLE Announcement (
    announcement_id INT AUTO_INCREMENT PRIMARY KEY,
    club_id         INT NULL,
    posted_by       INT NOT NULL,
    title           VARCHAR(150) NOT NULL,
    content         TEXT NOT NULL,
    priority        ENUM('Normal','Alert') NOT NULL DEFAULT 'Normal',
    is_pinned       TINYINT(1) NOT NULL DEFAULT 0,
    posted_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATE NULL,
    CONSTRAINT fk_ann_club FOREIGN KEY (club_id)   REFERENCES Club(club_id)          ON DELETE CASCADE,
    CONSTRAINT fk_ann_user FOREIGN KEY (posted_by) REFERENCES User_Account(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================================
-- INDEXES  (FK columns get an index automatically in InnoDB; these are
-- the composite ones the UI filters on)
-- =====================================================================
CREATE INDEX idx_event_club_date   ON Event(club_id, event_date);
CREATE INDEX idx_event_status_date ON Event(status, event_date);
CREATE INDEX idx_funding_club_year ON Club_Funding(club_id, academic_year);
CREATE INDEX idx_announcement_club ON Announcement(club_id, posted_at);

-- =====================================================================
-- TRIGGERS  (rules a CHECK constraint cannot express)
-- =====================================================================
DELIMITER $$

-- --- Disjointness of PERSON subtypes -----------------------------------
CREATE TRIGGER trg_student_disjoint BEFORE INSERT ON Student FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM Faculty WHERE faculty_id = NEW.student_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Person is already a Faculty member; cannot also be a Student';
  END IF;
END$$

CREATE TRIGGER trg_faculty_disjoint BEFORE INSERT ON Faculty FOR EACH ROW
BEGIN
  IF EXISTS (SELECT 1 FROM Student WHERE student_id = NEW.faculty_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Person is already a Student; cannot also be Faculty';
  END IF;
END$$

-- --- CLUB subtype must match the discriminator (Club.category) ---------
CREATE TRIGGER trg_technical_club_category BEFORE INSERT ON Technical_Club FOR EACH ROW
BEGIN
  IF (SELECT category FROM Club WHERE club_id = NEW.club_id) <> 'Technical' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Technical_Club row requires Club.category = Technical';
  END IF;
END$$

CREATE TRIGGER trg_cultural_club_category BEFORE INSERT ON Cultural_Club FOR EACH ROW
BEGIN
  IF (SELECT category FROM Club WHERE club_id = NEW.club_id) <> 'Cultural' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cultural_Club row requires Club.category = Cultural';
  END IF;
END$$

CREATE TRIGGER trg_sports_club_category BEFORE INSERT ON Sports_Club FOR EACH ROW
BEGIN
  IF (SELECT category FROM Club WHERE club_id = NEW.club_id) <> 'Sports' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sports_Club row requires Club.category = Sports';
  END IF;
END$$

-- If a club changes category, its old subtype row is no longer valid.
CREATE TRIGGER trg_club_category_change AFTER UPDATE ON Club FOR EACH ROW
BEGIN
  IF OLD.category <> NEW.category THEN
    DELETE FROM Technical_Club WHERE club_id = NEW.club_id AND NEW.category <> 'Technical';
    DELETE FROM Cultural_Club  WHERE club_id = NEW.club_id AND NEW.category <> 'Cultural';
    DELETE FROM Sports_Club    WHERE club_id = NEW.club_id AND NEW.category <> 'Sports';
  END IF;
END$$

-- --- Account role must agree with the Person subtype -------------------
CREATE TRIGGER trg_account_role_matches_person BEFORE INSERT ON User_Account FOR EACH ROW
BEGIN
  IF (NEW.role = 'Student' AND NOT EXISTS (SELECT 1 FROM Student WHERE student_id = NEW.person_id))
  OR (NEW.role = 'Faculty' AND NOT EXISTS (SELECT 1 FROM Faculty WHERE faculty_id = NEW.person_id)) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User_Account.role does not match the Person subtype';
  END IF;
END$$

-- --- Event capacity & status -------------------------------------------
CREATE TRIGGER trg_registration_rules BEFORE INSERT ON Event_Registration FOR EACH ROW
BEGIN
  IF (SELECT status FROM Event WHERE event_id = NEW.event_id) <> 'Upcoming' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registrations are only accepted for Upcoming events';
  END IF;
  IF (SELECT COUNT(*) FROM Event_Registration WHERE event_id = NEW.event_id)
     >= (SELECT capacity FROM Event WHERE event_id = NEW.event_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event is at full capacity';
  END IF;
END$$

CREATE TRIGGER trg_event_capacity_floor BEFORE UPDATE ON Event FOR EACH ROW
BEGIN
  IF NEW.capacity < (SELECT COUNT(*) FROM Event_Registration WHERE event_id = NEW.event_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Capacity cannot be lower than current registrations';
  END IF;
END$$

-- --- Exactly one President per club ------------------------------------
CREATE TRIGGER trg_one_president_insert BEFORE INSERT ON Membership FOR EACH ROW
BEGIN
  IF NEW.role = 'President' AND EXISTS (SELECT 1 FROM Membership WHERE club_id = NEW.club_id AND role = 'President') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This club already has a President';
  END IF;
END$$

CREATE TRIGGER trg_one_president_update BEFORE UPDATE ON Membership FOR EACH ROW
BEGIN
  IF NEW.role = 'President' AND EXISTS (SELECT 1 FROM Membership
       WHERE club_id = NEW.club_id AND role = 'President' AND student_id <> NEW.student_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This club already has a President';
  END IF;
END$$

-- --- College-wide announcements can only be posted by Admins -----------
CREATE TRIGGER trg_collegewide_announcement_admin_only BEFORE INSERT ON Announcement FOR EACH ROW
BEGIN
  IF NEW.club_id IS NULL AND (SELECT role FROM User_Account WHERE user_id = NEW.posted_by) <> 'Admin' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only Admins can post college-wide announcements';
  END IF;
END$$

DELIMITER ;

-- =====================================================================
-- VIEWS  (derived data — computed, never stored)
-- =====================================================================
CREATE VIEW v_club_summary AS
SELECT c.club_id, c.name, c.category, c.tagline, c.status, c.room_no, c.founded_year,
       (SELECT COUNT(*) FROM Membership m WHERE m.club_id = c.club_id)                          AS member_count,
       (SELECT COUNT(*) FROM Event e WHERE e.club_id = c.club_id AND e.status = 'Upcoming')      AS upcoming_events,
       (SELECT COALESCE(SUM(f.amount),0) FROM Club_Funding f WHERE f.club_id = c.club_id)        AS total_funding,
       (SELECT p.name FROM Membership m JOIN Person p ON p.person_id = m.student_id
         WHERE m.club_id = c.club_id AND m.role = 'President' LIMIT 1)                           AS president_name
FROM Club c;

CREATE VIEW v_event_seats AS
SELECT e.*, c.name AS club_name, c.category AS club_category,
       (SELECT COUNT(*) FROM Event_Registration r WHERE r.event_id = e.event_id) AS registered,
       e.capacity - (SELECT COUNT(*) FROM Event_Registration r WHERE r.event_id = e.event_id) AS seats_left
FROM Event e JOIN Club c ON c.club_id = e.club_id;

CREATE VIEW v_club_funding_by_year AS
SELECT club_id, academic_year, source_type, SUM(amount) AS total, COUNT(*) AS entries
FROM Club_Funding
GROUP BY club_id, academic_year, source_type;
