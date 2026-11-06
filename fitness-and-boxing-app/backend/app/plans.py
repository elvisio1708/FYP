"""Profile, training plans, session completion/feedback, stats and progress."""
import json
from datetime import date, datetime, timedelta

from flask import Blueprint, g, jsonify

from .auth import login_required
from .db import get_db, utcnow
from .services.boxing import CIRCUIT_PREFIX
from .services.recommender import estimate_minutes, get_recommender, week_factor
from .validation import (
    ApiError, json_body, validate_completion, validate_profile, validate_progress,
)

plans_bp = Blueprint("plans", __name__, url_prefix="/api")

FEEDBACK_WINDOW = 6  # most recent sessions that influence the next plan
STATS_WEEKS = 8      # weeks shown in the training-volume chart
EXERCISE_FIELDS = (
    "id", "name", "kind", "exercise_type", "body_part", "equipment", "description",
    "sets", "reps", "duration_seconds", "rest_seconds", "notes", "difficulty", "match_score",
)


# ---- helpers -----------------------------------------------------------------
def _profile_json(row) -> dict:
    return {
        "age": row["age"],
        "weight_kg": row["weight_kg"],
        "height_cm": row["height_cm"],
        "experience_level": row["experience_level"],
        "goal": row["goal"],
        "days_per_week": row["days_per_week"],
        "session_minutes": row["session_minutes"],
        "equipment": row["equipment"],
        "has_heavy_bag": bool(row["has_heavy_bag"]),
        "avoid_body_parts": [p for p in row["avoid_body_parts"].split(",") if p],
        "plan_weeks": row["plan_weeks"],
    }


def feedback_intensity(db, user_id: int) -> float:
    """Turn recent session ratings into an intensity multiplier (0.8 - 1.2).

    Ratings: 1 = too easy ... 3 = about right ... 5 = too hard. Average 3 means
    no change; each point away from 3 shifts intensity by 10%.
    """
    rows = db.execute(
        "SELECT rating FROM feedback WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, FEEDBACK_WINDOW),
    ).fetchall()
    if not rows:
        return 1.0
    avg = sum(r["rating"] for r in rows) / len(rows)
    return round(min(1.2, max(0.8, 1 + (3 - avg) * 0.1)), 2)


def _load_plan(db, plan_id: int, user_id: int) -> dict:
    plan = db.execute(
        "SELECT * FROM training_plans WHERE id = ? AND user_id = ?", (plan_id, user_id)
    ).fetchone()
    if plan is None:
        raise ApiError("Plan not found.", 404)
    sessions = db.execute(
        "SELECT * FROM training_sessions WHERE plan_id = ? ORDER BY week, day_index", (plan_id,)
    ).fetchall()
    exercises = db.execute(
        """SELECT e.* FROM session_exercises e
           JOIN training_sessions s ON s.id = e.session_id
           WHERE s.plan_id = ? ORDER BY e.session_id, e.position""",
        (plan_id,),
    ).fetchall()
    by_session: dict[int, list] = {}
    for e in exercises:
        by_session.setdefault(e["session_id"], []).append({
            **{k: e[k] for k in EXERCISE_FIELDS},
            "circuit": e["name"].startswith(CIRCUIT_PREFIX),
        })
    out_sessions = [{
        "id": s["id"], "week": s["week"], "day_index": s["day_index"],
        "scheduled_for": s["scheduled_for"], "kind": s["kind"], "title": s["title"],
        "focus": s["focus"], "duration_minutes": s["duration_minutes"],
        "completed": bool(s["completed"]), "completed_at": s["completed_at"],
        "exercises": by_session.get(s["id"], []),
    } for s in sessions]
    done = sum(1 for s in out_sessions if s["completed"])
    return {
        "id": plan["id"], "goal": plan["goal"], "experience_level": plan["experience_level"],
        "weeks": plan["weeks"], "days_per_week": plan["days_per_week"],
        "intensity": plan["intensity"], "notes": json.loads(plan["notes"]),
        "start_date": plan["start_date"], "status": plan["status"],
        "created_at": plan["created_at"],
        "sessions_total": len(out_sessions), "sessions_completed": done,
        "sessions": out_sessions,
    }


# ---- profile -------------------------------------------------------------------
@plans_bp.get("/profile")
@login_required
def get_profile():
    row = get_db().execute("SELECT * FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()
    return jsonify({"profile": _profile_json(row) if row else None})


@plans_bp.put("/profile")
@login_required
def put_profile():
    p = validate_profile(json_body())
    db = get_db()
    db.execute(
        """INSERT INTO profiles (user_id, age, weight_kg, height_cm, experience_level, goal,
               days_per_week, session_minutes, equipment, has_heavy_bag, avoid_body_parts,
               plan_weeks, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
               age=excluded.age, weight_kg=excluded.weight_kg, height_cm=excluded.height_cm,
               experience_level=excluded.experience_level, goal=excluded.goal,
               days_per_week=excluded.days_per_week, session_minutes=excluded.session_minutes,
               equipment=excluded.equipment, has_heavy_bag=excluded.has_heavy_bag,
               avoid_body_parts=excluded.avoid_body_parts, plan_weeks=excluded.plan_weeks,
               updated_at=excluded.updated_at""",
        (g.user["id"], p["age"], p["weight_kg"], p["height_cm"], p["experience_level"], p["goal"],
         p["days_per_week"], p["session_minutes"], p["equipment"], int(p["has_heavy_bag"]),
         ",".join(p["avoid_body_parts"]), p["plan_weeks"], utcnow()),
    )
    db.commit()
    row = db.execute("SELECT * FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()
    return jsonify({"profile": _profile_json(row)})


# ---- plans ---------------------------------------------------------------------
@plans_bp.post("/plans")
@login_required
def create_plan():
    db = get_db()
    prow = db.execute("SELECT * FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()
    if prow is None:
        raise ApiError("Complete your profile before generating a plan.", 400)
    profile = _profile_json(prow)
    intensity = feedback_intensity(db, g.user["id"])
    plan = get_recommender().generate(profile, intensity=intensity, start=date.today())
    plan_id = save_plan(db, g.user["id"], plan, date.today())
    return jsonify({"plan": _load_plan(db, plan_id, g.user["id"])}), 201


def save_plan(db, user_id: int, plan: dict, start: date) -> int:
    """Store a generated plan as the user's active plan and archive any other."""
    db.execute("UPDATE training_plans SET status = 'archived' WHERE user_id = ? AND status = 'active'", (user_id,))
    cur = db.execute(
        """INSERT INTO training_plans (user_id, goal, experience_level, weeks, days_per_week,
               intensity, notes, seed, start_date, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
        (user_id, plan["goal"], plan["experience_level"], plan["weeks"], plan["days_per_week"],
         plan["intensity"], json.dumps(plan["notes"]), plan["seed"], start.isoformat(), utcnow()),
    )
    plan_id = cur.lastrowid
    for s in plan["sessions"]:
        scur = db.execute(
            """INSERT INTO training_sessions (plan_id, week, day_index, scheduled_for, kind, title,
                   focus, duration_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (plan_id, s["week"], s["day_index"], s["scheduled_for"], s["kind"], s["title"],
             s["focus"], s["duration_minutes"]),
        )
        db.executemany(
            """INSERT INTO session_exercises (session_id, position, name, kind, exercise_type, body_part,
                   equipment, description, sets, reps, duration_seconds, rest_seconds, notes,
                   difficulty, match_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(scur.lastrowid, pos, e["name"], e["kind"], e.get("exercise_type"), e.get("body_part"),
              e.get("equipment"), e.get("description"), e.get("sets"), e.get("reps"),
              e.get("duration_seconds"), e.get("rest_seconds"), e.get("notes"),
              e.get("difficulty"), e.get("match_score"))
             for pos, e in enumerate(s["exercises"])],
        )
    db.commit()
    return plan_id


@plans_bp.get("/plans")
@login_required
def list_plans():
    rows = get_db().execute(
        """SELECT p.id, p.goal, p.experience_level, p.weeks, p.days_per_week, p.status, p.created_at,
                  COUNT(s.id) AS sessions_total, COALESCE(SUM(s.completed), 0) AS sessions_completed
           FROM training_plans p LEFT JOIN training_sessions s ON s.plan_id = p.id
           WHERE p.user_id = ? GROUP BY p.id ORDER BY p.id DESC""",
        (g.user["id"],),
    ).fetchall()
    return jsonify({"plans": [dict(r) for r in rows]})


@plans_bp.get("/plans/current")
@login_required
def current_plan():
    db = get_db()
    row = db.execute(
        "SELECT id FROM training_plans WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (g.user["id"],),
    ).fetchone()
    return jsonify({"plan": _load_plan(db, row["id"], g.user["id"]) if row else None})


@plans_bp.get("/plans/<int:plan_id>")
@login_required
def get_plan(plan_id: int):
    return jsonify({"plan": _load_plan(get_db(), plan_id, g.user["id"])})


# ---- sessions / feedback ---------------------------------------------------------
@plans_bp.post("/sessions/<int:session_id>/complete")
@login_required
def complete_session(session_id: int):
    data = validate_completion(json_body())
    db = get_db()
    row = db.execute(
        """SELECT s.id, s.completed FROM training_sessions s
           JOIN training_plans p ON p.id = s.plan_id
           WHERE s.id = ? AND p.user_id = ?""",
        (session_id, g.user["id"]),
    ).fetchone()
    if row is None:
        raise ApiError("Session not found.", 404)
    if row["completed"]:
        raise ApiError("This session is already marked as completed.", 409)
    now = utcnow()
    db.execute("UPDATE training_sessions SET completed = 1, completed_at = ? WHERE id = ?", (now, session_id))
    db.execute(
        "INSERT INTO feedback (user_id, session_id, rating, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (g.user["id"], session_id, data["rating"], data["notes"], now),
    )
    db.commit()
    return jsonify({
        "message": "Session completed.",
        "next_plan_intensity": feedback_intensity(db, g.user["id"]),
    })


@plans_bp.delete("/sessions/<int:session_id>/complete")
@login_required
def undo_complete(session_id: int):
    """Take back an accidental completion, including its rating."""
    db = get_db()
    row = db.execute(
        """SELECT s.id FROM training_sessions s JOIN training_plans p ON p.id = s.plan_id
           WHERE s.id = ? AND p.user_id = ? AND s.completed = 1""",
        (session_id, g.user["id"]),
    ).fetchone()
    if row is None:
        raise ApiError("Session not found.", 404)
    db.execute("UPDATE training_sessions SET completed = 0, completed_at = NULL WHERE id = ?", (session_id,))
    db.execute("DELETE FROM feedback WHERE session_id = ? AND user_id = ?", (session_id, g.user["id"]))
    db.commit()
    return jsonify({"message": "Session reopened.", "next_plan_intensity": feedback_intensity(db, g.user["id"])})


# ---- swapping exercises ----------------------------------------------------------
@plans_bp.post("/exercises/<int:exercise_id>/swap")
@login_required
def swap_exercise(exercise_id: int):
    """Replace a gym exercise everywhere it is still to come in the active plan.

    The same exercise repeats each week, so swapping one occurrence alone would
    bring it straight back. Completed sessions keep what was actually done.
    """
    db = get_db()
    target = db.execute(
        """SELECT e.name, e.kind AS exercise_kind, e.body_part, s.kind AS session_kind, s.completed,
                  p.id AS plan_id, p.goal, p.experience_level, p.intensity, p.status
           FROM session_exercises e
           JOIN training_sessions s ON s.id = e.session_id
           JOIN training_plans p ON p.id = s.plan_id
           WHERE e.id = ? AND p.user_id = ?""",
        (exercise_id, g.user["id"]),
    ).fetchone()
    if target is None:
        raise ApiError("Exercise not found.", 404)
    if target["exercise_kind"] != "gym":
        raise ApiError("Only gym exercises can be swapped.", 400)
    if target["completed"] or target["status"] != "active":
        raise ApiError("This session can no longer be changed.", 409)

    plan_id = target["plan_id"]
    prow = db.execute("SELECT * FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()
    # Current equipment and injuries apply, but the plan keeps its own goal and level.
    profile = {**_profile_json(prow), "goal": target["goal"], "experience_level": target["experience_level"]}
    in_plan = {r["name"] for r in db.execute(
        """SELECT DISTINCT e.name FROM session_exercises e
           JOIN training_sessions s ON s.id = e.session_id WHERE s.plan_id = ?""", (plan_id,))}
    recommender = get_recommender()
    row = recommender.alternative(profile, target["session_kind"], target["body_part"], in_plan)
    if row is None:
        raise ApiError("No other exercise fits your equipment for this body part.", 409)

    occurrences = db.execute(
        """SELECT e.id, e.session_id, s.week FROM session_exercises e
           JOIN training_sessions s ON s.id = e.session_id
           WHERE s.plan_id = ? AND s.completed = 0 AND e.name = ?""",
        (plan_id, target["name"]),
    ).fetchall()
    for occ in occurrences:
        new = recommender._prescribe(row, profile, target["intensity"], week_factor(occ["week"]))
        db.execute(
            """UPDATE session_exercises SET name = ?, exercise_type = ?, body_part = ?, equipment = ?,
                   description = ?, sets = ?, reps = ?, duration_seconds = ?, rest_seconds = ?,
                   notes = ?, difficulty = ?, match_score = ? WHERE id = ?""",
            (new["name"], new["exercise_type"], new["body_part"], new["equipment"], new["description"],
             new["sets"], new["reps"], new["duration_seconds"], new["rest_seconds"], new["notes"],
             new["difficulty"], new["match_score"], occ["id"]),
        )
    for session_id in {occ["session_id"] for occ in occurrences}:
        rows = db.execute("SELECT * FROM session_exercises WHERE session_id = ?", (session_id,)).fetchall()
        db.execute(
            "UPDATE training_sessions SET duration_minutes = ? WHERE id = ?",
            (estimate_minutes([dict(r) for r in rows]), session_id),
        )
    db.commit()
    return jsonify({"plan": _load_plan(db, plan_id, g.user["id"]), "replacement": row["Title"]})


# ---- stats -------------------------------------------------------------------------
def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_streak(days: list[date], today: date) -> int:
    """Consecutive calendar weeks with at least one session.

    The current week doesn't break a streak until it has passed: on a Monday
    morning you shouldn't lose a streak you can still extend today.
    """
    weeks = {_monday(d) for d in days}
    week = _monday(today)
    if week not in weeks:
        week -= timedelta(days=7)
    streak = 0
    while week in weeks:
        streak += 1
        week -= timedelta(days=7)
    return streak


@plans_bp.get("/stats")
@login_required
def stats():
    db = get_db()
    user_id = g.user["id"]
    done = db.execute(
        """SELECT s.completed_at, s.duration_minutes FROM training_sessions s
           JOIN training_plans p ON p.id = s.plan_id
           WHERE p.user_id = ? AND s.completed = 1""",
        (user_id,),
    ).fetchall()
    rounds = db.execute(
        """SELECT COALESCE(SUM(e.sets), 0) FROM session_exercises e
           JOIN training_sessions s ON s.id = e.session_id
           JOIN training_plans p ON p.id = s.plan_id
           WHERE p.user_id = ? AND s.completed = 1 AND e.kind = 'boxing'""",
        (user_id,),
    ).fetchone()[0]
    ratings = db.execute(
        """SELECT f.rating, f.created_at, s.title FROM feedback f
           LEFT JOIN training_sessions s ON s.id = f.session_id
           WHERE f.user_id = ? ORDER BY f.id DESC LIMIT 12""",
        (user_id,),
    ).fetchall()

    today = date.today()
    days = [datetime.fromisoformat(r["completed_at"]).astimezone().date() for r in done]
    minutes_by_week: dict[date, list[int]] = {}
    for day, row in zip(days, done):
        minutes_by_week.setdefault(_monday(day), []).append(row["duration_minutes"] or 0)
    this_week = _monday(today)
    weeks = [this_week - timedelta(days=7 * i) for i in range(STATS_WEEKS - 1, -1, -1)]
    recent = [r["rating"] for r in ratings[:FEEDBACK_WINDOW]]
    return jsonify({
        "sessions": len(done),
        "minutes": sum(r["duration_minutes"] or 0 for r in done),
        "rounds": rounds,
        "week_streak": week_streak(days, today),
        "sessions_this_week": len(minutes_by_week.get(this_week, [])),
        "by_week": [{
            "week_start": w.isoformat(),
            "sessions": len(minutes_by_week.get(w, [])),
            "minutes": sum(minutes_by_week.get(w, [])),
        } for w in weeks],
        "ratings": [
            {"rating": r["rating"], "date": r["created_at"][:10], "title": r["title"]}
            for r in reversed(ratings)
        ],
        "average_rating": round(sum(recent) / len(recent), 2) if recent else None,
        "next_plan_intensity": feedback_intensity(db, user_id),
    })


# ---- progress ----------------------------------------------------------------------
@plans_bp.get("/progress")
@login_required
def list_progress():
    rows = get_db().execute(
        "SELECT id, date, metric, value FROM progress WHERE user_id = ? ORDER BY date, id",
        (g.user["id"],),
    ).fetchall()
    return jsonify({"progress": [dict(r) for r in rows]})


@plans_bp.post("/progress")
@login_required
def add_progress():
    data = validate_progress(json_body())
    db = get_db()
    cur = db.execute(
        "INSERT INTO progress (user_id, date, metric, value, created_at) VALUES (?, ?, ?, ?, ?)",
        (g.user["id"], data["date"], data["metric"], data["value"], utcnow()),
    )
    db.commit()
    return jsonify({"entry": {"id": cur.lastrowid, **data}}), 201


@plans_bp.delete("/progress/<int:entry_id>")
@login_required
def delete_progress(entry_id: int):
    db = get_db()
    cur = db.execute("DELETE FROM progress WHERE id = ? AND user_id = ?", (entry_id, g.user["id"]))
    db.commit()
    if cur.rowcount == 0:
        raise ApiError("Entry not found.", 404)
    return jsonify({"message": "Entry deleted."})
