"""
MySQL / MariaDB connection helpers (XAMPP).

Settings come from environment variables with XAMPP defaults:
    CLUBHUB_DB_HOST=127.0.0.1  CLUBHUB_DB_PORT=3306  CLUBHUB_DB_USER=root
    CLUBHUB_DB_PASSWORD=       CLUBHUB_DB_NAME=clubhub

Queries are written with '?' placeholders (kept from the SQLite version);
this module converts them to '%s' for the connector.
"""

import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

import mysql.connector
from mysql.connector import errors
from flask import g, current_app

# Any of these means "the database refused the write" (constraint, FK, trigger SIGNAL).
IntegrityError = (errors.IntegrityError, errors.DatabaseError, errors.DataError)

CONFIG = dict(
    host=os.environ.get("CLUBHUB_DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("CLUBHUB_DB_PORT", "3306")),
    user=os.environ.get("CLUBHUB_DB_USER", "root"),
    password=os.environ.get("CLUBHUB_DB_PASSWORD", ""),
    database=os.environ.get("CLUBHUB_DB_NAME", "clubhub"),
)


def connect(database=None, **overrides):
    cfg = {**CONFIG, **overrides}
    cfg["database"] = database          # None ⇒ connect to the server only
    return mysql.connector.connect(charset="utf8mb4", autocommit=False, **cfg)


def get_db():
    if "db" not in g:
        cfg = {"database": CONFIG["database"], **(current_app.config.get("DB_CONFIG") or {})}
        g.db = connect(**cfg)
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _plain(v):
    """Normalise driver types to what the templates expect (strings / floats)."""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _q(sql):
    return sql.replace("?", "%s")


def query(sql, args=(), one=False):
    """SELECT helper → list of dicts (or one dict / None)."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(_q(sql), tuple(args))
    rows = [{k: _plain(v) for k, v in r.items()} for r in cur.fetchall()]
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """INSERT/UPDATE/DELETE helper. Commits and returns the cursor (lastrowid, rowcount)."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(_q(sql), tuple(args))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return cur


@contextmanager
def transaction():
    """Several writes, all or nothing:   with transaction() as cur: cur.execute(...)"""
    db = get_db()
    cur = db.cursor()
    try:
        if not db.in_transaction:
            db.start_transaction()
        yield _Cur(cur)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()


class _Cur:
    """Thin wrapper so transaction code can keep using '?' placeholders."""
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, args=()):
        self._cur.execute(_q(sql), tuple(args))
        return self

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        return self._cur.fetchone()


def init_app(app):
    app.teardown_appcontext(close_db)
