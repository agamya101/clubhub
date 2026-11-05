"""
Admin console: /admin/…  — every table, every row.
Also a read-only SQL console and schema browser for demos.
"""

import re
import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

import constants as C
import crud
import queries as Q
from auth import roles_required
from db import execute, get_db, query

bp = Blueprint("admin", __name__, url_prefix="/admin")

ADMIN_ONLY = roles_required("Admin")


# ------------------------------------------------------------------ dashboard
@bp.route("/")
@ADMIN_ONLY
def dashboard():
    counts = {t: query(f"SELECT COUNT(*) AS n FROM {t}", one=True)["n"] for t in (
        "Person", "Student", "Faculty", "User_Account", "Club", "Club_Advisor", "Membership", "Event",
        "Event_Registration", "Club_Funding", "Club_Asset", "Club_Document", "Announcement")}
    funding_by_category = query("""
        SELECT c.category, COALESCE(SUM(f.amount),0) AS total
        FROM Club c LEFT JOIN Club_Funding f ON f.club_id = c.club_id
        GROUP BY c.category ORDER BY total DESC""")
    members_by_club = query("SELECT name, member_count FROM v_club_summary ORDER BY member_count DESC")
    events_by_type = query("SELECT event_type, COUNT(*) AS n FROM Event GROUP BY event_type ORDER BY n DESC")
    recent_regs = query("""
        SELECT p.name, e.title, r.registered_at FROM Event_Registration r
        JOIN Person p ON p.person_id = r.student_id JOIN Event e ON e.event_id = r.event_id
        ORDER BY r.registered_at DESC LIMIT 6""")
    return render_template("admin/dashboard.html", counts=counts, funding_by_category=funding_by_category,
                           members_by_club=members_by_club, events_by_type=events_by_type, recent_regs=recent_regs,
                           upcoming=Q.events(upcoming_only=True, limit=5))


# ------------------------------------------------------------------ students
@bp.route("/students")
@ADMIN_ONLY
def students():
    q = request.args.get("q", "").strip()
    like = f"%{q}%"
    rows = query("""
        SELECT s.student_id, p.name, p.email, p.phone, s.roll_no, s.branch, s.year,
               u.username, u.is_active,
               (SELECT COUNT(*) FROM Membership m WHERE m.student_id = s.student_id) AS clubs
        FROM Student s JOIN Person p ON p.person_id = s.student_id
        LEFT JOIN User_Account u ON u.person_id = s.student_id
        WHERE ? = '' OR p.name LIKE ? OR s.roll_no LIKE ? OR p.email LIKE ? OR s.branch LIKE ?
        ORDER BY s.roll_no""", (q, like, like, like, like))
    return render_template("admin/students.html", rows=rows, q=q)


def _person_form(form, errors):
    name = form.get("name", "").strip()
    email = form.get("email", "").strip().lower()
    phone = form.get("phone", "").strip() or None
    if not name:
        errors.append("Name is required.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("Enter a valid email.")
    if phone and not (10 <= len(phone) <= 15):
        errors.append("Phone must be 10–15 characters.")
    return name, email, phone


@bp.route("/students/new", methods=["GET", "POST"])
@bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@ADMIN_ONLY
def student_form(student_id=None):
    row = None
    if student_id:
        row = query("""SELECT s.*, p.name, p.email, p.phone, u.username FROM Student s
                       JOIN Person p ON p.person_id = s.student_id LEFT JOIN User_Account u ON u.person_id = s.student_id
                       WHERE s.student_id = ?""", (student_id,), one=True)
        if not row:
            abort(404)
    errors = []
    if request.method == "POST":
        f = request.form
        name, email, phone = _person_form(f, errors)
        roll = f.get("roll_no", "").strip().upper()
        branch, year = f.get("branch"), f.get("year", type=int)
        if not roll:
            errors.append("Roll number is required.")
        if branch not in C.BRANCHES:
            errors.append("Pick a valid branch.")
        if year not in (1, 2, 3, 4):
            errors.append("Year must be 1–4.")
        if not errors:
            db = get_db()
            try:
                with db:  # one transaction across Person + Student (+ account)
                    if student_id:
                        db.execute("UPDATE Person SET name=?, email=?, phone=? WHERE person_id=?", (name, email, phone, student_id))
                        db.execute("UPDATE Student SET roll_no=?, branch=?, year=? WHERE student_id=?", (roll, branch, year, student_id))
                    else:
                        cur = db.execute("INSERT INTO Person (name, email, phone) VALUES (?,?,?)", (name, email, phone))
                        pid = cur.lastrowid
                        db.execute("INSERT INTO Student (student_id, roll_no, branch, year) VALUES (?,?,?,?)", (pid, roll, branch, year))
                        if f.get("create_account"):
                            db.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?,?,?,?)",
                                       (roll, generate_password_hash(roll), "Student", pid))
                flash("Student saved.", "success")
                return redirect(url_for("admin.students"))
            except sqlite3.IntegrityError as e:
                errors.append(crud.friendly_integrity_error(e))
        row = {**(row or {}), **f}
    return render_template("admin/student_form.html", row=row, errors=errors, C=C)


@bp.route("/students/<int:student_id>/delete", methods=["POST"])
@ADMIN_ONLY
def student_delete(student_id):
    execute("DELETE FROM Person WHERE person_id = ?", (student_id,))  # cascades Student, Membership, Registrations, Account
    flash("Student and all related records deleted.", "info")
    return redirect(url_for("admin.students"))


# ------------------------------------------------------------------ faculty
@bp.route("/faculty")
@ADMIN_ONLY
def faculty():
    rows = query("""
        SELECT f.faculty_id, p.name, p.email, p.phone, f.department, f.designation, u.username, u.is_active,
               (SELECT GROUP_CONCAT(c.name, ', ') FROM Club_Advisor ca JOIN Club c ON c.club_id = ca.club_id
                 WHERE ca.faculty_id = f.faculty_id) AS clubs
        FROM Faculty f JOIN Person p ON p.person_id = f.faculty_id
        LEFT JOIN User_Account u ON u.person_id = f.faculty_id ORDER BY p.name""")
    return render_template("admin/faculty.html", rows=rows)


@bp.route("/faculty/new", methods=["GET", "POST"])
@bp.route("/faculty/<int:faculty_id>/edit", methods=["GET", "POST"])
@ADMIN_ONLY
def faculty_form(faculty_id=None):
    row = None
    if faculty_id:
        row = query("""SELECT f.*, p.name, p.email, p.phone, u.username FROM Faculty f
                       JOIN Person p ON p.person_id = f.faculty_id LEFT JOIN User_Account u ON u.person_id = f.faculty_id
                       WHERE f.faculty_id = ?""", (faculty_id,), one=True)
        if not row:
            abort(404)
    errors = []
    if request.method == "POST":
        f = request.form
        name, email, phone = _person_form(f, errors)
        dept, desig = f.get("department", "").strip(), f.get("designation")
        if not dept:
            errors.append("Department is required.")
        if desig not in C.DESIGNATIONS:
            errors.append("Pick a valid designation.")
        if not errors:
            db = get_db()
            try:
                with db:
                    if faculty_id:
                        db.execute("UPDATE Person SET name=?, email=?, phone=? WHERE person_id=?", (name, email, phone, faculty_id))
                        db.execute("UPDATE Faculty SET department=?, designation=? WHERE faculty_id=?", (dept, desig, faculty_id))
                    else:
                        pid = db.execute("INSERT INTO Person (name, email, phone) VALUES (?,?,?)", (name, email, phone)).lastrowid
                        db.execute("INSERT INTO Faculty (faculty_id, department, designation) VALUES (?,?,?)", (pid, dept, desig))
                        if f.get("create_account"):
                            uname = email.split("@")[0]
                            db.execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?,?,?,?)",
                                       (uname, generate_password_hash("faculty123"), "Faculty", pid))
                flash("Faculty saved.", "success")
                return redirect(url_for("admin.faculty"))
            except sqlite3.IntegrityError as e:
                errors.append(crud.friendly_integrity_error(e))
        row = {**(row or {}), **f}
    return render_template("admin/faculty_form.html", row=row, errors=errors, C=C)


@bp.route("/faculty/<int:faculty_id>/delete", methods=["POST"])
@ADMIN_ONLY
def faculty_delete(faculty_id):
    execute("DELETE FROM Person WHERE person_id = ?", (faculty_id,))
    flash("Faculty member deleted; their clubs remain.", "info")
    return redirect(url_for("admin.faculty"))


# ------------------------------------------------------------------ accounts
@bp.route("/accounts")
@ADMIN_ONLY
def accounts():
    rows = query("""SELECT u.*, p.name FROM User_Account u LEFT JOIN Person p ON p.person_id = u.person_id
                    ORDER BY u.role, u.username""")
    people_without = query("""
        SELECT p.person_id, p.name, CASE WHEN s.student_id IS NULL THEN 'Faculty' ELSE 'Student' END AS role,
               COALESCE(s.roll_no, p.email) AS handle
        FROM Person p LEFT JOIN Student s ON s.student_id = p.person_id
        WHERE NOT EXISTS (SELECT 1 FROM User_Account u WHERE u.person_id = p.person_id) ORDER BY p.name""")
    return render_template("admin/accounts.html", rows=rows, people_without=people_without)


@bp.route("/accounts/new", methods=["POST"])
@ADMIN_ONLY
def account_new():
    f = request.form
    username, password = f.get("username", "").strip(), f.get("password", "")
    person_id = f.get("person_id", type=int)
    if len(username) < 3 or len(password) < 6:
        flash("Username needs 3+ characters and password 6+.", "error")
        return redirect(url_for("admin.accounts"))
    if person_id:
        role = "Student" if query("SELECT 1 FROM Student WHERE student_id = ?", (person_id,), one=True) else "Faculty"
    else:
        role, person_id = "Admin", None
    try:
        execute("INSERT INTO User_Account (username, password_hash, role, person_id) VALUES (?,?,?,?)",
                (username, generate_password_hash(password), role, person_id))
        flash(f"{role} account created.", "success")
    except sqlite3.IntegrityError as e:
        flash(crud.friendly_integrity_error(e), "error")
    return redirect(url_for("admin.accounts"))


@bp.route("/accounts/<int:user_id>/password", methods=["POST"])
@ADMIN_ONLY
def account_password(user_id):
    pw = request.form.get("password", "")
    if len(pw) < 6:
        flash("Password needs 6+ characters.", "error")
    else:
        execute("UPDATE User_Account SET password_hash = ? WHERE user_id = ?", (generate_password_hash(pw), user_id))
        flash("Password reset.", "success")
    return redirect(url_for("admin.accounts"))


@bp.route("/accounts/<int:user_id>/toggle", methods=["POST"])
@ADMIN_ONLY
def account_toggle(user_id):
    execute("UPDATE User_Account SET is_active = 1 - is_active WHERE user_id = ?", (user_id,))
    return redirect(url_for("admin.accounts"))


@bp.route("/accounts/<int:user_id>/delete", methods=["POST"])
@ADMIN_ONLY
def account_delete(user_id):
    if query("SELECT COUNT(*) AS n FROM User_Account WHERE role='Admin'", one=True)["n"] <= 1 and \
            query("SELECT role FROM User_Account WHERE user_id=?", (user_id,), one=True)["role"] == "Admin":
        flash("Cannot delete the last admin account.", "error")
    else:
        execute("DELETE FROM User_Account WHERE user_id = ?", (user_id,))
        flash("Account deleted.", "info")
    return redirect(url_for("admin.accounts"))


# ------------------------------------------------------------------ clubs
@bp.route("/clubs")
@ADMIN_ONLY
def clubs():
    return render_template("admin/clubs.html", rows=Q.club_summaries(active_only=False))


@bp.route("/clubs/new", methods=["GET", "POST"])
@ADMIN_ONLY
def club_new():
    errors = []
    if request.method == "POST":
        f = request.form
        name, category = f.get("name", "").strip(), f.get("category")
        if not name:
            errors.append("Name is required.")
        if category not in C.CLUB_CATEGORIES:
            errors.append("Pick a category.")
        if not errors:
            db = get_db()
            try:
                with db:
                    cid = db.execute("""INSERT INTO Club (name, category, tagline, description, room_no, founded_year, contact_email, status)
                                        VALUES (?,?,?,?,?,?,?,?)""",
                                     (name, category, f.get("tagline") or None, f.get("description") or None,
                                      f.get("room_no") or None, f.get("founded_year", type=int),
                                      f.get("contact_email") or None, f.get("status", "Active"))).lastrowid
                    if category == "Technical":
                        db.execute("INSERT INTO Technical_Club (club_id, github_url, tech_stack) VALUES (?,?,?)",
                                   (cid, f.get("github_url") or None, f.get("tech_stack") or "—"))
                    elif category == "Cultural":
                        db.execute("INSERT INTO Cultural_Club (club_id, art_form) VALUES (?,?)", (cid, f.get("art_form") or "Dance"))
                    elif category == "Sports":
                        db.execute("INSERT INTO Sports_Club (club_id, sport, coach_name) VALUES (?,?,?)",
                                   (cid, f.get("sport") or "—", f.get("coach_name") or None))
                flash("Club created. Add a President under Members.", "success")
                return redirect(url_for("manage.overview", club_id=cid))
            except sqlite3.IntegrityError as e:
                errors.append(crud.friendly_integrity_error(e))
    return render_template("manage/profile.html", club=None, errors=errors, C=C, values=request.form)


@bp.route("/clubs/<int:club_id>/delete", methods=["POST"])
@ADMIN_ONLY
def club_delete(club_id):
    execute("DELETE FROM Club WHERE club_id = ?", (club_id,))
    flash("Club and everything under it deleted.", "info")
    return redirect(url_for("admin.clubs"))


# ------------------------------------------------------------------ advisors (Club_Advisor)
@bp.route("/advisors")
@ADMIN_ONLY
def advisors():
    rows = query("""SELECT ca.*, c.name AS club_name, p.name AS faculty_name, f.department
                    FROM Club_Advisor ca JOIN Club c ON c.club_id = ca.club_id
                    JOIN Faculty f ON f.faculty_id = ca.faculty_id JOIN Person p ON p.person_id = f.faculty_id
                    ORDER BY c.name, p.name""")
    return render_template("admin/advisors.html", rows=rows,
                           clubs=query("SELECT club_id, name FROM Club ORDER BY name"),
                           faculty=query("SELECT f.faculty_id, p.name FROM Faculty f JOIN Person p ON p.person_id=f.faculty_id ORDER BY p.name"))


@bp.route("/advisors/add", methods=["POST"])
@ADMIN_ONLY
def advisor_add():
    try:
        execute("INSERT INTO Club_Advisor (club_id, faculty_id) VALUES (?,?)",
                (request.form.get("club_id", type=int), request.form.get("faculty_id", type=int)))
        flash("Advisor assigned.", "success")
    except sqlite3.IntegrityError as e:
        flash(crud.friendly_integrity_error(e), "error")
    return redirect(url_for("admin.advisors"))


@bp.route("/advisors/<int:club_id>/<int:faculty_id>/remove", methods=["POST"])
@ADMIN_ONLY
def advisor_remove(club_id, faculty_id):
    execute("DELETE FROM Club_Advisor WHERE club_id = ? AND faculty_id = ?", (club_id, faculty_id))
    flash("Advisor unassigned.", "info")
    return redirect(url_for("admin.advisors"))


# ------------------------------------------------------------------ memberships (global)
@bp.route("/memberships")
@ADMIN_ONLY
def memberships():
    club_id = request.args.get("club", type=int)
    rows = query("""SELECT m.*, p.name, s.roll_no, c.name AS club_name
                    FROM Membership m JOIN Student s ON s.student_id = m.student_id JOIN Person p ON p.person_id = s.student_id
                    JOIN Club c ON c.club_id = m.club_id
                    WHERE ? IS NULL OR m.club_id = ? ORDER BY c.name, m.role, p.name""", (club_id, club_id))
    return render_template("admin/memberships.html", rows=rows, roles=C.MEMBERSHIP_ROLES, active_club=club_id,
                           clubs=query("SELECT club_id, name FROM Club ORDER BY name"))


@bp.route("/memberships/add", methods=["POST"])
@ADMIN_ONLY
def membership_add():
    f = request.form
    s = query("SELECT student_id FROM Student WHERE roll_no = ?", (f.get("roll_no", "").strip().upper(),), one=True)
    if not s:
        flash("No student with that roll number.", "error")
    else:
        try:
            execute("INSERT INTO Membership (student_id, club_id, role) VALUES (?,?,?)",
                    (s["student_id"], f.get("club_id", type=int), f.get("role", "Member")))
            flash("Membership added.", "success")
        except sqlite3.IntegrityError as e:
            flash(crud.friendly_integrity_error(e), "error")
    return redirect(url_for("admin.memberships"))


# ------------------------------------------------------------------ registrations (global)
@bp.route("/registrations")
@ADMIN_ONLY
def registrations():
    event_id = request.args.get("event", type=int)
    rows = query("""SELECT r.*, p.name, s.roll_no, e.title, e.event_date, c.name AS club_name
                    FROM Event_Registration r JOIN Student s ON s.student_id = r.student_id JOIN Person p ON p.person_id = s.student_id
                    JOIN Event e ON e.event_id = r.event_id JOIN Club c ON c.club_id = e.club_id
                    WHERE ? IS NULL OR r.event_id = ? ORDER BY r.registered_at DESC""", (event_id, event_id))
    return render_template("admin/registrations.html", rows=rows, active_event=event_id,
                           events=query("SELECT event_id, title FROM Event ORDER BY event_date DESC"))


@bp.route("/registrations/add", methods=["POST"])
@ADMIN_ONLY
def registration_add():
    f = request.form
    s = query("SELECT student_id FROM Student WHERE roll_no = ?", (f.get("roll_no", "").strip().upper(),), one=True)
    if not s:
        flash("No student with that roll number.", "error")
    else:
        try:
            execute("INSERT INTO Event_Registration (student_id, event_id) VALUES (?,?)", (s["student_id"], f.get("event_id", type=int)))
            flash("Registration added.", "success")
        except sqlite3.IntegrityError as e:
            flash(crud.friendly_integrity_error(e), "error")
    return redirect(url_for("admin.registrations"))


@bp.route("/registrations/<int:student_id>/<int:event_id>/remove", methods=["POST"])
@ADMIN_ONLY
def registration_remove(student_id, event_id):
    execute("DELETE FROM Event_Registration WHERE student_id = ? AND event_id = ?", (student_id, event_id))
    flash("Registration removed.", "info")
    return redirect(url_for("admin.registrations"))


# ------------------------------------------------------------------ generic club-scoped resources, global view
@bp.route("/<resource>")
@ADMIN_ONLY
def resource_list(resource):
    if resource not in crud.RESOURCES:
        abort(404)
    club_id = request.args.get("club", type=int)
    rows = crud.list_rows(resource, club_id=club_id)
    if resource == "announcements" and club_id is None:
        rows = crud.list_rows(resource)
    return render_template("manage/resource_list.html", club=None, resource=resource, spec=crud.spec(resource),
                           rows=rows, scope="admin", active_club=club_id,
                           clubs=query("SELECT club_id, name FROM Club ORDER BY name"))


@bp.route("/<resource>/new", methods=["GET", "POST"])
@bp.route("/<resource>/<int:pk>/edit", methods=["GET", "POST"])
@ADMIN_ONLY
def resource_form(resource, pk=None):
    if resource not in crud.RESOURCES:
        abort(404)
    row = crud.get_row(resource, pk) if pk else None
    if pk and not row:
        abort(404)
    errors = []
    clubs = query("SELECT club_id, name FROM Club ORDER BY name")
    if request.method == "POST":
        values, errors = crud.validate(resource, request.form)
        club_id = request.form.get("club_id", type=int)   # may be None for college-wide announcements
        if resource != "announcements" and not club_id:
            errors.append("Pick a club.")
        if not errors:
            if pk:
                err = crud.update(resource, pk, values, club_id=club_id)
            else:
                _, err = crud.insert(resource, values, club_id)
            if err:
                errors.append(err)
            else:
                flash("Saved.", "success")
                return redirect(url_for("admin.resource_list", resource=resource))
        row = {**(row or {}), **request.form}
    return render_template("manage/resource_form.html", club=None, resource=resource, spec=crud.spec(resource),
                           values=row or {}, errors=errors, mode="edit" if pk else "new", pk=pk, scope="admin", clubs=clubs)


@bp.route("/<resource>/<int:pk>/delete", methods=["POST"])
@ADMIN_ONLY
def resource_delete(resource, pk):
    if resource not in crud.RESOURCES:
        abort(404)
    crud.delete(resource, pk)
    flash("Deleted.", "info")
    return redirect(url_for("admin.resource_list", resource=resource))


# ------------------------------------------------------------------ schema browser + SQL console
@bp.route("/schema")
@ADMIN_ONLY
def schema():
    tables = []
    for t in query("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        cols = query(f"PRAGMA table_info({t['name']})")
        fks = query(f"PRAGMA foreign_key_list({t['name']})")
        n = query(f"SELECT COUNT(*) AS n FROM {t['name']}", one=True)["n"]
        tables.append(dict(name=t["name"], sql=t["sql"], cols=cols, fks=fks, rows=n))
    triggers = query("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' ORDER BY tbl_name, name")
    views = query("SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name")
    indexes = query("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name")
    return render_template("admin/schema.html", tables=tables, triggers=triggers, views=views, indexes=indexes)


SAMPLE_QUERIES = {
    "Members per club (JOIN + GROUP BY)":
        "SELECT c.name, COUNT(m.student_id) AS members\nFROM Club c LEFT JOIN Membership m ON m.club_id = c.club_id\nGROUP BY c.club_id ORDER BY members DESC;",
    "Students in 2+ clubs (HAVING)":
        "SELECT p.name, s.roll_no, COUNT(*) AS clubs\nFROM Membership m JOIN Student s ON s.student_id = m.student_id\nJOIN Person p ON p.person_id = s.student_id\nGROUP BY s.student_id HAVING COUNT(*) >= 2;",
    "Seats left per upcoming event (VIEW)":
        "SELECT title, club_name, event_date, registered, capacity, seats_left\nFROM v_event_seats WHERE status = 'Upcoming' ORDER BY event_date;",
    "Funding by club and source (aggregate)":
        "SELECT c.name, f.source_type, SUM(f.amount) AS total\nFROM Club_Funding f JOIN Club c ON c.club_id = f.club_id\nGROUP BY c.club_id, f.source_type ORDER BY c.name, total DESC;",
    "Generalisation: Person with its subtype":
        "SELECT p.person_id, p.name,\n  CASE WHEN s.student_id IS NOT NULL THEN 'Student' ELSE 'Faculty' END AS kind,\n  COALESCE(s.roll_no, f.department) AS detail\nFROM Person p LEFT JOIN Student s ON s.student_id = p.person_id\nLEFT JOIN Faculty f ON f.faculty_id = p.person_id;",
    "Specialisation: clubs with subtype attributes":
        "SELECT c.name, c.category, t.tech_stack, cu.art_form, sp.sport\nFROM Club c LEFT JOIN Technical_Club t ON t.club_id = c.club_id\nLEFT JOIN Cultural_Club cu ON cu.club_id = c.club_id\nLEFT JOIN Sports_Club sp ON sp.club_id = c.club_id;",
    "Events a student has NOT registered for (NOT EXISTS)":
        "SELECT e.title FROM Event e\nWHERE e.status = 'Upcoming' AND NOT EXISTS (\n  SELECT 1 FROM Event_Registration r WHERE r.event_id = e.event_id AND r.student_id = 1);",
    "Who heads each club (derived role)":
        "SELECT c.name AS club, p.name AS head, m.role\nFROM Membership m JOIN Club c ON c.club_id = m.club_id JOIN Person p ON p.person_id = m.student_id\nWHERE m.role IN ('President','Vice President') ORDER BY c.name, m.role;",
}


@bp.route("/sql", methods=["GET", "POST"])
@ADMIN_ONLY
def sql_console():
    sql, columns, rows, error = request.form.get("sql", "") if request.method == "POST" else "", [], [], None
    if request.method == "POST":
        stripped = sql.strip().rstrip(";").strip()
        if not re.match(r"^(SELECT|WITH|EXPLAIN|PRAGMA)\b", stripped, re.I):
            error = "Read-only console: only SELECT / WITH / EXPLAIN / PRAGMA statements are allowed."
        elif ";" in stripped:
            error = "One statement at a time."
        else:
            try:
                cur = get_db().execute(stripped)
                columns = [d[0] for d in cur.description] if cur.description else []
                rows = cur.fetchmany(200)
            except sqlite3.Error as e:
                error = str(e)
    return render_template("admin/sql.html", sql=sql, columns=columns, rows=rows, error=error, samples=SAMPLE_QUERIES)
