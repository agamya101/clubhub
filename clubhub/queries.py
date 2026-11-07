"""Read queries shared by several blueprints."""

from db import query
from constants import CLUB_SUBTYPE

def academic_year():
    from datetime import date
    t = date.today()
    y = t.year if t.month >= 7 else t.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def club_summaries(category=None, active_only=True):
    conds, args = [], []
    if category:
        conds.append("category = ?"); args.append(category)
    if active_only:
        conds.append("status = 'Active'")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    return query(f"SELECT * FROM v_club_summary {where} ORDER BY name", tuple(args))


def club_detail(club_id):
    club = query("SELECT * FROM v_club_summary WHERE club_id = ?", (club_id,), one=True)
    if not club:
        return None
    full = query("SELECT * FROM Club WHERE club_id = ?", (club_id,), one=True)
    club.update(full)
    sub = CLUB_SUBTYPE.get(club["category"])
    club["subtype"] = query(f"SELECT * FROM {sub} WHERE club_id = ?", (club_id,), one=True) if sub else None
    club["advisors"] = query("""
        SELECT f.faculty_id, p.name, p.email, p.phone, f.department, f.designation, ca.assigned_on
        FROM Club_Advisor ca JOIN Faculty f ON f.faculty_id = ca.faculty_id
        JOIN Person p ON p.person_id = f.faculty_id
        WHERE ca.club_id = ? ORDER BY ca.assigned_on""", (club_id,))
    return club


def club_members(club_id, private=False):
    """Public view: name, role, branch, year. Private adds email, phone, roll_no."""
    extra = ", p.email, p.phone, s.roll_no" if private else ""
    return query(f"""
        SELECT s.student_id, p.name, s.branch, s.year, m.role, m.joined_at {extra}
        FROM Membership m JOIN Student s ON s.student_id = m.student_id
        JOIN Person p ON p.person_id = s.student_id
        WHERE m.club_id = ?
        ORDER BY CASE m.role WHEN 'President' THEN 1 WHEN 'Vice President' THEN 2 WHEN 'Secretary' THEN 3
                             WHEN 'Treasurer' THEN 4 WHEN 'Core Member' THEN 5 ELSE 6 END, p.name""", (club_id,))


def events(club_id=None, event_type=None, status=None, upcoming_only=False, limit=None):
    conds, args = [], []
    if club_id:
        conds.append("club_id = ?"); args.append(club_id)
    if event_type:
        conds.append("event_type = ?"); args.append(event_type)
    if status:
        conds.append("status = ?"); args.append(status)
    if upcoming_only:
        conds.append("status = 'Upcoming' AND event_date >= NOW()")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    order = "ORDER BY event_date ASC" if upcoming_only else "ORDER BY event_date DESC"
    lim = f"LIMIT {int(limit)}" if limit else ""
    return query(f"SELECT * FROM v_event_seats {where} {order} {lim}", tuple(args))


def event_detail(event_id):
    return query("SELECT * FROM v_event_seats WHERE event_id = ?", (event_id,), one=True)


def event_registrants(event_id):
    return query("""
        SELECT s.student_id, p.name, p.email, s.roll_no, s.branch, s.year, r.registered_at
        FROM Event_Registration r JOIN Student s ON s.student_id = r.student_id
        JOIN Person p ON p.person_id = s.student_id
        WHERE r.event_id = ? ORDER BY r.registered_at""", (event_id,))


def announcements(club_id=None, include_collegewide=False, live_only=True, limit=None, alerts_only=False):
    conds, args = [], []
    if club_id is not None and include_collegewide:
        conds.append("(n.club_id = ? OR n.club_id IS NULL)"); args.append(club_id)
    elif club_id is not None:
        conds.append("n.club_id = ?"); args.append(club_id)
    elif not include_collegewide:
        pass  # all
    if live_only:
        conds.append("(n.expires_at IS NULL OR n.expires_at >= CURDATE())")
    if alerts_only:
        conds.append("n.priority = 'Alert'")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    lim = f"LIMIT {int(limit)}" if limit else ""
    return query(f"""
        SELECT n.*, c.name AS club_name, c.category AS club_category,
               COALESCE(p.name, 'Student Welfare Office') AS author
        FROM Announcement n LEFT JOIN Club c ON c.club_id = n.club_id
        JOIN User_Account u ON u.user_id = n.posted_by
        LEFT JOIN Person p ON p.person_id = u.person_id
        {where} ORDER BY n.is_pinned DESC, n.posted_at DESC {lim}""", tuple(args))


def collegewide_alerts():
    return query("""
        SELECT n.* FROM Announcement n
        WHERE n.club_id IS NULL AND n.priority = 'Alert'
          AND (n.expires_at IS NULL OR n.expires_at >= CURDATE())
        ORDER BY n.posted_at DESC""")


def documents(club_id, visibility_levels):
    marks = ",".join("?" for _ in visibility_levels)
    return query(f"SELECT * FROM Club_Document WHERE club_id = ? AND visibility IN ({marks}) ORDER BY uploaded_on DESC",
                 (club_id, *visibility_levels))


def student_clubs(student_id):
    return query("""
        SELECT c.club_id, c.name, c.category, c.tagline, m.role, m.joined_at
        FROM Membership m JOIN Club c ON c.club_id = m.club_id
        WHERE m.student_id = ? ORDER BY m.joined_at DESC""", (student_id,))


def student_registrations(student_id):
    return query("""
        SELECT v.*, r.registered_at
        FROM Event_Registration r JOIN v_event_seats v ON v.event_id = r.event_id
        WHERE r.student_id = ? ORDER BY v.event_date DESC""", (student_id,))


def funding_summary(club_id):
    return query("""
        SELECT academic_year, source_type, SUM(amount) AS total, COUNT(*) AS entries
        FROM Club_Funding WHERE club_id = ?
        GROUP BY academic_year, source_type ORDER BY academic_year DESC, total DESC""", (club_id,))


def funding_total(club_id, academic_year=None):
    if academic_year:
        return query("SELECT COALESCE(SUM(amount),0) AS t FROM Club_Funding WHERE club_id = ? AND academic_year = ?",
                     (club_id, academic_year), one=True)["t"]
    return query("SELECT COALESCE(SUM(amount),0) AS t FROM Club_Funding WHERE club_id = ?", (club_id,), one=True)["t"]
