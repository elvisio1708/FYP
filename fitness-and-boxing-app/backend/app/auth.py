"""Authentication: register, login, logout, current user, account management.

Uses Flask's signed session cookie (HttpOnly, SameSite=Lax). Passwords are
hashed with werkzeug and are never logged or returned. Repeated failed logins
for the same username from the same address are locked out for a while.
"""
import sqlite3
import time
from functools import wraps

from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, utcnow
from .validation import ApiError, json_body, validate_new_password, validate_register

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

# Verified against when the username doesn't exist, so a missing user and a
# wrong password take about the same time and give the same answer.
_DUMMY_HASH = generate_password_hash("not-a-real-password")

MAX_FAILED_LOGINS = 8
LOCKOUT_SECONDS = 15 * 60


def _attempt_key(username: str) -> str:
    # Keyed on address + username so nobody can lock another user out from afar.
    return f"{request.remote_addr}|{username.lower()}"


def _check_lockout(db, key: str) -> None:
    cutoff = time.time() - LOCKOUT_SECONDS
    failed = db.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE key = ? AND created_at > ?", (key, cutoff)
    ).fetchone()[0]
    if failed >= MAX_FAILED_LOGINS:
        raise ApiError("Too many failed attempts. Try again in 15 minutes.", 429)


def _record_failure(db, key: str) -> None:
    db.execute("DELETE FROM login_attempts WHERE created_at <= ?", (time.time() - LOCKOUT_SECONDS,))
    db.execute("INSERT INTO login_attempts (key, created_at) VALUES (?, ?)", (key, time.time()))
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            raise ApiError("Please log in.", 401)
        row = get_db().execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:  # account deleted but cookie still valid
            session.clear()
            raise ApiError("Please log in.", 401)
        g.user = row
        return view(*args, **kwargs)

    return wrapped


def _user_json(row) -> dict:
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


@auth_bp.post("/register")
def register():
    data = validate_register(json_body())
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash, date_joined) VALUES (?, ?, ?, ?)",
            (data["username"], data["email"], generate_password_hash(data["password"]), utcnow()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # Don't reveal which of the two was taken beyond what the user needs.
        raise ApiError("That username or email is already registered.", 409)
    session.clear()
    session["user_id"] = cur.lastrowid
    session.permanent = True
    row = db.execute("SELECT id, username, email FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({"user": _user_json(row)}), 201


@auth_bp.post("/login")
def login():
    data = json_body()
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    if not username or not isinstance(password, str) or not password:
        raise ApiError("Enter your username and password.")

    db = get_db()
    key = _attempt_key(username)
    _check_lockout(db, key)
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    stored = row["password_hash"] if row else _DUMMY_HASH
    ok = check_password_hash(stored, password)
    if row is None or not ok:
        _record_failure(db, key)
        raise ApiError("Invalid username or password.", 401)

    db.execute("DELETE FROM login_attempts WHERE key = ?", (key,))
    db.execute("UPDATE users SET last_login = ? WHERE id = ?", (utcnow(), row["id"]))
    db.commit()
    session.clear()  # new session on login (prevents session fixation)
    session["user_id"] = row["id"]
    session.permanent = True
    return jsonify({"user": _user_json(row)})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@auth_bp.get("/me")
@login_required
def me():
    return jsonify({"user": _user_json(g.user)})


def _require_password(db, password) -> None:
    """Sensitive account changes need the current password, not just a cookie."""
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    if not isinstance(password, str) or not check_password_hash(row["password_hash"], password):
        raise ApiError("That password is not correct.", 403)


@auth_bp.put("/account/password")
@login_required
def change_password():
    data = json_body()
    db = get_db()
    _require_password(db, data.get("current_password"))
    new_password = validate_new_password(data)
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), g.user["id"]),
    )
    db.commit()
    return jsonify({"message": "Password updated."})


@auth_bp.delete("/account")
@login_required
def delete_account():
    data = json_body()
    db = get_db()
    _require_password(db, data.get("password"))
    db.execute("DELETE FROM users WHERE id = ?", (g.user["id"],))  # cascades to all user data
    db.commit()
    session.clear()
    return jsonify({"message": "Account deleted."})
