from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from backend.database import create_user, get_user_by_email, get_user_by_id, update_last_login


auth_bp = Blueprint("auth", __name__)


login_manager: LoginManager | None = None


def init_login(app):
    global login_manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)


@dataclass
class User(UserMixin):
    id: int
    name: str
    email: str
    role: str
    active: bool

    def get_id(self) -> str:  # type: ignore[override]
        return str(self.id)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_active(self) -> bool:  # flask-login expects this property
        return bool(self.active)



@auth_bp.record_once
def _register(state):
    app = state.app
    # bind user loader
    @login_manager.user_loader  # type: ignore[attr-defined]
    def load_user(user_id: str):
        row = get_user_by_id(app.config["DATABASE_PATH"], int(user_id))
        if not row:
            return None
        return User(id=row["id"], name=row["name"], email=row["email"], role=row["role"], active=bool(row["is_active"]))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user_row = get_user_by_email(current_app.config["DATABASE_PATH"], email)
        if not user_row:
            error = "Invalid email or password."
        else:
            if not check_password_hash(user_row["password_hash"], password):
                error = "Invalid email or password."
            else:
                user = User(id=user_row["id"], name=user_row["name"], email=user_row["email"], role=user_row["role"], active=bool(user_row["is_active"]))
                login_user(user)
                update_last_login(current_app.config["DATABASE_PATH"], user.id)
                flash("Signed in successfully.", "success")
                next_page = request.args.get("next") or ("/admin/dashboard" if user.is_admin else "/dashboard")
                return redirect(next_page)
    return render_template("login.html", error=error)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    errors = []
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("Valid email is required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if get_user_by_email(current_app.config["DATABASE_PATH"], email):
            errors.append("An account with that email already exists.")

        if not errors:
            password_hash = generate_password_hash(password)
            user_id = create_user(current_app.config["DATABASE_PATH"], name, email, password_hash, role="user")
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("signup.html", errors=errors)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("home"))


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)

    return wrapper
