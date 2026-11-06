"""Request validation. Returns clean values or raises ApiError(400)."""
import math
import re
from datetime import date

from flask import request

from .services.recommender import (
    BODY_PARTS, EQUIPMENT, GOALS, LEVELS, SESSION_MINUTES,
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# metric -> plausible (low, high), so a typo can't wreck the progress chart
PROGRESS_METRICS = {
    "weight_kg": (30, 250),
    "waist_cm": (40, 200),
    "body_fat_pct": (3, 70),
}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, fields: dict | None = None):
        super().__init__(message)
        self.message, self.status, self.fields = message, status, fields or {}


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object.")
    return data


def _number(data, key, lo, hi, errors, *, integer=False, required=True):
    raw = data.get(key)
    if raw in (None, ""):
        if required:
            errors[key] = "This field is required."
        return None
    try:
        if isinstance(raw, bool):
            raise TypeError
        val = float(raw)
        if not math.isfinite(val):  # "nan" and "inf" parse as floats
            raise ValueError
    except (TypeError, ValueError):
        errors[key] = "Must be a number."
        return None
    if integer and val != int(val):
        errors[key] = "Must be a whole number."
        return None
    if not (lo <= val <= hi):
        errors[key] = f"Must be between {lo} and {hi}."
        return None
    return int(val) if integer else val


def validate_register(data: dict) -> dict:
    errors = {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    password = data.get("password", "")
    if not USERNAME_RE.match(username):
        errors["username"] = "3-30 characters: letters, numbers and underscores."
    if not EMAIL_RE.match(email) or len(email) > 100:
        errors["email"] = "Enter a valid email address."
    password_error = _password_error(password)
    if password_error:
        errors["password"] = password_error
    if errors:
        raise ApiError("Please fix the highlighted fields.", fields=errors)
    return {"username": username, "email": email, "password": password}


def _password_error(password) -> str | None:
    if not isinstance(password, str) or len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    return None


def validate_new_password(data: dict) -> str:
    error = _password_error(data.get("new_password", ""))
    if error:
        raise ApiError("Please fix the highlighted fields.", fields={"new_password": error})
    return data["new_password"]


def validate_profile(data: dict) -> dict:
    errors = {}
    clean = {
        "age": _number(data, "age", 14, 90, errors, integer=True),
        "weight_kg": _number(data, "weight_kg", 30, 250, errors),
        "height_cm": _number(data, "height_cm", 100, 230, errors, required=False),
        "days_per_week": _number(data, "days_per_week", 2, 6, errors, integer=True),
        "plan_weeks": _number(data, "plan_weeks", 2, 12, errors, integer=True, required=False) or 4,
    }
    for key, allowed in (("experience_level", LEVELS), ("goal", GOALS), ("equipment", EQUIPMENT)):
        val = data.get(key)
        if val not in allowed:
            errors[key] = "Choose one of: " + ", ".join(allowed) + "."
        clean[key] = val

    minutes = _number(data, "session_minutes", 30, 60, errors, integer=True)
    if minutes is not None and minutes not in SESSION_MINUTES:
        errors["session_minutes"] = "Choose 30, 45 or 60 minutes."
    clean["session_minutes"] = minutes

    clean["has_heavy_bag"] = bool(data.get("has_heavy_bag", False))

    avoid = data.get("avoid_body_parts", [])
    if not isinstance(avoid, list) or any(a not in BODY_PARTS for a in avoid):
        errors["avoid_body_parts"] = "Must be a list of known body parts."
        avoid = []
    clean["avoid_body_parts"] = sorted(set(avoid))

    if errors:
        raise ApiError("Please fix the highlighted fields.", fields=errors)
    return clean


def validate_progress(data: dict) -> dict:
    errors = {}
    metric = data.get("metric")
    if metric not in PROGRESS_METRICS:
        errors["metric"] = "Choose one of: " + ", ".join(PROGRESS_METRICS) + "."
    lo, hi = PROGRESS_METRICS.get(metric, (0, 1000))
    value = _number(data, "value", lo, hi, errors)
    when = data.get("date") or date.today().isoformat()
    try:
        date.fromisoformat(str(when))
    except ValueError:
        errors["date"] = "Use YYYY-MM-DD."
    if errors:
        raise ApiError("Please fix the highlighted fields.", fields=errors)
    return {"metric": metric, "value": value, "date": str(when)}


def validate_completion(data: dict) -> dict:
    errors = {}
    rating = _number(data, "rating", 1, 5, errors, integer=True)
    content = str(data.get("notes", "") or "").strip()
    if len(content) > 1000:
        errors["notes"] = "Keep notes under 1000 characters."
    if errors:
        raise ApiError("Please fix the highlighted fields.", fields=errors)
    return {"rating": rating, "notes": content}
