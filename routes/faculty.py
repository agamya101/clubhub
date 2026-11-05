"""
Faculty advisor panel: /faculty/…
Read-everything for the clubs in Club_Advisor for this faculty member,
plus the ability to post announcements / alerts to those clubs.
"""

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import crud
import queries as Q
from auth import roles_required
from db import execute, query

bp = Blueprint("faculty", __name__, url_prefix="/faculty")


@bp.context_processor
def _advised_clubs_for_rail():
    ids = g.get("advised_clubs", [])
    if not ids:
        return dict(advised=[])
    marks = ",".join("?" for _ in ids)
    return dict(advised=query(f"SELECT club_id, name FROM Club WHERE club_id IN ({marks}) ORDER BY name", tuple(ids)))


def _advised_or_403(club_id):
    if club_id not in g.advised_clubs:
        abort(403)
    club = Q.club_detail(club_id)
    if not club:
        abort(404)
    return club


def _flags(club_ids):
    """Practical things an advisor should look at. Each flag: (level, club_id, club_name, text, link)."""
    if not club_ids:
        return []
    marks = ",".join("?" for _ in club_ids)
    flags = []
    # Upcoming events within 14 days that are under 30% booked.
    for e in query(f"""SELECT * FROM v_event_seats WHERE club_id IN ({marks}) AND status = 'Upcoming'
                       AND event_date BETWEEN datetime('now') AND datetime('now', '+14 days')
                       AND registered * 1.0 / capacity < 0.30""", tuple(club_ids)):
        flags.append(("warn", e["club_id"], e["club_name"],
                      f"“{e['title']}” is in {_days(e['event_date'])} with only {e['registered']}/{e['capacity']} seats taken.",
                      url_for("public.event", event_id=e["event_id"])))
    # Full events.
    for e in query(f"SELECT * FROM v_event_seats WHERE club_id IN ({marks}) AND status='Upcoming' AND seats_left <= 0", tuple(club_ids)):
        flags.append(("info", e["club_id"], e["club_name"], f"“{e['title']}” is fully booked ({e['capacity']} seats).",
                      url_for("public.event", event_id=e["event_id"])))
    # Assets needing repair.
    for a in query(f"""SELECT a.*, c.name AS club_name FROM Club_Asset a JOIN Club c ON c.club_id = a.club_id
                       WHERE a.club_id IN ({marks}) AND a.condition = 'Needs Repair'""", tuple(club_ids)):
        flags.append(("warn", a["club_id"], a["club_name"], f"{a['quantity']} × {a['name']} marked “Needs Repair”.",
                      url_for("faculty.club", club_id=a["club_id"]) + "#assets"))
    # No funding recorded this academic year.
    ay = _academic_year()
    for c in query(f"""SELECT club_id, name FROM Club WHERE club_id IN ({marks}) AND status = 'Active'
                       AND NOT EXISTS (SELECT 1 FROM Club_Funding f WHERE f.club_id = Club.club_id AND f.academic_year = ?)""",
                   tuple(club_ids) + (ay,)):
        flags.append(("warn", c["club_id"], c["name"], f"No funding recorded for {ay} yet.",
                      url_for("faculty.club", club_id=c["club_id"]) + "#funding"))
    # Clubs without a President.
    for c in query(f"""SELECT club_id, name FROM Club WHERE club_id IN ({marks})
                       AND NOT EXISTS (SELECT 1 FROM Membership m WHERE m.club_id = Club.club_id AND m.role = 'President')""",
                   tuple(club_ids)):
        flags.append(("error", c["club_id"], c["name"], "This club has no President.", url_for("faculty.club", club_id=c["club_id"])))
    order = {"error": 0, "warn": 1, "info": 2}
    return sorted(flags, key=lambda f: order[f[0]])


def _days(dt):
    d = query("SELECT CAST(julianday(?) - julianday('now') AS INTEGER) AS d", (dt,), one=True)["d"]
    return "today" if d <= 0 else ("1 day" if d == 1 else f"{d} days")


def _academic_year():
    return query("""SELECT CASE WHEN strftime('%m','now') >= '07'
                           THEN strftime('%Y','now') || '-' || substr(strftime('%Y','now','+1 year'),3,2)
                           ELSE strftime('%Y','now','-1 year') || '-' || substr(strftime('%Y','now'),3,2) END AS ay""",
                 one=True)["ay"]


@bp.route("/")
@roles_required("Faculty")
def dashboard():
    fid = g.user["person_id"]
    me = query("""SELECT p.name, p.email, f.department, f.designation
                  FROM Faculty f JOIN Person p ON p.person_id = f.faculty_id WHERE f.faculty_id = ?""", (fid,), one=True)
    clubs = [c for c in Q.club_summaries(active_only=False) if c["club_id"] in g.advised_clubs]
    marks = ",".join("?" for _ in g.advised_clubs) or "NULL"
    upcoming = query(f"SELECT * FROM v_event_seats WHERE club_id IN ({marks}) AND status='Upcoming' ORDER BY event_date LIMIT 8",
                     tuple(g.advised_clubs))
    return render_template("faculty/dashboard.html", me=me, clubs=clubs, flags=_flags(g.advised_clubs),
                           upcoming=upcoming, year=_academic_year())


@bp.route("/clubs/<int:club_id>")
@roles_required("Faculty")
def club(club_id):
    club = _advised_or_403(club_id)
    events = Q.events(club_id=club_id)
    for e in events:
        e["registrants"] = Q.event_registrants(e["event_id"]) if e["status"] == "Upcoming" else []
    return render_template("faculty/club.html", club=club,
                           members=Q.club_members(club_id, private=True),
                           events=events,
                           funding=crud.list_rows("funding", club_id),
                           funding_summary=Q.funding_summary(club_id),
                           assets=crud.list_rows("assets", club_id),
                           docs=crud.list_rows("documents", club_id),
                           notices=crud.list_rows("announcements", club_id),
                           flags=[f for f in _flags([club_id])])


@bp.route("/clubs/<int:club_id>/announcements/new", methods=["GET", "POST"])
@roles_required("Faculty")
def announce(club_id):
    club = _advised_or_403(club_id)
    errors, values = [], {}
    if request.method == "POST":
        values, errors = crud.validate("announcements", request.form)
        if not errors:
            _, err = crud.insert("announcements", values, club_id)
            if err:
                errors.append(err)
            else:
                flash("Announcement posted.", "success")
                return redirect(url_for("faculty.club", club_id=club_id) + "#notices")
    return render_template("manage/resource_form.html", club=club, resource="announcements",
                           spec=crud.spec("announcements"), values=values or request.form, errors=errors,
                           mode="new", scope="faculty")


@bp.route("/clubs/<int:club_id>/announcements/<int:pk>/delete", methods=["POST"])
@roles_required("Faculty")
def announce_delete(club_id, pk):
    _advised_or_403(club_id)
    row = crud.get_row("announcements", pk)
    # Faculty may only remove notices they posted themselves.
    if not row or row["club_id"] != club_id or row["posted_by"] != g.user["user_id"]:
        abort(403)
    crud.delete("announcements", pk)
    flash("Announcement removed.", "info")
    return redirect(url_for("faculty.club", club_id=club_id) + "#notices")
