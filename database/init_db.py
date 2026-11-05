"""
ClubHub database initialiser.

    python database/init_db.py            # rebuild database/clubhub.db
    python database/init_db.py --path X   # build somewhere else (tests)

Runs schema.sql, seed.sql, then creates login accounts with hashed
passwords and the seed announcements (which need account ids).

Seed logins
    admin        / admin123
    <roll_no>    / <roll_no>       e.g. 2023UCS1001 / 2023UCS1001
    <email user> / faculty123      e.g. neelam.sinha / faculty123
"""

import argparse
import os
import sqlite3

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "clubhub.db")
SCHEMA = os.path.join(BASE_DIR, "schema.sql")
SEED = os.path.join(BASE_DIR, "seed.sql")

ANNOUNCEMENTS = [
    # (club_id or None, poster username, title, content, priority, pinned, expires_at)
    (None, "admin", "Winter fest dates announced",
     "Moksha-Sphere 2027 will run 13–15 February. Societies must submit event proposals through their faculty advisor by 30 November.",
     "Alert", 1, "2026-11-30"),
    (None, "admin", "Society room bookings move online",
     "From 10 November, room and auditorium bookings go through the Student Welfare portal. Paper forms will no longer be accepted.",
     "Normal", 0, None),
    (1, "2023UCS1001", "HackForge 2026 registrations are open",
     "120 seats, teams of up to four. Register individually; team formation happens on the Discord. Deadline 18 November.",
     "Normal", 1, "2026-11-18"),
    (1, "neelam.sinha", "Lab 205 closed for maintenance on 8 Nov",
     "Electrical work in Lab 205 on Saturday 8 November. Build night moves to Lab 204 for that week only.",
     "Alert", 0, "2026-11-08"),
    (2, "2023UIT1042", "Auditions: what to prepare",
     "Bring a 60-second solo in any style. Crew leads will teach a short combination on the spot — no prior choreography needed.",
     "Normal", 1, "2026-11-14"),
    (3, "amit.saxena", "Medical certificates required for Ashwa Open",
     "Every participant must upload a fitness certificate dated within the last 6 months before 1 December. No certificate, no bib.",
     "Alert", 1, "2026-12-01"),
    (4, "2022UEE1051", "Marginalia issue 7 — call for submissions",
     "Poetry, flash fiction and essays under 1500 words. Theme: 'Thresholds'. Submissions close 25 November.",
     "Normal", 0, "2026-11-25"),
    (5, "2023UCE1077", "Volunteers needed for Blood Donation Camp",
     "We need 12 volunteers for registration desks and refreshments on 10 November, 9am–2pm. Reply on the group.",
     "Normal", 0, "2026-11-10"),
    (6, "farah.khan", "Alumni panel — submit your questions",
     "Send questions for the Quant Careers panel through the form by 15 November so the moderators can group them.",
     "Normal", 0, "2026-11-15"),
]


def run_sql_file(conn, path):
    with open(path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def create_accounts(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?,?,?,NULL)",
                ("admin", generate_password_hash("admin123"), "Admin"))

    for sid, roll in cur.execute("SELECT student_id, roll_no FROM Student").fetchall():
        conn.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?,?,?,?)",
                     (roll, generate_password_hash(roll), "Student", sid))

    for fid, email in cur.execute(
            "SELECT f.faculty_id, p.email FROM Faculty f JOIN Person p ON p.person_id = f.faculty_id").fetchall():
        username = email.split("@")[0]
        conn.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?,?,?,?)",
                     (username, generate_password_hash("faculty123"), "Faculty", fid))


def create_announcements(conn):
    for club_id, username, title, content, priority, pinned, expires in ANNOUNCEMENTS:
        uid = conn.execute("SELECT user_id FROM User_Account WHERE username = ?", (username,)).fetchone()[0]
        conn.execute("""INSERT INTO Announcement (club_id, posted_by, title, content, priority, is_pinned, expires_at)
                        VALUES (?,?,?,?,?,?,?)""",
                     (club_id, uid, title, content, priority, pinned, expires))


def init_database(db_path=DEFAULT_DB, quiet=False):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    run_sql_file(conn, SCHEMA)
    run_sql_file(conn, SEED)
    create_accounts(conn)
    create_announcements(conn)
    conn.commit()

    if not quiet:
        print(f"[+] Database built at {db_path}\n")
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for t in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"    {t:<20} {n:>4} rows")
        print("\n    Logins: admin/admin123 · <roll_no>/<roll_no> · <email-user>/faculty123")
    conn.close()
    return db_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=DEFAULT_DB)
    args = ap.parse_args()
    init_database(args.path)
