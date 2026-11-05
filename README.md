# ClubHub — Student Club & Organisation Management System

A DBMS mini-project: a public campus portal for societies and events, with role-based
panels for students, club heads, faculty advisors and admins — on a 16-table SQLite
schema normalised to BCNF.

```
Flask 3 · SQLite 3 · Jinja2 · no JS framework · 25 tests
```

## Run it

```bash
pip install -r requirements.txt
python database/init_db.py      # builds database/clubhub.db from schema.sql + seed.sql
python app.py                   # http://127.0.0.1:5000
```

Tests: `python -m pytest tests/ -q`

### Demo logins

| Role | Username | Password | What you can do |
|---|---|---|---|
| Admin | `admin` | `admin123` | everything, incl. schema browser & SQL console |
| Club head (ByteForge President) | `2023UCS1001` | `2023UCS1001` | manage ByteForge: events, members, notices, funding, assets, docs |
| Student | `2025UCS1302` | `2025UCS1302` | join clubs, register for events |
| Faculty advisor (ByteForge) | `neelam.sinha` | `faculty123` | read-all for advised clubs, post alerts, see auto-generated flags |

Every seeded student logs in with `roll_no / roll_no`; every faculty member with
`<email-prefix> / faculty123`.

## Where is the database?

`database/clubhub.db` is a single file — SQLite needs no server (no XAMPP). To look at the
tables visually, open that file in **DB Browser for SQLite** (free), or use the built-in
**Admin → Schema browser** and **Admin → SQL console** pages, which read `sqlite_master`
live and run read-only queries against the real database.

## What's in the box

```
app.py              Flask factory, template filters, error pages
auth.py             RBAC: load user, role predicates, decorators
db.py               connection helper (PRAGMA foreign_keys = ON on every connection)
crud.py             generic CRUD engine for events / funding / assets / documents / announcements
queries.py          shared read queries
constants.py        enumerations mirroring the CHECK constraints
routes/
  public.py         /, /clubs, /clubs/<id>, /events, /events/<id>, /notices   (no login)
  auth_routes.py    /login, /logout
  student.py        /me, register/cancel, join/leave
  manage.py         /manage/<club_id>/…  club-head panel (also used by admins)
  faculty.py        /faculty/…  advisor panel with "needs attention" flags
  admin.py          /admin/…  every table + schema browser + SQL console
database/
  schema.sql        16 tables · 18 FKs · 13 triggers · 3 views · 9 indexes
  seed.sql          6 clubs, 14 students, 5 faculty, 11 events, funding, assets, docs
  init_db.py        builds the DB and hashes the demo passwords
docs/
  DATABASE_DESIGN.md  ER model, RBAC, constraints, BCNF proof, viva Q&A
  erd.mmd / erd.png   ER diagram (Mermaid)
templates/, static/ server-rendered UI
tests/              pytest suite: constraints, triggers, RBAC, CRUD
```

## Schema at a glance

```
Person ─┬─ Student ──┬─ Membership ──────── Club ─┬─ Technical_Club
        │            ├─ Event_Registration ─ Event ┘ ├─ Cultural_Club
        │            └─ User_Account                 ├─ Sports_Club
        └─ Faculty ──┬─ Club_Advisor ──────────────┤
                     └─ User_Account                 ├─ Club_Funding
                                                     ├─ Club_Asset
Admin ─── User_Account (person_id NULL)              ├─ Club_Document
                                                     └─ Announcement (club_id NULL ⇒ college-wide)
```

Two generalisation hierarchies (Person ⇒ Student | Faculty; Club ⇒ Technical | Cultural |
Sports), three M:N bridges, six 1:N children of Club. "Club head" is not stored — it is
derived from `Membership.role`. Full reasoning in `docs/DATABASE_DESIGN.md`.

## Access matrix

| | Public | Student | Club head | Faculty (advised clubs) | Admin |
|---|:-:|:-:|:-:|:-:|:-:|
| Browse clubs, events, notices, public docs | ✓ | ✓ | ✓ | ✓ | ✓ |
| Member list | names + roles | names + roles | full contact details | full contact details | full |
| Register / join | | ✓ | ✓ | | ✓ |
| Create / edit events, notices, members, funding, assets, docs | | | own club | notices only | all |
| See funding, private docs, registrant lists | | | own club | ✓ | all |
| Students, faculty, accounts, clubs, advisors, SQL console | | | | | ✓ |
