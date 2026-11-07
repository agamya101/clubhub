"""
ClubHub database initialiser for MySQL / MariaDB (XAMPP).

    1. Start Apache + MySQL in the XAMPP control panel.
    2. python database/init_db.py              # (re)builds database `clubhub`
       python database/init_db.py --name x     # build under another name (tests)

Runs schema.sql (drops & recreates every table), seed.sql, then creates
login accounts with hashed passwords and the seed announcements.

Connection settings: environment variables CLUBHUB_DB_HOST / PORT / USER /
PASSWORD (XAMPP default is root with an empty password).

Seed logins
    admin        / admin123
    <roll_no>    / <roll_no>       e.g. 2023UCS1001 / 2023UCS1001
    <email user> / faculty123      e.g. neelam.sinha / faculty123
"""

import argparse
import os
import re
import sys

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
from db import CONFIG, connect  # noqa: E402

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


def split_statements(sql_text):
    """Split a .sql file into statements, honouring DELIMITER lines (for triggers)."""
    statements, buf, delim = [], [], ";"
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") and not buf:
            continue
        m = re.match(r"^DELIMITER\s+(\S+)\s*$", stripped, re.I)
        if m:
            delim = m.group(1)
            continue
        buf.append(line)
        if stripped.endswith(delim):
            stmt = "\n".join(buf).strip()
            stmt = stmt[: -len(delim)].strip()
            if stmt and not all(l.strip().startswith("--") or not l.strip() for l in stmt.splitlines()):
                statements.append(stmt)
            buf = []
    return statements


def run_sql_file(conn, path, db_name):
    cur = conn.cursor()
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().replace("clubhub", db_name) if db_name != "clubhub" else f.read()
    for stmt in split_statements(text):
        cur.execute(stmt)
    conn.commit()
    cur.close()


def create_accounts(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (%s,%s,%s,NULL)",
                ("admin", generate_password_hash("admin123"), "Admin"))
    cur.execute("SELECT student_id, roll_no FROM Student")
    for sid, roll in cur.fetchall():
        cur.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (%s,%s,%s,%s)",
                    (roll, generate_password_hash(roll), "Student", sid))
    cur.execute("SELECT f.faculty_id, p.email FROM Faculty f JOIN Person p ON p.person_id = f.faculty_id")
    for fid, email in cur.fetchall():
        cur.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (%s,%s,%s,%s)",
                    (email.split("@")[0], generate_password_hash("faculty123"), "Faculty", fid))
    conn.commit()
    cur.close()


def create_announcements(conn):
    cur = conn.cursor()
    for club_id, username, title, content, priority, pinned, expires in ANNOUNCEMENTS:
        cur.execute("SELECT user_id FROM User_Account WHERE username = %s", (username,))
        uid = cur.fetchone()[0]
        cur.execute("""INSERT INTO Announcement (club_id, posted_by, title, content, priority, is_pinned, expires_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""", (club_id, uid, title, content, priority, pinned, expires))
    conn.commit()
    cur.close()


def init_database(db_name="clubhub", quiet=False):
    # connect without a database first so schema.sql can CREATE DATABASE
    conn = connect(database=None)
    conn.autocommit = True
    run_sql_file(conn, SCHEMA, db_name)
    conn.autocommit = False
    cur = conn.cursor(); cur.execute(f"USE `{db_name}`"); cur.close()
    run_sql_file(conn, SEED, db_name)
    create_accounts(conn)
    create_announcements(conn)

    if not quiet:
        print(f"[+] Database `{db_name}` built on {CONFIG['host']}:{CONFIG['port']} as {CONFIG['user']}\n")
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type='BASE TABLE' ORDER BY table_name", (db_name,))
        for (t,) in cur.fetchall():
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            print(f"    {t:<20} {cur.fetchone()[0]:>4} rows")
        print("\n    Logins: admin/admin123 · <roll_no>/<roll_no> · <email-user>/faculty123")
        cur.close()
    conn.close()
    return db_name


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="clubhub")
    args = ap.parse_args()
    try:
        init_database(args.name)
    except Exception as e:  # most common: XAMPP MySQL not started
        print(f"[!] Could not build the database: {e}")
        print("    Is MySQL running in the XAMPP control panel? Host/user/password come from CLUBHUB_DB_* env vars.")
        sys.exit(1)
