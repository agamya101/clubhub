"""
ClubHub test suite — run with:  python -m pytest tests/ -q
Needs MySQL/MariaDB running (XAMPP). Builds a throwaway database `clubhub_test`.
Covers: schema constraints & triggers, RBAC (every tier), CRUD through the UI routes.
"""
import os
import sys

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "database"))

from init_db import init_database  # noqa: E402
from app import create_app  # noqa: E402
import db as dbmod  # noqa: E402

TEST_DB = "clubhub_test"
IntegrityError = Exception


class _Conn:
    """sqlite-like shim over the MySQL connection used by the schema tests."""
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, args=()):
        cur = self.raw.cursor(dictionary=True)
        cur.execute(sql.replace("?", "%s"), tuple(args))
        if cur.with_rows:
            rows = cur.fetchall()
            cur.close()
            self.raw.commit()  # end the read snapshot so later reads see the app's writes
            return _Rows(rows)
        self.raw.commit()
        cur.close()
        return _Rows([])


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        r = self.rows[0] if self.rows else None
        return _Row(r) if r is not None else None


class _Row(dict):
    def __getitem__(self, k):
        if isinstance(k, int):
            return list(self.values())[k]
        return dict.__getitem__(self, k)


@pytest.fixture()
def db_path():
    return init_database(TEST_DB, quiet=True)


@pytest.fixture()
def conn(db_path):
    raw = dbmod.connect(database=TEST_DB)
    yield _Conn(raw)
    raw.close()


@pytest.fixture()
def client(db_path):
    app = create_app({"TESTING": True, "DB_CONFIG": {"database": TEST_DB}, "SECRET_KEY": "t"})
    return app.test_client()


def login(client, u, p):
    client.post("/logout")
    return client.post("/login", data={"username": u, "password": p})


# ---------------------------------------------------------------- schema
def test_sixteen_tables(conn):
    names = {r["table_name"] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type='BASE TABLE'").rows}
    assert len(names) == 16
    assert {"Person", "Student", "Faculty", "Club", "Technical_Club", "Announcement"} <= names


def test_person_subtype_disjoint(conn):
    with pytest.raises(IntegrityError, match="already a Student"):
        conn.execute("INSERT INTO Faculty (faculty_id, department, designation) VALUES (1, 'X', 'Lecturer')")


def test_club_subtype_must_match_category(conn):
    with pytest.raises(IntegrityError, match="category = Technical"):
        conn.execute("INSERT INTO Technical_Club (club_id, tech_stack) VALUES (2, 'x')")  # club 2 is Cultural


def test_category_change_drops_subtype(conn):
    conn.execute("UPDATE Club SET category = 'Literary' WHERE club_id = 1")
    assert conn.execute("SELECT COUNT(*) FROM Technical_Club WHERE club_id = 1").fetchone()[0] == 0


def test_capacity_trigger(conn):
    conn.execute("INSERT INTO Event (club_id, title, event_type, event_date, venue, capacity) VALUES (1,'t','Meetup','2027-01-01 10:00','v',1)")
    eid = conn.execute("SELECT MAX(event_id) FROM Event").fetchone()[0]
    conn.execute("INSERT INTO Event_Registration (student_id, event_id) VALUES (1, ?)", (eid,))
    with pytest.raises(IntegrityError, match="full capacity"):
        conn.execute("INSERT INTO Event_Registration (student_id, event_id) VALUES (2, ?)", (eid,))
    with pytest.raises(IntegrityError, match="Capacity cannot be lower"):
        conn.execute("UPDATE Event SET capacity = 0 WHERE event_id = ?", (eid,))


def test_no_registration_for_completed_event(conn):
    with pytest.raises(IntegrityError, match="Upcoming"):
        conn.execute("INSERT INTO Event_Registration (student_id, event_id) VALUES (2, 3)")


def test_one_president(conn):
    with pytest.raises(IntegrityError, match="already has a President"):
        conn.execute("UPDATE Membership SET role='President' WHERE student_id = 6 AND club_id = 1")


def test_admin_account_has_no_person(conn):
    with pytest.raises(IntegrityError):
        conn.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES ('x','h','Admin',1)")
    with pytest.raises(IntegrityError, match="does not match"):
        conn.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES ('y','h','Faculty',1)")


def test_collegewide_announcement_admin_only(conn):
    fac = conn.execute("SELECT user_id FROM User_Account WHERE role='Faculty' LIMIT 1").fetchone()[0]
    with pytest.raises(IntegrityError, match="Only Admins"):
        conn.execute("INSERT INTO Announcement (club_id, posted_by, title, content) VALUES (NULL, ?, 't', 'c')", (fac,))


def test_cascade_delete_person(conn):
    conn.execute("DELETE FROM Person WHERE person_id = 1")
    assert conn.execute("SELECT COUNT(*) FROM Membership WHERE student_id = 1").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM User_Account WHERE person_id = 1").fetchone()[0] == 0


def test_views(conn):
    row = conn.execute("SELECT * FROM v_event_seats WHERE event_id = 1").fetchone()
    assert row["seats_left"] == row["capacity"] - row["registered"]
    assert conn.execute("SELECT president_name FROM v_club_summary WHERE club_id = 1").fetchone()[0] == "Aarav Mehta"


# ---------------------------------------------------------------- RBAC
def test_public_pages_open(client):
    for p in ("/", "/clubs", "/clubs/1", "/events", "/events/1", "/notices", "/login"):
        assert client.get(p).status_code == 200


def test_public_cannot_see_emails(client):
    html = client.get("/clubs/1").data.decode()
    assert "aarav.mehta@nsut.ac.in" not in html and "2025UCS1302" not in html


def test_protected_redirects_anonymous(client):
    for p in ("/me", "/manage/1", "/faculty/", "/admin/"):
        assert client.get(p).status_code == 302


def test_student_tiers(client):
    login(client, "2025UCS1302", "2025UCS1302")  # plain member
    assert client.get("/me").status_code == 200
    assert client.get("/manage/1").status_code == 403
    assert client.get("/admin/").status_code == 403
    login(client, "2023UCS1001", "2023UCS1001")  # president of club 1
    assert client.get("/manage/1").status_code == 200
    assert client.get("/manage/2").status_code == 403
    assert "2025UCS1302" in client.get("/clubs/1").data.decode()          # roll numbers visible to heads
    assert "priya.nair@nsut.ac.in" in client.get("/manage/1/members").data.decode()


def test_faculty_scope(client):
    login(client, "neelam.sinha", "faculty123")  # advises club 1 only
    assert client.get("/faculty/clubs/1").status_code == 200
    assert client.get("/faculty/clubs/2").status_code == 403
    assert client.post("/manage/1/events/new", data={}).status_code == 403
    assert client.post("/faculty/clubs/2/announcements/new", data={"title": "t", "content": "c", "priority": "Normal"}).status_code == 403


def test_admin_everything(client):
    login(client, "admin", "admin123")
    for p in ("/admin/", "/admin/students", "/admin/faculty", "/admin/accounts", "/admin/clubs", "/admin/events",
              "/admin/funding", "/admin/schema", "/admin/sql", "/manage/3", "/manage/3/members"):
        assert client.get(p).status_code == 200, p


def test_wrong_password(client):
    r = login(client, "admin", "nope")
    assert b"Wrong username" in r.data


# ---------------------------------------------------------------- CRUD through the UI
def test_student_register_and_cancel(client, conn):
    login(client, "2025UCS1302", "2025UCS1302")
    r = client.post("/events/5/register", follow_redirects=True)
    assert b"registered" in r.data
    assert conn.execute("SELECT COUNT(*) FROM Event_Registration WHERE student_id=8 AND event_id=5").fetchone()[0] == 1
    r = client.post("/events/5/register", follow_redirects=True)
    assert b"already registered" in r.data
    client.post("/events/5/cancel", follow_redirects=True)
    assert conn.execute("SELECT COUNT(*) FROM Event_Registration WHERE student_id=8 AND event_id=5").fetchone()[0] == 0


def test_student_join_leave(client, conn):
    login(client, "2025UCS1302", "2025UCS1302")
    client.post("/clubs/4/join", follow_redirects=True)
    assert conn.execute("SELECT role FROM Membership WHERE student_id=8 AND club_id=4").fetchone()[0] == "Member"
    client.post("/clubs/4/leave", follow_redirects=True)
    assert conn.execute("SELECT COUNT(*) FROM Membership WHERE student_id=8 AND club_id=4").fetchone()[0] == 0


def test_club_head_event_crud(client, conn):
    login(client, "2023UCS1001", "2023UCS1001")
    data = dict(title="Docker 101", event_type="Workshop", event_date="2026-12-10T17:00", venue="Lab", capacity="30", status="Upcoming")
    client.post("/manage/1/events/new", data=data, follow_redirects=True)
    eid = conn.execute("SELECT event_id FROM Event WHERE title='Docker 101'").fetchone()[0]
    client.post(f"/manage/1/events/{eid}/edit", data={**data, "venue": "Lab 999"}, follow_redirects=True)
    assert conn.execute("SELECT venue FROM Event WHERE event_id=?", (eid,)).fetchone()[0] == "Lab 999"
    client.post(f"/manage/1/events/{eid}/delete", follow_redirects=True)
    assert conn.execute("SELECT COUNT(*) FROM Event WHERE event_id=?", (eid,)).fetchone()[0] == 0


def test_club_head_cannot_touch_other_clubs_rows(client):
    login(client, "2023UCS1001", "2023UCS1001")
    assert client.get("/manage/1/events/4/edit").status_code == 404  # event 4 belongs to club 2


def test_admin_creates_student_with_account(client, conn):
    login(client, "admin", "admin123")
    client.post("/admin/students/new", data=dict(name="New Kid", email="new.kid@nsut.ac.in", roll_no="2026UCS0001",
                                                 branch="CSE", year="1", create_account="1"), follow_redirects=True)
    assert conn.execute("SELECT COUNT(*) FROM Student WHERE roll_no='2026UCS0001'").fetchone()[0] == 1
    assert login(client, "2026UCS0001", "2026UCS0001").status_code == 302
    assert client.get("/me").status_code == 200


def test_admin_creates_club_with_subtype(client, conn):
    login(client, "admin", "admin123")
    client.post("/admin/clubs/new", data=dict(name="Chess Club", category="Sports", sport="Chess", status="Active"), follow_redirects=True)
    cid = conn.execute("SELECT club_id FROM Club WHERE name='Chess Club'").fetchone()[0]
    assert conn.execute("SELECT sport FROM Sports_Club WHERE club_id=?", (cid,)).fetchone()[0] == "Chess"


def test_sql_console_is_read_only(client):
    login(client, "admin", "admin123")
    assert b"ByteForge" in client.post("/admin/sql", data={"sql": "SELECT name FROM Club"}).data
    assert b"only SELECT" in client.post("/admin/sql", data={"sql": "DELETE FROM Club"}).data
