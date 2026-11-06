"""Stats, swapping, undo, account management, lockout, validation edge cases."""
import sqlite3
from datetime import date

import pytest

from app.auth import MAX_FAILED_LOGINS
from app.plans import week_streak

PASSWORD = "correct-horse-1"


def with_plan(c, profile, **overrides):
    assert c.put("/api/profile", json={**profile, **overrides}).status_code == 200
    r = c.post("/api/plans", json={})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["plan"]


def gym_exercise(plan):
    for s in plan["sessions"]:
        for e in s["exercises"]:
            if e["kind"] == "gym":
                return s, e
    raise AssertionError("plan has no gym exercise")


# ------------------------------------------------------------ validation --------
@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", True, [], {}])
def test_rating_rejects_non_numbers_without_crashing(make_user, profile, bad):
    c = make_user()
    plan = with_plan(c, profile)
    r = c.post(f"/api/sessions/{plan['sessions'][0]['id']}/complete", json={"rating": bad})
    assert r.status_code == 400


@pytest.mark.parametrize("metric,value", [("weight_kg", 5), ("waist_cm", 500), ("body_fat_pct", 90)])
def test_progress_rejects_implausible_values(make_user, metric, value):
    assert make_user().post("/api/progress", json={"metric": metric, "value": value}).status_code == 400


# ---------------------------------------------------------- plan contents --------
def test_gym_exercises_explain_their_selection(make_user, profile):
    _, e = gym_exercise(with_plan(make_user(), profile, goal="strength"))
    assert 0 <= e["difficulty"] <= 2
    assert 0 < e["match_score"] <= 1


def test_hiit_stations_are_flagged_as_a_circuit(make_user, profile):
    plan = with_plan(make_user(), profile)
    hiit = next(s for s in plan["sessions"] if s["kind"] == "boxing_hiit")
    assert sum(e["circuit"] for e in hiit["exercises"]) == 5


def test_heavy_bag_note_only_when_plan_has_bag_rounds(make_user, profile):
    plan = with_plan(make_user(), profile, goal="fat_loss")
    assert not any("heavy bag" in n.lower() for n in plan["notes"])


# --------------------------------------------------------------- swapping --------
def test_swap_replaces_all_upcoming_occurrences_only(make_user, profile):
    c = make_user()
    plan = with_plan(c, profile, goal="strength")
    session, exercise = gym_exercise(plan)
    assert c.post(f"/api/sessions/{session['id']}/complete", json={"rating": 3}).status_code == 200

    later = next(
        e for s in plan["sessions"] if s["id"] != session["id"]
        for e in s["exercises"] if e["name"] == exercise["name"]
    )
    r = c.post(f"/api/exercises/{later['id']}/swap", json={})
    assert r.status_code == 200
    body = r.get_json()
    assert body["replacement"] != exercise["name"]

    sessions = body["plan"]["sessions"]
    done = next(s for s in sessions if s["id"] == session["id"])
    assert exercise["name"] in [e["name"] for e in done["exercises"]]
    for s in sessions:
        if s["id"] != session["id"]:
            assert exercise["name"] not in [e["name"] for e in s["exercises"]]


def test_swap_respects_equipment_and_body_part(make_user, profile):
    c = make_user()
    plan = with_plan(c, profile, goal="strength", equipment="bodyweight")
    _, exercise = gym_exercise(plan)
    plan = c.post(f"/api/exercises/{exercise['id']}/swap", json={}).get_json()["plan"]
    _, replaced = next(
        (s, e) for s in plan["sessions"] for e in s["exercises"] if e["id"] == exercise["id"]
    )
    assert replaced["equipment"] == "Body Only"
    assert replaced["body_part"] == exercise["body_part"]


def test_cannot_swap_boxing_completed_or_other_users_exercises(make_user, profile):
    owner, other = make_user(), make_user()
    plan = with_plan(owner, profile, goal="strength")
    session, exercise = gym_exercise(plan)
    warmup = session["exercises"][0]
    assert owner.post(f"/api/exercises/{warmup['id']}/swap", json={}).status_code == 400
    assert other.post(f"/api/exercises/{exercise['id']}/swap", json={}).status_code == 404
    owner.post(f"/api/sessions/{session['id']}/complete", json={"rating": 3})
    assert owner.post(f"/api/exercises/{exercise['id']}/swap", json={}).status_code == 409


# ------------------------------------------------------------------- undo --------
def test_undo_reopens_session_and_removes_its_rating(make_user, profile):
    c = make_user()
    sid = with_plan(c, profile)["sessions"][0]["id"]
    r = c.post(f"/api/sessions/{sid}/complete", json={"rating": 5})
    assert r.get_json()["next_plan_intensity"] == 0.8
    r = c.delete(f"/api/sessions/{sid}/complete")
    assert r.get_json()["next_plan_intensity"] == 1.0
    assert c.get("/api/stats").get_json()["sessions"] == 0
    assert c.post(f"/api/sessions/{sid}/complete", json={"rating": 3}).status_code == 200


def test_undo_is_scoped_to_owner(make_user, profile):
    owner, other = make_user(), make_user()
    sid = with_plan(owner, profile)["sessions"][0]["id"]
    owner.post(f"/api/sessions/{sid}/complete", json={"rating": 3})
    assert other.delete(f"/api/sessions/{sid}/complete").status_code == 404


# ------------------------------------------------------------------ stats --------
def test_stats_empty(make_user):
    s = make_user().get("/api/stats").get_json()
    assert (s["sessions"], s["minutes"], s["rounds"], s["week_streak"]) == (0, 0, 0, 0)
    assert s["average_rating"] is None and s["next_plan_intensity"] == 1.0
    assert len(s["by_week"]) == 8


def test_stats_counts_completed_work(make_user, profile):
    c = make_user()
    session = with_plan(c, profile)["sessions"][0]  # boxing technique
    c.post(f"/api/sessions/{session['id']}/complete", json={"rating": 2})
    s = c.get("/api/stats").get_json()
    rounds = sum(e["sets"] for e in session["exercises"] if e["kind"] == "boxing")
    assert s["sessions"] == 1 and s["sessions_this_week"] == 1 and s["week_streak"] == 1
    assert s["minutes"] == session["duration_minutes"]
    assert s["rounds"] == rounds > 0
    assert s["ratings"][-1]["rating"] == 2 and s["ratings"][-1]["title"] == session["title"]
    assert s["by_week"][-1]["sessions"] == 1


@pytest.mark.parametrize("days,expected", [
    ([], 0),
    ([date(2026, 11, 4)], 1),                                        # this week
    ([date(2026, 10, 28)], 1),                                       # last week still counts
    ([date(2026, 10, 21)], 0),                                       # a full week was missed
    ([date(2026, 11, 2), date(2026, 10, 28), date(2026, 10, 20)], 3),
    ([date(2026, 11, 2), date(2026, 11, 3), date(2026, 10, 20)], 1),  # gap breaks it
])
def test_week_streak(days, expected):
    assert week_streak(days, date(2026, 11, 6)) == expected


# --------------------------------------------------------------- progress --------
def test_delete_progress_is_scoped_to_owner(make_user):
    owner, other = make_user(), make_user()
    entry = owner.post("/api/progress", json={"metric": "weight_kg", "value": 72}).get_json()["entry"]
    assert other.delete(f"/api/progress/{entry['id']}").status_code == 404
    assert owner.delete(f"/api/progress/{entry['id']}").status_code == 200
    assert owner.get("/api/progress").get_json()["progress"] == []


# ---------------------------------------------------------------- account --------
def login(client, username, password):
    return client.post("/api/login", json={"username": username, "password": password})


def test_login_locks_after_repeated_failures(client, make_user):
    make_user("boxer")
    for _ in range(MAX_FAILED_LOGINS):
        assert login(client, "boxer", "wrong-password").status_code == 401
    assert login(client, "boxer", "wrong-password").status_code == 429
    assert login(client, "BOXER", PASSWORD).status_code == 429  # even the right password
    assert login(client, "someone_else", "wrong-password").status_code == 401


def test_successful_login_clears_failures(client, make_user):
    make_user("boxer")
    for _ in range(MAX_FAILED_LOGINS - 1):
        login(client, "boxer", "wrong-password")
    assert login(client, "boxer", PASSWORD).status_code == 200
    assert login(client, "boxer", "wrong-password").status_code == 401
    assert login(client, "boxer", PASSWORD).status_code == 200


def test_change_password(client, make_user):
    c = make_user("boxer")
    body = {"current_password": "nope", "new_password": "another-good-1"}
    assert c.put("/api/account/password", json=body).status_code == 403
    assert c.put("/api/account/password", json={"current_password": PASSWORD, "new_password": "short"}).status_code == 400
    assert c.put("/api/account/password", json={**body, "current_password": PASSWORD}).status_code == 200
    assert login(client, "boxer", PASSWORD).status_code == 401
    assert login(client, "boxer", "another-good-1").status_code == 200


def test_delete_account_removes_everything(app, client, make_user, profile):
    c = make_user("boxer")
    with_plan(c, profile)
    assert c.delete("/api/account", json={"password": "wrong"}).status_code == 403
    assert c.get("/api/me").status_code == 200
    assert c.delete("/api/account", json={"password": PASSWORD}).status_code == 200
    assert c.get("/api/me").status_code == 401
    assert login(client, "boxer", PASSWORD).status_code == 401
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    for table in ("users", "profiles", "training_plans", "training_sessions", "session_exercises"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


# --------------------------------------------------------------- database --------
def test_old_database_gets_new_columns(tmp_path):
    from app import create_app

    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE session_exercises (id INTEGER PRIMARY KEY, session_id INTEGER, name TEXT)")
    conn.commit()
    conn.close()
    create_app({"TESTING": True, "DATABASE_PATH": str(path)})
    columns = {r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(session_exercises)")}
    assert {"difficulty", "match_score"} <= columns


def test_security_headers(client):
    headers = client.get("/api/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


# ------------------------------------------------------------- dataset text --------
def test_long_descriptions_end_cleanly():
    from app.services.recommender import shorten

    assert shorten("Short.") == "Short."
    assert shorten("One sentence. " * 50).endswith("sentence.")
    assert len(shorten("One sentence. " * 50)) <= 400
    assert shorten("word " * 200).endswith("word…")


def test_titles_have_no_trailing_hyphens():
    from app.services.difficulty_model import load_exercises

    assert not load_exercises()["Title"].str.endswith("-").any()


# --------------------------------------------------------------- difficulty --------
@pytest.fixture(scope="module")
def recommender():
    from app.services.recommender import get_recommender

    return get_recommender()


def test_publisher_tags_are_removed_before_scoring():
    from app.services.difficulty_rules import clean_title, has_publisher_prefix

    assert clean_title("HM Downward-Facing Dog Pose") == "Downward-Facing Dog Pose"
    assert clean_title("Hack Squat - Gethin Variation") == "Hack Squat"
    assert has_publisher_prefix("Holman Deadlift to Squat Thrust")
    assert not has_publisher_prefix("Upright Row")  # a word, not the "UP" tag
    assert clean_title("Upright Row") == "Upright Row"


def test_a_prefixed_rows_default_label_earns_no_points():
    from app.services.difficulty_rules import difficulty_points

    args = ("Strength", "Dumbbell")
    assert difficulty_points("Hold", *args, "Beginner") < difficulty_points("HM Hold", *args, "Beginner")


def test_model_orders_judgement_pairs(recommender):
    """Regression guard on the trained model. Honest numbers come from ml/train.py."""
    import json

    from app.services.difficulty_model import PAIRS_PATH

    d = recommender.df.set_index("Title")["difficulty"]
    pairs = json.loads(PAIRS_PATH.read_text())
    pairs = pairs["development"] + pairs["held_out"]
    correct = sum(d[easy] < d[hard] for easy, hard in pairs)
    assert correct / len(pairs) >= 0.9


@pytest.mark.parametrize("equipment", ["bodyweight", "home", "full_gym"])
def test_beginners_never_get_the_hardest_exercises(recommender, profile, equipment):
    from app.services.recommender import BEGINNER_MAX_DIFFICULTY

    for goal in ("strength", "boxing", "fat_loss", "general"):
        plan = recommender.generate({**profile, "goal": goal, "equipment": equipment, "days_per_week": 6}, seed=3)
        gym = [e for s in plan["sessions"] for e in s["exercises"] if e["kind"] == "gym"]
        assert gym, "the cap must not empty the session"
        assert max(e["difficulty"] for e in gym) <= BEGINNER_MAX_DIFFICULTY


def test_harder_levels_get_harder_exercises(recommender, profile):
    def mean_difficulty(level):
        values = [
            e["difficulty"]
            for seed in range(8)
            for s in recommender.generate(
                {**profile, "goal": "strength", "equipment": "full_gym", "experience_level": level}, seed=seed
            )["sessions"]
            for e in s["exercises"] if e["kind"] == "gym"
        ]
        return sum(values) / len(values)

    assert mean_difficulty("beginner") < mean_difficulty("intermediate") < mean_difficulty("advanced")
