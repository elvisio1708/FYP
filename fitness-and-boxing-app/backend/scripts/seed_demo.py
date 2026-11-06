"""Create a local demo account with about a month of sample training history.

    python scripts/seed_demo.py           # creates the account
    python scripts/seed_demo.py --reset   # deletes it first, then recreates it

For demos only. All of the history is made up, and the password below is
public, so never run this against a deployed database.
"""
import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from app.db import get_db, utcnow  # noqa: E402
from app.plans import save_plan  # noqa: E402
from app.services.recommender import get_recommender  # noqa: E402

USERNAME = "demo"
PASSWORD = "secondsout"
WEEKS_AGO = 4

PROFILE = {
    "age": 24, "weight_kg": 78.0, "height_cm": 178.0, "experience_level": "intermediate",
    "goal": "boxing", "days_per_week": 4, "session_minutes": 45, "equipment": "full_gym",
    "has_heavy_bag": True, "avoid_body_parts": [], "plan_weeks": 8,
}


def seed(db, rng) -> None:
    cur = db.execute(
        "INSERT INTO users (username, email, password_hash, date_joined) VALUES (?, ?, ?, ?)",
        (USERNAME, "demo@example.com", generate_password_hash(PASSWORD), utcnow()),
    )
    user_id = cur.lastrowid
    db.execute(
        """INSERT INTO profiles (user_id, age, weight_kg, height_cm, experience_level, goal, days_per_week,
               session_minutes, equipment, has_heavy_bag, avoid_body_parts, plan_weeks, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)""",
        (user_id, PROFILE["age"], PROFILE["weight_kg"], PROFILE["height_cm"], PROFILE["experience_level"],
         PROFILE["goal"], PROFILE["days_per_week"], PROFILE["session_minutes"], PROFILE["equipment"],
         int(PROFILE["has_heavy_bag"]), PROFILE["plan_weeks"], utcnow()),
    )

    today = date.today()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=WEEKS_AGO)
    plan = get_recommender().generate(PROFILE, start=start, seed=2026)
    plan_id = save_plan(db, user_id, plan, start)

    past = db.execute(
        "SELECT id, scheduled_for FROM training_sessions WHERE plan_id = ? AND scheduled_for < ? ORDER BY scheduled_for",
        (plan_id, today.isoformat()),
    ).fetchall()
    for session in past:
        if rng.random() < 0.1:  # the odd missed session, like real life
            continue
        when = datetime.combine(date.fromisoformat(session["scheduled_for"]), time(18, 30), timezone.utc)
        stamp = when.isoformat(timespec="seconds")
        db.execute("UPDATE training_sessions SET completed = 1, completed_at = ? WHERE id = ?", (stamp, session["id"]))
        db.execute(
            "INSERT INTO feedback (user_id, session_id, rating, content, created_at) VALUES (?, ?, ?, '', ?)",
            (user_id, session["id"], rng.choice([2, 3, 3, 3, 4]), stamp),
        )

    for weeks_back in range(WEEKS_AGO + 2, -1, -1):
        day = (today - timedelta(weeks=weeks_back)).isoformat()
        weight = 80.4 - (WEEKS_AGO + 2 - weeks_back) * 0.35 + rng.uniform(-0.15, 0.15)
        waist = 86.5 - (WEEKS_AGO + 2 - weeks_back) * 0.3 + rng.uniform(-0.1, 0.1)
        for metric, value in (("weight_kg", weight), ("waist_cm", waist)):
            db.execute(
                "INSERT INTO progress (user_id, date, metric, value, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, day, metric, round(value, 1), utcnow()),
            )
    db.commit()


def main() -> None:
    with create_app().app_context():
        db = get_db()
        db.execute("PRAGMA foreign_keys = ON")
        exists = db.execute("SELECT id FROM users WHERE username = ?", (USERNAME,)).fetchone()
        if exists and "--reset" not in sys.argv:
            print(f"'{USERNAME}' already exists. Use --reset to recreate it.")
            return
        if exists:
            db.execute("DELETE FROM users WHERE id = ?", (exists["id"],))
        seed(db, random.Random(7))
        print(f"Demo account ready. Username: {USERNAME}  Password: {PASSWORD}")


if __name__ == "__main__":
    main()
