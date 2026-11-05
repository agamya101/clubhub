# ClubHub — Database Design

Student Club & Organisation Management System · SQLite 3 · 16 tables · BCNF

---

## 1. Requirements the schema answers

| Need | Where it lives |
|---|---|
| Public can browse societies, events, notices | `Club`, `Event`, `Announcement` + views |
| Students sign in, join clubs, register for events | `User_Account`, `Membership`, `Event_Registration` |
| Club heads manage their own club | derived from `Membership.role` |
| Faculty advisors see everything about advised clubs and raise alerts | `Club_Advisor`, `Announcement.priority` |
| Societies record funding, inventory and documents | `Club_Funding`, `Club_Asset`, `Club_Document` |
| Students and faculty share identity attributes | `Person` supertype |
| Technical / cultural / sports clubs carry extra attributes | `Club` subtypes |

---

## 2. Entity-Relationship model

### 2.1 Generalisation / specialisation

**PERSON ⇒ STUDENT | FACULTY** — *disjoint, total*
`Person` holds what every human in the system has (`name`, `email`, `phone`).
`Student` adds `roll_no`, `branch`, `year`; `Faculty` adds `department`, `designation`.
The subtype's primary key **is** the supertype's key (`student_id = person_id`), so a
Student row cannot exist without its Person row. Triggers `trg_student_disjoint` /
`trg_faculty_disjoint` guarantee a person is never both.

**CLUB ⇒ TECHNICAL_CLUB | CULTURAL_CLUB | SPORTS_CLUB** — *disjoint, partial*
`Club.category` is the discriminator. Literary, Social and Academic clubs have no extra
attributes so they have no subtype row (partial). Triggers
`trg_*_club_category` refuse a subtype row whose parent's category disagrees, and
`trg_club_category_change` drops the stale subtype row if a club is recategorised.

### 2.2 Relationships

| Relationship | Type | Participation | Implemented as |
|---|---|---|---|
| Person – Student / Faculty | ISA | total on Person | PK = FK |
| Club – subtype | ISA | partial on Club | PK = FK |
| Person – User_Account | 1 : 0..1 | partial both ways (admins have no Person) | `User_Account.person_id UNIQUE` |
| Student – Club (JOINS) | M : N | partial both | `Membership(student_id, club_id)` + `role` |
| Faculty – Club (ADVISES) | M : N | partial both | `Club_Advisor(club_id, faculty_id)` |
| Student – Event (REGISTERS) | M : N | partial both | `Event_Registration(student_id, event_id)` |
| Club – Event (ORGANISES) | 1 : N | **total** on Event | `Event.club_id NOT NULL` |
| Club – Club_Funding | 1 : N | total on Funding | `club_id NOT NULL` |
| Club – Club_Asset | 1 : N | total on Asset | `club_id NOT NULL` |
| Club – Club_Document | 1 : N | total on Document | `club_id NOT NULL` |
| Club – Announcement | 1 : N | **partial** on Announcement (NULL ⇒ college-wide) | `club_id NULL`able |
| User_Account – Announcement (POSTS) | 1 : N | total on Announcement | `posted_by NOT NULL` |

Weak-entity note: the three bridge tables and the subtype tables are identified by their
parents' keys. `Membership` is a relationship *with attributes* (`role`, `joined_at`).

### 2.3 Drawing it for the viva

`erd.mmd` / `erd.png` is a crow's-foot diagram generated from the schema. For Chen
notation: draw ISA triangles under PERSON and CLUB, diamonds for JOINS / ADVISES /
REGISTERS / ORGANISES / POSTS, double lines for total participation (Event→Club,
subtype→supertype), and write `role`, `joined_at` as attributes on the JOINS diamond.

---

## 3. Role-based access control

| Tier | Stored as | Rights |
|---|---|---|
| Public | — | read clubs, events, notices, public docs, member names + roles |
| Student | `User_Account.role='Student'` | + register / cancel events, join / leave clubs, own profile, member-visibility docs |
| **Club Head** | **derived**: `Membership.role IN ('President','Vice President')` | + full CRUD on that club's events, notices, members, funding, assets, docs; sees member contact details |
| Faculty | `User_Account.role='Faculty'` | read everything for clubs in `Club_Advisor`; post notices / alerts there; auto-generated "needs attention" flags |
| Admin | `User_Account.role='Admin'` | everything, plus people, accounts, clubs, advisors, SQL console |

Club Head is deliberately **not** a column. If it were stored in `User_Account` it would
duplicate `Membership.role` — an update anomaly waiting to happen (promote someone and
forget to flip the flag). Deriving it means one write grants the rights.

Passwords are stored as `werkzeug` PBKDF2 hashes. `User_Account` has a CHECK that
Admins have `person_id IS NULL` and everyone else does not; a trigger checks the role
matches the person's subtype.

---

## 4. Constraints inventory

| Kind | Examples |
|---|---|
| PRIMARY KEY | every table; composite on the three bridges; PK=FK on the five subtypes |
| FOREIGN KEY + ON DELETE CASCADE | 18 FKs. Deleting a Person removes their Student row, memberships, registrations and account; deleting a Club removes everything under it |
| UNIQUE | `Person.email`, `Student.roll_no`, `Club.name`, `User_Account.username`, `User_Account.person_id` |
| NOT NULL | all identifying / required attributes |
| CHECK (domain) | 15 enumerations (`category`, `role`, `event_type`, `status`, `source_type`, …), `year BETWEEN 1 AND 4`, `capacity > 0`, `amount > 0`, email `LIKE '%_@_%._%'`, `academic_year GLOB 'NNNN-NN'` |
| CHECK (row) | `registration_deadline <= event_date`; Admin ⇔ `person_id IS NULL` |
| DEFAULT | `status='Active'`, `role='Member'`, `priority='Normal'`, timestamps |
| TRIGGERS (13) | subtype disjointness ×2, subtype/category agreement ×4, account-role agreement, event capacity ×2, registrations only for Upcoming events, exactly one President per club ×2, college-wide notices admin-only |
| VIEWS (3) | `v_club_summary`, `v_event_seats`, `v_club_funding_by_year` — all derived numbers live here, never in base tables |
| INDEXES (9) | every FK the UI filters on, plus `(status, event_date)` |

---

## 5. Normalisation — BCNF proof

Method: list each relation's functional dependencies; show every determinant is a
candidate key. (A relation is in BCNF iff for every non-trivial FD X → Y, X is a superkey.
BCNF ⊆ 3NF ⊆ 2NF ⊆ 1NF.)

**1NF** — every column atomic (no lists: a student's clubs are rows in `Membership`, a
club's tech stack is a single descriptive string, not a repeating group); every table has a PK.

**2NF** — only the composite-key tables can have partial dependencies:
- `Membership(student_id, club_id)`: `role`, `joined_at` depend on the *pair* (a student's role differs per club). ✔
- `Event_Registration(student_id, event_id)`: `registered_at` depends on the pair. ✔
- `Club_Advisor(club_id, faculty_id)`: `assigned_on` depends on the pair. ✔

**3NF / BCNF** — per relation:

| Relation | FDs | Determinants are keys? |
|---|---|---|
| Person | `person_id → name, email, phone`; `email → person_id, name, phone` | yes — `person_id` and `email` are both candidate keys |
| Student | `student_id → roll_no, branch, year`; `roll_no → student_id, …` | yes — two candidate keys |
| Faculty | `faculty_id → department, designation` | yes |
| User_Account | `user_id → …`; `username → …`; `person_id → …` (when not null) | yes — three candidate keys |
| Club | `club_id → …`; `name → …` | yes. `category` does **not** determine `room_no`, `founded_year` etc. — no transitive FD |
| Technical/Cultural/Sports_Club | `club_id → attrs` | yes |
| Club_Advisor | `(club_id, faculty_id) → assigned_on` | yes |
| Membership | `(student_id, club_id) → role, joined_at` | yes |
| Event | `event_id → club_id, title, …` | yes. `club_id` does not determine `venue` (clubs host events in many venues) — no transitive FD. `club_name` is deliberately **not** stored here (that would be `event_id → club_id → club_name`) |
| Event_Registration | `(student_id, event_id) → registered_at` | yes |
| Club_Funding | `funding_id → club_id, source_type, sponsor_name, amount, …` | yes. `sponsor_name` does not determine `source_type` (the same sponsor could be a grant one year, sponsorship the next) |
| Club_Asset | `asset_id → …` | yes |
| Club_Document | `doc_id → …` | yes |
| Announcement | `announcement_id → club_id, posted_by, …` | yes. `posted_by` does not determine `club_id` (a faculty member advises several clubs) |

Things we refused to store because they are derivable (would break 3NF or create
redundancy): member counts, seats left, funding totals, `club_name` on child tables,
`is_club_head`, `age`. All of these come from the views or a JOIN.

**Why not go further?** 4NF/5NF concerns multi-valued dependencies; none of our tables
has two independent multi-valued facts about the same key (Student's clubs and Student's
event registrations are in separate tables already).

---

## 6. Sample queries the app runs

```sql
-- Members of a club with role ordering (JOIN across supertype)
SELECT p.name, s.branch, s.year, m.role
FROM Membership m
JOIN Student s ON s.student_id = m.student_id
JOIN Person  p ON p.person_id  = s.student_id
WHERE m.club_id = ?
ORDER BY CASE m.role WHEN 'President' THEN 1 WHEN 'Vice President' THEN 2 ELSE 3 END, p.name;

-- Seats left (view hides the correlated subquery)
SELECT title, club_name, seats_left FROM v_event_seats WHERE status = 'Upcoming';

-- Which clubs does this student head?  (RBAC derivation)
SELECT club_id FROM Membership WHERE student_id = ? AND role IN ('President','Vice President');

-- Faculty "needs attention": events within 14 days under 30 % booked
SELECT * FROM v_event_seats
WHERE club_id IN (SELECT club_id FROM Club_Advisor WHERE faculty_id = ?)
  AND status = 'Upcoming'
  AND event_date BETWEEN datetime('now') AND datetime('now', '+14 days')
  AND registered * 1.0 / capacity < 0.30;

-- Funding by year and source (GROUP BY on a view)
SELECT academic_year, source_type, total FROM v_club_funding_by_year WHERE club_id = ?;

-- Transaction: create Person + Student + account atomically (routes/admin.py)
BEGIN;
INSERT INTO Person (name, email, phone) VALUES (?, ?, ?);
INSERT INTO Student (student_id, roll_no, branch, year) VALUES (last_insert_rowid(), ?, ?, ?);
INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?, ?, 'Student', ?);
COMMIT;
```

---

## 7. Likely viva questions

- *Why a Person table?* Students and faculty share name/email/phone; one table, one UNIQUE
  email, one place to update. Classic generalisation; subtypes carry only their own attributes.
- *Total vs partial?* Person→subtype is total (trigger + app ensure every Person is one of
  them); Club→subtype is partial (Literary clubs have no subtype row).
- *Where is "club head" stored?* Nowhere — derived from `Membership.role`. Storing it would
  duplicate a fact.
- *How is capacity enforced?* A `BEFORE INSERT` trigger counts registrations; a CHECK cannot
  reference another table.
- *Why cascade deletes?* A membership without a student is meaningless. Faculty deletion
  cascades only to `Club_Advisor`, so clubs survive losing an advisor.
- *What stops a Student account for a Faculty person?* `trg_account_role_matches_person`.
- *Is it BCNF?* Yes — section 5; every determinant is a candidate key, and all derived values
  are in views.
