"""
ClubHub — Student Club & Organisation Management System
Flask application factory.

    python database/init_db.py   # build database/clubhub.db
    python app.py                # http://127.0.0.1:5000
"""

import os
from datetime import datetime

from flask import Flask, render_template

import auth
import db
from routes import admin, auth_routes, faculty, manage, public, student

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CLUBHUB_SECRET", "clubhub-dev-secret-change-me"),
        DATABASE=os.path.join(BASE_DIR, "database", "clubhub.db"),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.before_request(auth.load_current_user)
    app.context_processor(auth.template_helpers)

    for bp in (public.bp, auth_routes.bp, student.bp, manage.bp, faculty.bp, admin.bp):
        app.register_blueprint(bp)

    # ---- template filters -------------------------------------------------
    @app.template_filter("dt")
    def fmt_datetime(value):
        """'2026-11-21 09:00' → 'Sat 21 Nov, 09:00'"""
        if not value:
            return "—"
        for f in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                d = datetime.strptime(value[:len("2026-11-21 09:00:00")], f)
                return d.strftime("%a %d %b, %H:%M") if "%H" in f else d.strftime("%d %b %Y")
            except ValueError:
                continue
        return value

    @app.template_filter("date")
    def fmt_date(value):
        if not value:
            return "—"
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            return value

    @app.template_filter("inr")
    def fmt_inr(value):
        """Indian grouping: 1234567 → 12,34,567"""
        if value is None:
            return "—"
        n = int(round(float(value)))
        s = str(abs(n))
        if len(s) > 3:
            head, tail = s[:-3], s[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            if head:
                parts.insert(0, head)
            s = ",".join(parts) + "," + tail
        return ("-" if n < 0 else "") + "₹" + s

    @app.template_filter("month")
    def fmt_month(value):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%b").upper()
        except (ValueError, TypeError):
            return ""

    @app.template_filter("day")
    def fmt_day(value):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d")
        except (ValueError, TypeError):
            return ""

    @app.template_filter("initials")
    def initials(name):
        parts = [p for p in (name or "").replace("Dr.", "").split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    # ---- errors ------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, title="Not allowed",
                               text="Your account does not have permission to open this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, title="Not found",
                               text="That page or record does not exist."), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
