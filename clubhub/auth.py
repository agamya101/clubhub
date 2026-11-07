"""
Role-based access control for ClubHub.

Four access tiers, two of them stored:

    Public      no account                       browse clubs, events, notices
    Student     User_Account.role = 'Student'    + register for events, join clubs
    Club Head   DERIVED: Student whose Membership.role is President or
                Vice President                   + manage that club
    Faculty     User_Account.role = 'Faculty'    read-everything + alerts for
                                                 clubs they advise (Club_Advisor)
    Admin       User_Account.role = 'Admin'      everything

"Club Head" is deliberately not a column: it is a function of Membership,
so promoting someone to President grants the rights with no second write.
"""

from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from db import query

HEAD_ROLES = ("President", "Vice President")


# ---------------------------------------------------------------- loading
def load_current_user():
    """before_request hook: populate g.user and the clubs they control."""
    g.user = None
    g.head_clubs = []      # club ids this student heads
    g.advised_clubs = []   # club ids this faculty advises
    uid = session.get("user_id")
    if not uid:
        return
    user = query("""
        SELECT u.user_id, u.username, u.role, u.person_id, u.is_active,
               p.name, p.email
        FROM User_Account u LEFT JOIN Person p ON p.person_id = u.person_id
        WHERE u.user_id = ?""", (uid,), one=True)
    if not user or not user["is_active"]:
        session.clear()
        return
    g.user = user
    if user["role"] == "Student":
        g.head_clubs = [r["club_id"] for r in query(
            "SELECT club_id FROM Membership WHERE student_id = ? AND role IN (?, ?)",
            (user["person_id"], *HEAD_ROLES))]
    elif user["role"] == "Faculty":
        g.advised_clubs = [r["club_id"] for r in query(
            "SELECT club_id FROM Club_Advisor WHERE faculty_id = ?", (user["person_id"],))]


def authenticate(username, password):
    row = query("SELECT user_id, password_hash, is_active FROM User_Account WHERE username = ?",
                (username,), one=True)
    if row and row["is_active"] and check_password_hash(row["password_hash"], password):
        return row["user_id"]
    return None


# ---------------------------------------------------------------- predicates
def is_admin():
    return bool(g.user) and g.user["role"] == "Admin"


def is_student():
    return bool(g.user) and g.user["role"] == "Student"


def is_faculty():
    return bool(g.user) and g.user["role"] == "Faculty"


def is_club_head(club_id=None):
    if not is_student():
        return False
    return bool(g.head_clubs) if club_id is None else club_id in g.head_clubs


def advises(club_id):
    return is_faculty() and club_id in g.advised_clubs


def can_manage_club(club_id):
    """Create/edit/delete events, notices, members, funding, resources for a club."""
    return is_admin() or is_club_head(club_id)


def can_view_private(club_id):
    """See member contact details, funding, private documents, registrations."""
    return is_admin() or is_club_head(club_id) or advises(club_id)


def can_post_announcement(club_id):
    """Club heads and advisors for their club; admin anywhere (incl. college-wide)."""
    if club_id is None:
        return is_admin()
    return is_admin() or is_club_head(club_id) or advises(club_id)


def home_for(user):
    return {"Admin": "admin.dashboard", "Faculty": "faculty.dashboard",
            "Student": "student.dashboard"}[user["role"]]


# ---------------------------------------------------------------- decorators
def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not g.user:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view(*a, **kw)
    return wrapped


def roles_required(*roles):
    def deco(view):
        @wraps(view)
        @login_required
        def wrapped(*a, **kw):
            if g.user["role"] not in roles:
                abort(403)
            return view(*a, **kw)
        return wrapped
    return deco


def club_manager_required(view):
    """For routes with a <int:club_id> argument — admin or that club's head."""
    @wraps(view)
    @login_required
    def wrapped(*a, **kw):
        if not can_manage_club(kw.get("club_id")):
            abort(403)
        return view(*a, **kw)
    return wrapped


def club_viewer_required(view):
    """Admin, club head, or faculty advisor of that club."""
    @wraps(view)
    @login_required
    def wrapped(*a, **kw):
        if not can_view_private(kw.get("club_id")):
            abort(403)
        return view(*a, **kw)
    return wrapped


def template_helpers():
    """Injected into every template."""
    return dict(
        current_user=g.get("user"),
        head_clubs=g.get("head_clubs", []),
        advised_clubs=g.get("advised_clubs", []),
        is_admin=is_admin, is_student=is_student, is_faculty=is_faculty,
        is_club_head=is_club_head, can_manage_club=can_manage_club,
        can_view_private=can_view_private, can_post_announcement=can_post_announcement,
    )
