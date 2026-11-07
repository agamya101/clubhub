"""
Club-head panel: /manage/<club_id>/…
Accessible to the club's President / Vice President and to Admins.
Faculty advisors get a read-only view of the same data under /faculty.
"""


from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import constants as C
import crud
import queries as Q
from auth import club_manager_required, is_admin, login_required
from db import execute, query, IntegrityError

bp = Blueprint("manage", __name__, url_prefix="/manage")

RESOURCES = ("events", "announcements", "funding", "assets", "documents")


def _club_or_404(club_id):
    club = Q.club_detail(club_id)
    if not club:
        abort(404)
    return club


@bp.route("/")
@login_required
def index():
    if is_admin():
        clubs = Q.club_summaries(active_only=False)
    else:
        ids = g.head_clubs
        if not ids:
            abort(403)
        clubs = [c for c in Q.club_summaries(active_only=False) if c["club_id"] in ids]
    if len(clubs) == 1:
        return redirect(url_for("manage.overview", club_id=clubs[0]["club_id"]))
    return render_template("manage/index.html", clubs=clubs)


@bp.route("/<int:club_id>")
@club_manager_required
def overview(club_id):
    club = _club_or_404(club_id)
    year = Q.academic_year()
    stats = dict(
        members=club["member_count"],
        upcoming=club["upcoming_events"],
        funding_year=Q.funding_total(club_id, year),
        funding_all=club["total_funding"],
        assets=query("SELECT COUNT(*) AS n, COALESCE(SUM(cost),0) AS v FROM Club_Asset WHERE club_id = ?", (club_id,), one=True),
        repairs=query("SELECT COUNT(*) AS n FROM Club_Asset WHERE club_id = ? AND item_condition = 'Needs Repair'", (club_id,), one=True)["n"],
    )
    return render_template("manage/overview.html", club=club, stats=stats, year=year,
                           upcoming=Q.events(club_id=club_id, upcoming_only=True),
                           notices=Q.announcements(club_id=club_id, live_only=False, limit=5),
                           leaders=[m for m in Q.club_members(club_id, private=True) if m["role"] != "Member"])


# ------------------------------------------------------------ club profile
@bp.route("/<int:club_id>/profile", methods=["GET", "POST"])
@club_manager_required
def profile(club_id):
    club = _club_or_404(club_id)
    errors = []
    if request.method == "POST":
        f = request.form
        fields = dict(tagline=f.get("tagline", "").strip() or None,
                      description=f.get("description", "").strip() or None,
                      room_no=f.get("room_no", "").strip() or None,
                      contact_email=f.get("contact_email", "").strip() or None,
                      founded_year=f.get("founded_year", type=int))
        if is_admin():  # only admins may rename, recategorise or deactivate
            fields["name"] = f.get("name", "").strip()
            fields["category"] = f.get("category")
            fields["status"] = f.get("status")
            if not fields["name"]:
                errors.append("Name is required.")
            if fields["category"] not in C.CLUB_CATEGORIES or fields["status"] not in C.CLUB_STATUSES:
                errors.append("Invalid category or status.")
        if not errors:
            try:
                keys = list(fields)
                execute(f"UPDATE Club SET {', '.join(k + ' = ?' for k in keys)} WHERE club_id = ?",
                        tuple(fields[k] for k in keys) + (club_id,))
                _save_subtype(club_id, fields.get("category", club["category"]), f)
                flash("Club profile saved.", "success")
                return redirect(url_for("manage.profile", club_id=club_id))
            except IntegrityError as e:
                errors.append(crud.friendly_integrity_error(e))
    return render_template("manage/profile.html", club=club, errors=errors, C=C)


def _save_subtype(club_id, category, f):
    """Upsert the specialisation row that matches the club's category."""
    if category == "Technical":
        execute("""INSERT INTO Technical_Club (club_id, github_url, tech_stack) VALUES (?,?,?)
                   ON DUPLICATE KEY UPDATE github_url = VALUES(github_url), tech_stack = VALUES(tech_stack)""",
                (club_id, f.get("github_url", "").strip() or None, f.get("tech_stack", "").strip() or "—"))
    elif category == "Cultural":
        execute("""INSERT INTO Cultural_Club (club_id, art_form) VALUES (?,?)
                   ON DUPLICATE KEY UPDATE art_form = VALUES(art_form)""",
                (club_id, f.get("art_form") or "Dance"))
    elif category == "Sports":
        execute("""INSERT INTO Sports_Club (club_id, sport, coach_name) VALUES (?,?,?)
                   ON DUPLICATE KEY UPDATE sport = VALUES(sport), coach_name = VALUES(coach_name)""",
                (club_id, f.get("sport", "").strip() or "—", f.get("coach_name", "").strip() or None))


# ------------------------------------------------------------ members
@bp.route("/<int:club_id>/members")
@club_manager_required
def members(club_id):
    club = _club_or_404(club_id)
    return render_template("manage/members.html", club=club, members=Q.club_members(club_id, private=True),
                           roles=C.MEMBERSHIP_ROLES)


@bp.route("/<int:club_id>/members/add", methods=["POST"])
@club_manager_required
def member_add(club_id):
    roll = request.form.get("roll_no", "").strip()
    role = request.form.get("role", "Member")
    s = query("SELECT student_id FROM Student WHERE roll_no = ?", (roll,), one=True)
    if not s:
        flash(f"No student with roll number {roll}.", "error")
    elif role not in C.MEMBERSHIP_ROLES:
        flash("Invalid role.", "error")
    else:
        try:
            execute("INSERT INTO Membership (student_id, club_id, role) VALUES (?,?,?)", (s["student_id"], club_id, role))
            flash("Member added.", "success")
        except IntegrityError as e:
            flash(crud.friendly_integrity_error(e).replace("That record already exists (duplicate key).",
                                                           "That student is already a member."), "error")
    return redirect(url_for("manage.members", club_id=club_id))


@bp.route("/<int:club_id>/members/<int:student_id>/role", methods=["POST"])
@club_manager_required
def member_role(club_id, student_id):
    role = request.form.get("role")
    if role not in C.MEMBERSHIP_ROLES:
        abort(400)
    try:
        execute("UPDATE Membership SET role = ? WHERE club_id = ? AND student_id = ?", (role, club_id, student_id))
        flash("Role updated.", "success")
    except IntegrityError as e:
        flash(crud.friendly_integrity_error(e), "error")
    return redirect(request.referrer or url_for("manage.members", club_id=club_id))


@bp.route("/<int:club_id>/members/<int:student_id>/remove", methods=["POST"])
@club_manager_required
def member_remove(club_id, student_id):
    execute("DELETE FROM Membership WHERE club_id = ? AND student_id = ?", (club_id, student_id))
    flash("Member removed.", "info")
    return redirect(request.referrer or url_for("manage.members", club_id=club_id))


# ------------------------------------------------------------ generic resources
@bp.route("/<int:club_id>/<resource>")
@club_manager_required
def resource_list(club_id, resource):
    if resource not in RESOURCES:
        abort(404)
    club = _club_or_404(club_id)
    rows = crud.list_rows(resource, club_id=club_id)
    extra = {}
    if resource == "funding":
        extra["summary"] = Q.funding_summary(club_id)
        extra["total"] = club["total_funding"]
    return render_template("manage/resource_list.html", club=club, resource=resource,
                           spec=crud.spec(resource), rows=rows, scope="manage", **extra)


@bp.route("/<int:club_id>/<resource>/new", methods=["GET", "POST"])
@club_manager_required
def resource_new(club_id, resource):
    if resource not in RESOURCES:
        abort(404)
    club = _club_or_404(club_id)
    errors, values = [], {}
    if request.method == "POST":
        values, errors = crud.validate(resource, request.form)
        if not errors:
            _, err = crud.insert(resource, values, club_id)
            if err:
                errors.append(err)
            else:
                flash(f"{crud.spec(resource)['label']} added.", "success")
                return redirect(url_for("manage.resource_list", club_id=club_id, resource=resource))
    return render_template("manage/resource_form.html", club=club, resource=resource, spec=crud.spec(resource),
                           values=values or request.form, errors=errors, mode="new", scope="manage")


@bp.route("/<int:club_id>/<resource>/<int:pk>/edit", methods=["GET", "POST"])
@club_manager_required
def resource_edit(club_id, resource, pk):
    if resource not in RESOURCES:
        abort(404)
    club = _club_or_404(club_id)
    row = crud.get_row(resource, pk)
    if not row or row["club_id"] != club_id:
        abort(404)
    errors = []
    if request.method == "POST":
        values, errors = crud.validate(resource, request.form)
        if not errors:
            err = crud.update(resource, pk, values)
            if err:
                errors.append(err)
            else:
                flash("Saved.", "success")
                return redirect(url_for("manage.resource_list", club_id=club_id, resource=resource))
        row = {**row, **request.form}
    return render_template("manage/resource_form.html", club=club, resource=resource, spec=crud.spec(resource),
                           values=row, errors=errors, mode="edit", pk=pk, scope="manage")


@bp.route("/<int:club_id>/<resource>/<int:pk>/delete", methods=["POST"])
@club_manager_required
def resource_delete(club_id, resource, pk):
    if resource not in RESOURCES:
        abort(404)
    row = crud.get_row(resource, pk)
    if not row or row["club_id"] != club_id:
        abort(404)
    crud.delete(resource, pk)
    flash("Deleted.", "info")
    return redirect(url_for("manage.resource_list", club_id=club_id, resource=resource))


@bp.route("/<int:club_id>/events/<int:event_id>/registrations")
@club_manager_required
def registrations(club_id, event_id):
    club = _club_or_404(club_id)
    ev = Q.event_detail(event_id)
    if not ev or ev["club_id"] != club_id:
        abort(404)
    return render_template("manage/registrations.html", club=club, ev=ev, rows=Q.event_registrants(event_id), scope="manage")


@bp.route("/<int:club_id>/events/<int:event_id>/registrations/<int:student_id>/remove", methods=["POST"])
@club_manager_required
def registration_remove(club_id, event_id, student_id):
    ev = Q.event_detail(event_id)
    if not ev or ev["club_id"] != club_id:
        abort(404)
    execute("DELETE FROM Event_Registration WHERE event_id = ? AND student_id = ?", (event_id, student_id))
    flash("Registration removed.", "info")
    return redirect(url_for("manage.registrations", club_id=club_id, event_id=event_id))
