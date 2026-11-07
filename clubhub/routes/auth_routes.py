"""Login / logout. One form for every role; redirect depends on role."""

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from auth import authenticate, home_for
from db import query

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for(home_for(g.user)))
    error = None
    if request.method == "POST":
        uid = authenticate(request.form.get("username", "").strip(), request.form.get("password", ""))
        if uid:
            session.clear()
            session["user_id"] = uid
            user = query("SELECT role FROM User_Account WHERE user_id = ?", (uid,), one=True)
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for(home_for(user)))
        error = "Wrong username or password."
    return render_template("auth/login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("public.home"))
