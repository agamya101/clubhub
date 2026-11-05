"""SQLite connection helpers. One connection per request, foreign keys always on."""

import sqlite3
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    """SELECT helper → list of dicts (or one dict / None)."""
    rows = get_db().execute(sql, args).fetchall()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def execute(sql, args=()):
    """INSERT/UPDATE/DELETE helper. Commits and returns the cursor."""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur


def init_app(app):
    app.teardown_appcontext(close_db)
