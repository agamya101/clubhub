"""
Generic CRUD engine for the club-scoped resources (events, funding, assets,
documents, announcements). One spec per resource drives listing, forms,
validation and SQL — the same code serves the club-head panel and the
admin console. Entities with composite keys or supertype/subtype splits
(students, faculty, clubs, memberships…) have hand-written handlers in
routes/admin.py.
"""


from flask import g

import constants as C
from db import execute, query, IntegrityError


def F(name, label, type="text", required=False, options=None, help=None, step=None, readonly=False):
    return dict(name=name, label=label, type=type, required=required, options=options,
                help=help, step=step, readonly=readonly)


RESOURCES = {
    "events": dict(
        table="Event", pk="event_id", label="Event", plural="Events", icon="calendar",
        order="e.event_date DESC",
        fields=[
            F("title", "Title", required=True),
            F("event_type", "Type", "select", True, C.EVENT_TYPES),
            F("event_date", "Date & time", "datetime-local", True),
            F("registration_deadline", "Registration deadline", "date", help="Leave blank to accept registrations until the event starts."),
            F("venue", "Venue", required=True),
            F("capacity", "Capacity", "number", True, step="1"),
            F("status", "Status", "select", True, C.EVENT_STATUSES),
            F("description", "Description", "textarea"),
        ],
        list_sql="""SELECT e.*, c.name AS club_name,
                           (SELECT COUNT(*) FROM Event_Registration r WHERE r.event_id = e.event_id) AS registered
                    FROM Event e JOIN Club c ON c.club_id = e.club_id {where} ORDER BY {order}""",
        columns=[("title", "Title"), ("event_type", "Type"), ("event_date", "When"), ("venue", "Venue"),
                 ("seats", "Seats"), ("status", "Status")],
    ),
    "funding": dict(
        table="Club_Funding", pk="funding_id", label="Funding entry", plural="Funding", icon="coins",
        order="f.received_on DESC",
        fields=[
            F("source_type", "Source", "select", True, C.FUNDING_SOURCES),
            F("sponsor_name", "Sponsor / grantor", help="Optional for membership fees or event revenue."),
            F("amount", "Amount (₹)", "number", True, step="0.01"),
            F("received_on", "Received on", "date", True),
            F("academic_year", "Academic year", required=True, help="Format 2026-27"),
            F("remarks", "Remarks", "textarea"),
        ],
        list_sql="SELECT f.*, c.name AS club_name FROM Club_Funding f JOIN Club c ON c.club_id = f.club_id {where} ORDER BY {order}",
        columns=[("received_on", "Date"), ("source_type", "Source"), ("sponsor_name", "From"),
                 ("amount", "Amount"), ("academic_year", "Year")],
    ),
    "assets": dict(
        table="Club_Asset", pk="asset_id", label="Asset", plural="Assets", icon="box",
        order="a.name ASC",
        fields=[
            F("name", "Item", required=True),
            F("asset_type", "Type", "select", True, C.ASSET_TYPES),
            F("quantity", "Quantity", "number", True, step="1"),
            F("item_condition", "Condition", "select", True, C.ASSET_CONDITIONS),
            F("acquired_on", "Acquired on", "date"),
            F("cost", "Total cost (₹)", "number", step="0.01"),
        ],
        list_sql="SELECT a.*, c.name AS club_name FROM Club_Asset a JOIN Club c ON c.club_id = a.club_id {where} ORDER BY {order}",
        columns=[("name", "Item"), ("asset_type", "Type"), ("quantity", "Qty"), ("item_condition", "Condition"),
                 ("acquired_on", "Acquired"), ("cost", "Cost")],
    ),
    "documents": dict(
        table="Club_Document", pk="doc_id", label="Document", plural="Documents", icon="file",
        order="d.uploaded_on DESC",
        fields=[
            F("title", "Title", required=True),
            F("doc_type", "Type", "select", True, C.DOC_TYPES),
            F("url", "Link", "url", True, help="Drive / GitHub / form link."),
            F("visibility", "Visibility", "select", True, C.DOC_VISIBILITY,
              help="Public: anyone. Members: signed-in students. Private: club heads, advisors, admin."),
            F("uploaded_on", "Uploaded on", "date", True),
        ],
        list_sql="SELECT d.*, c.name AS club_name FROM Club_Document d JOIN Club c ON c.club_id = d.club_id {where} ORDER BY {order}",
        columns=[("title", "Title"), ("doc_type", "Type"), ("visibility", "Visibility"), ("uploaded_on", "Uploaded")],
    ),
    "announcements": dict(
        table="Announcement", pk="announcement_id", label="Announcement", plural="Announcements", icon="megaphone",
        order="n.is_pinned DESC, n.posted_at DESC",
        fields=[
            F("title", "Title", required=True),
            F("content", "Message", "textarea", True),
            F("priority", "Priority", "select", True, C.ANNOUNCEMENT_PRIORITY,
              help="Alerts are shown as a banner on the public site and student dashboards."),
            F("is_pinned", "Pin to top", "checkbox"),
            F("expires_at", "Expires on", "date", help="Hidden from public pages after this date."),
        ],
        list_sql="""SELECT n.*, c.name AS club_name, u.username AS posted_by_name, u.role AS poster_role
                    FROM Announcement n LEFT JOIN Club c ON c.club_id = n.club_id
                    JOIN User_Account u ON u.user_id = n.posted_by {where} ORDER BY {order}""",
        columns=[("title", "Title"), ("priority", "Priority"), ("is_pinned", "Pinned"),
                 ("posted_by_name", "By"), ("posted_at", "Posted"), ("expires_at", "Expires")],
    ),
}

ALIAS = {"events": "e", "funding": "f", "assets": "a", "documents": "d", "announcements": "n"}


def spec(name):
    return RESOURCES[name]


def list_rows(name, club_id=None, extra_where="", args=()):
    s = spec(name)
    alias = ALIAS[name]
    conds, params = [], []
    if club_id is not None:
        conds.append(f"{alias}.club_id = ?")
        params.append(club_id)
    if extra_where:
        conds.append(extra_where)
        params.extend(args)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    return query(s["list_sql"].format(where=where, order=s["order"]), tuple(params))


def get_row(name, pk):
    s = spec(name)
    return query(f"SELECT * FROM {s['table']} WHERE {s['pk']} = ?", (pk,), one=True)


def validate(name, form):
    """Return (clean_dict, errors_list). Coerces types; required check; enum check."""
    s = spec(name)
    data, errors = {}, []
    for f in s["fields"]:
        raw = form.get(f["name"], "")
        if f["type"] == "checkbox":
            data[f["name"]] = 1 if raw else 0
            continue
        raw = (raw or "").strip()
        if not raw:
            if f["required"]:
                errors.append(f"{f['label']} is required.")
            data[f["name"]] = None
            continue
        if f["type"] == "number":
            try:
                data[f["name"]] = int(raw) if f.get("step") == "1" else float(raw)
            except ValueError:
                errors.append(f"{f['label']} must be a number.")
                continue
            if data[f["name"]] <= 0 and f["name"] in ("capacity", "amount", "quantity"):
                errors.append(f"{f['label']} must be greater than zero.")
        elif f["type"] == "select" and raw not in f["options"]:
            errors.append(f"{f['label']} must be one of: {', '.join(f['options'])}.")
            continue
        elif f["type"] == "datetime-local":
            data[f["name"]] = raw.replace("T", " ")[:16]
            continue
        else:
            data[f["name"]] = raw
    if name == "events" and data.get("registration_deadline") and data.get("event_date") \
            and data["registration_deadline"] > data["event_date"]:
        errors.append("Registration deadline cannot be after the event date.")
    return data, errors


def friendly_integrity_error(err):
    msg = str(err)
    errno = getattr(err, "errno", None)
    if errno == 1062 or "Duplicate entry" in msg:
        return "That record already exists (duplicate key)."
    if errno in (1451, 1452) or "foreign key constraint" in msg.lower():
        return "That record refers to something that does not exist."
    if errno in (3819, 4025) or "CONSTRAINT" in msg and "failed" in msg:
        return "A value fails the database's validation rules (" + msg.split(":")[-1].strip() + ")."
    if errno == 1265 or "Data truncated" in msg:
        return "A value is not one of the allowed options."
    if errno == 1644:  # trigger SIGNAL — message is already human-readable
        return msg.split(": ", 1)[-1]
    return msg


def insert(name, data, club_id, posted_by=None):
    s = spec(name)
    cols = {**data, "club_id": club_id}
    if name == "announcements":
        cols["posted_by"] = posted_by or g.user["user_id"]
    keys = list(cols)
    sql = f"INSERT INTO {s['table']} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})"
    try:
        cur = execute(sql, tuple(cols[k] for k in keys))
        return cur.lastrowid, None
    except IntegrityError as e:
        return None, friendly_integrity_error(e)


def update(name, pk, data, club_id=None):
    s = spec(name)
    cols = dict(data)
    if club_id is not None:
        cols["club_id"] = club_id
    keys = list(cols)
    sql = f"UPDATE {s['table']} SET {', '.join(k + ' = ?' for k in keys)} WHERE {s['pk']} = ?"
    try:
        execute(sql, tuple(cols[k] for k in keys) + (pk,))
        return None
    except IntegrityError as e:
        return friendly_integrity_error(e)


def delete(name, pk):
    s = spec(name)
    cur = execute(f"DELETE FROM {s['table']} WHERE {s['pk']} = ?", (pk,))
    return cur.rowcount > 0
