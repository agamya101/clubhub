"""Public pages — no login needed. Only non-sensitive columns are exposed."""

from flask import Blueprint, abort, g, render_template, request

import constants as C
import queries as Q
from auth import can_view_private, is_student
from db import query

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    stats = query("""
        SELECT (SELECT COUNT(*) FROM Club WHERE status='Active')                                   AS clubs,
               (SELECT COUNT(*) FROM Student)                                                      AS students,
               (SELECT COUNT(*) FROM Event WHERE status='Upcoming' AND event_date >= NOW()) AS upcoming,
               (SELECT COUNT(*) FROM Event_Registration)                                           AS registrations""", one=True)
    return render_template(
        "public/home.html",
        stats=stats,
        alerts=Q.collegewide_alerts(),
        events=Q.events(upcoming_only=True, limit=6),
        clubs=Q.club_summaries(),
        notices=Q.announcements(limit=5),
    )


@bp.route("/clubs")
def clubs():
    category = request.args.get("category") or None
    if category and category not in C.CLUB_CATEGORIES:
        abort(404)
    return render_template("public/clubs.html", clubs=Q.club_summaries(category=category),
                           categories=C.CLUB_CATEGORIES, active=category)


@bp.route("/clubs/<int:club_id>")
def club(club_id):
    club = Q.club_detail(club_id)
    if not club:
        abort(404)
    private = can_view_private(club_id)
    if is_student():
        levels = ["Public", "Members"]
    else:
        levels = ["Public"]
    if private:
        levels = ["Public", "Members", "Private"]
    my_role = None
    if is_student():
        r = query("SELECT role FROM Membership WHERE student_id = ? AND club_id = ?",
                  (g.user["person_id"], club_id), one=True)
        my_role = r["role"] if r else None
    return render_template(
        "public/club.html", club=club, private=private, my_role=my_role,
        members=Q.club_members(club_id, private=private),
        upcoming=Q.events(club_id=club_id, upcoming_only=True),
        past=[e for e in Q.events(club_id=club_id) if e["status"] != "Upcoming"],
        notices=Q.announcements(club_id=club_id),
        docs=Q.documents(club_id, levels),
    )


@bp.route("/events")
def events():
    event_type = request.args.get("type") or None
    club_id = request.args.get("club", type=int)
    when = request.args.get("when", "upcoming")
    if event_type and event_type not in C.EVENT_TYPES:
        abort(404)
    if when == "past":
        rows = [e for e in Q.events(club_id=club_id, event_type=event_type) if e["status"] in ("Completed", "Cancelled")]
    else:
        rows = Q.events(club_id=club_id, event_type=event_type, upcoming_only=True)
    my_regs = set()
    if is_student():
        my_regs = {r["event_id"] for r in query(
            "SELECT event_id FROM Event_Registration WHERE student_id = ?", (g.user["person_id"],))}
    return render_template("public/events.html", events=rows, types=C.EVENT_TYPES,
                           clubs=query("SELECT club_id, name FROM Club WHERE status='Active' ORDER BY name"),
                           active_type=event_type, active_club=club_id, when=when, my_regs=my_regs)


@bp.route("/events/<int:event_id>")
def event(event_id):
    ev = Q.event_detail(event_id)
    if not ev:
        abort(404)
    registered = False
    if is_student():
        registered = bool(query("SELECT 1 FROM Event_Registration WHERE student_id = ? AND event_id = ?",
                                (g.user["person_id"], event_id), one=True))
    registrants = Q.event_registrants(event_id) if can_view_private(ev["club_id"]) else None
    return render_template("public/event.html", ev=ev, registered=registered, registrants=registrants)


@bp.route("/notices")
def notices():
    return render_template("public/notices.html", notices=Q.announcements())
