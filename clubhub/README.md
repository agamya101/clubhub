# ClubHub — Student Club & Organisation Management System

A DBMS mini-project: a public campus portal for societies and events, with role-based
panels for students, club heads, faculty advisors and admins — on a 16-table MySQL
schema normalised to BCNF.

```
Flask 3 · MySQL / MariaDB (XAMPP) · Jinja2 · no JS framework · 25 tests
```

## Run it (XAMPP)

1. Open the **XAMPP Control Panel** and start **MySQL** (Apache is not needed; Flask serves the app).
2. In the project folder:

```bash
pip install -r requirements.txt
python database/init_db.py      # creates database `clubhub` (16 tables, triggers, views, seed data)
python app.py                   # http://127.0.0.1:5000
```

The app connects as `root` with an empty password on `127.0.0.1:3306` — XAMPP's default.
If you changed it, set environment variables before running:
`CLUBHUB_DB_USER`, `CLUBHUB_DB_PASSWORD`, `CLUBHUB_DB_HOST`, `CLUBHUB_DB_PORT`.

Prefer phpMyAdmin? Import `database/schema.sql`, then `database/seed.sql`, then run
`python database/init_db.py` anyway — it also creates the login accounts with hashed passwords.

Tests: `python -m pytest tests/ -q` (builds and uses a throwaway database `clubhub_test`).

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

In MySQL, as database `clubhub`. Open **http://localhost/phpmyadmin** → `clubhub` to browse
tables, or use the built-in **Admin → Schema browser** and **Admin → SQL console** pages,
which read `information_schema` live and run read-only queries against the real database.

## What's in the box

```
app.py              Flask factory, template filters, error pages
auth.py             RBAC: load user, role predicates, decorators
db.py               MySQL connection helper, query()/execute()/transaction()
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
  schema.sql        16 tables · 18 FKs · 12 triggers · 3 views (MySQL / MariaDB)
  seed.sql          6 clubs, 14 students, 5 faculty, 11 events, funding, assets, docs
  init_db.py        creates the database, runs schema + seed, hashes the demo passwords
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
