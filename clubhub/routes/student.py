"""Student actions: dashboard, event registration, joining clubs."""


from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import queries as Q
from auth import roles_required
from crud import friendly_integrity_error
from db import execute, query, IntegrityError

bp = Blueprint("student", __name__)


@bp.route("/me")
@roles_required("Student")
def dashboard():
    sid = g.user["person_id"]
    me = query("""SELECT p.name, p.email, p.phone, s.roll_no, s.branch, s.year
                  FROM Student s JOIN Person p ON p.person_id = s.student_id WHERE s.student_id = ?""",
               (sid,), one=True)
    regs = Q.student_registrations(sid)
    clubs = Q.student_clubs(sid)
    club_ids = [c["club_id"] for c in clubs]
    notices = []
    if club_ids:
        marks = ",".join("?" for _ in club_ids)
        notices = query(f"""
            SELECT n.*, c.name AS club_name FROM Announcement n LEFT JOIN Club c ON c.club_id = n.club_id
            WHERE (n.club_id IN ({marks}) OR n.club_id IS NULL)
              AND (n.expires_at IS NULL OR n.expires_at >= CURDATE())
            ORDER BY n.priority = 'Alert' DESC, n.is_pinned DESC, n.posted_at DESC LIMIT 8""", tuple(club_ids))
    return render_template("student/dashboard.html", me=me, clubs=clubs,
                           upcoming=[r for r in regs if r["status"] == "Upcoming"],
                           past=[r for r in regs if r["status"] != "Upcoming"],
                           notices=notices,
                           suggestions=Q.events(upcoming_only=True, limit=4))


@bp.route("/events/<int:event_id>/register", methods=["POST"])
@roles_required("Student")
def register(event_id):
    ev = Q.event_detail(event_id)
    if not ev:
        abort(404)
    if ev["registration_deadline"] and str(ev["registration_deadline"]) < str(query("SELECT CURDATE() AS d", one=True)["d"]):
        flash("Registration for this event has closed.", "error")
        return redirect(url_for("public.event", event_id=event_id))
    try:
        execute("INSERT INTO Event_Registration (student_id, event_id) VALUES (?, ?)", (g.user["person_id"], event_id))
        flash(f"You're registered for {ev['title']}.", "success")
    except IntegrityError as e:
        msg = friendly_integrity_error(e)
        if "duplicate" in msg:
            msg = "You are already registered for this event."
        flash(msg, "error")
    return redirect(request.referrer or url_for("public.event", event_id=event_id))


@bp.route("/events/<int:event_id>/cancel", methods=["POST"])
@roles_required("Student")
def cancel(event_id):
    cur = execute("DELETE FROM Event_Registration WHERE student_id = ? AND event_id = ?", (g.user["person_id"], event_id))
    flash("Registration cancelled." if cur.rowcount else "You were not registered.", "info")
    return redirect(request.referrer or url_for("public.event", event_id=event_id))


@bp.route("/clubs/<int:club_id>/join", methods=["POST"])
@roles_required("Student")
def join(club_id):
    club = query("SELECT name, status FROM Club WHERE club_id = ?", (club_id,), one=True)
    if not club:
        abort(404)
    if club["status"] != "Active":
        flash("This club is not accepting members right now.", "error")
        return redirect(url_for("public.club", club_id=club_id))
    try:
        execute("INSERT INTO Membership (student_id, club_id, role) VALUES (?, ?, 'Member')", (g.user["person_id"], club_id))
        flash(f"Welcome to {club['name']}.", "success")
    except IntegrityError:
        flash("You are already a member.", "info")
    return redirect(url_for("public.club", club_id=club_id))


@bp.route("/clubs/<int:club_id>/leave", methods=["POST"])
@roles_required("Student")
def leave(club_id):
    row = query("SELECT role FROM Membership WHERE student_id = ? AND club_id = ?", (g.user["person_id"], club_id), one=True)
    if row and row["role"] == "President":
        flash("A President cannot leave; hand over the role first.", "error")
        return redirect(url_for("public.club", club_id=club_id))
    execute("DELETE FROM Membership WHERE student_id = ? AND club_id = ?", (g.user["person_id"], club_id))
    flash("You have left the club.", "info")
    return redirect(url_for("public.club", club_id=club_id))
