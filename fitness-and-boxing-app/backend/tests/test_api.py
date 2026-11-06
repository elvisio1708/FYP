import itertools

import pytest

from app.plans import feedback_intensity  # noqa: F401  (imported to ensure module loads)


def _setup_plan(client, profile):
    assert client.put("/api/profile", json=profile).status_code == 200
    r = client.post("/api/plans")
    assert r.status_code == 201, r.get_json()
    return r.get_json()["plan"]


# ---------------------------------------------------------------- auth ----------
def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


@pytest.mark.parametrize("payload,field", [
    ({"username": "ab", "email": "a@b.co", "password": "longenough1"}, "username"),
    ({"username": "valid_name", "email": "not-an-email", "password": "longenough1"}, "email"),
    ({"username": "valid_name", "email": "a@b.co", "password": "short"}, "password"),
])
def test_register_validation(client, payload, field):
    r = client.post("/api/register", json=payload)
    assert r.status_code == 400
    assert field in r.get_json()["fields"]


def test_register_rejects_non_json(client):
    assert client.post("/api/register", data="username=a").status_code == 400


def test_register_login_logout_flow(client):
    body = {"username": "Elvis", "email": "e@example.com", "password": "correct-horse-1"}
    assert client.post("/api/register", json=body).status_code == 201
    assert client.get("/api/me").get_json()["user"]["username"] == "Elvis"

    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401

    assert client.post("/api/login", json={"username": "Elvis", "password": "correct-horse-1"}).status_code == 200
    assert client.get("/api/me").status_code == 200


def test_register_duplicate_is_case_insensitive(client):
    body = {"username": "Elvis", "email": "e@example.com", "password": "correct-horse-1"}
    assert client.post("/api/register", json=body).status_code == 201
    other = {"username": "elvis", "email": "other@example.com", "password": "correct-horse-1"}
    assert client.post("/api/register", json=other).status_code == 409
    other = {"username": "someone", "email": "E@EXAMPLE.COM", "password": "correct-horse-1"}
    assert client.post("/api/register", json=other).status_code == 409


def test_login_failures_are_indistinguishable(client):
    client.post("/api/register", json={"username": "elvis", "email": "e@example.com", "password": "correct-horse-1"})
    wrong_pw = client.post("/api/login", json={"username": "elvis", "password": "nope-nope-nope"})
    no_user = client.post("/api/login", json={"username": "ghost", "password": "nope-nope-nope"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.get_json() == no_user.get_json()


def test_login_missing_fields(client):
    assert client.post("/api/login", json={}).status_code == 400


def test_password_is_hashed_and_never_returned(client, app):
    body = {"username": "elvis", "email": "e@example.com", "password": "correct-horse-1"}
    r = client.post("/api/register", json=body)
    assert "password" not in str(r.get_json())
    import sqlite3
    row = sqlite3.connect(app.config["DATABASE_PATH"]).execute("SELECT password_hash FROM users").fetchone()
    assert row[0] != "correct-horse-1" and row[0].startswith(("scrypt:", "pbkdf2:"))


@pytest.mark.parametrize("method,path", [
    ("get", "/api/me"), ("get", "/api/profile"), ("put", "/api/profile"), ("post", "/api/plans"),
    ("get", "/api/plans"), ("get", "/api/plans/current"), ("get", "/api/plans/1"),
    ("post", "/api/sessions/1/complete"), ("get", "/api/progress"), ("post", "/api/progress"),
])
def test_protected_routes_require_login(client, method, path):
    assert getattr(client, method)(path, json={}).status_code == 401


# ------------------------------------------------------------- profile ----------
def test_plan_requires_profile(make_user):
    c = make_user()
    r = c.post("/api/plans")
    assert r.status_code == 400 and "profile" in r.get_json()["error"].lower()


def test_profile_roundtrip(make_user, profile):
    c = make_user()
    assert c.get("/api/profile").get_json() == {"profile": None}
    profile["avoid_body_parts"] = ["Shoulders", "Lower Back"]
    assert c.put("/api/profile", json=profile).status_code == 200
    got = c.get("/api/profile").get_json()["profile"]
    assert got["goal"] == "boxing" and got["avoid_body_parts"] == ["Lower Back", "Shoulders"]
    profile["goal"] = "strength"  # update, not duplicate
    c.put("/api/profile", json=profile)
    assert c.get("/api/profile").get_json()["profile"]["goal"] == "strength"


@pytest.mark.parametrize("change,field", [
    ({"age": 5}, "age"), ({"weight_kg": "heavy"}, "weight_kg"), ({"goal": "become_a_wizard"}, "goal"),
    ({"experience_level": "god"}, "experience_level"), ({"days_per_week": 7}, "days_per_week"),
    ({"session_minutes": 50}, "session_minutes"), ({"equipment": "yacht"}, "equipment"),
    ({"avoid_body_parts": ["Elbows"]}, "avoid_body_parts"),
])
def test_profile_validation(make_user, profile, change, field):
    c = make_user()
    r = c.put("/api/profile", json={**profile, **change})
    assert r.status_code == 400 and field in r.get_json()["fields"]


# --------------------------------------------------------------- plans ----------
GOALS = ["strength", "fat_loss", "boxing", "general"]
LEVELS = ["beginner", "intermediate", "advanced"]


@pytest.mark.parametrize("goal,level", list(itertools.product(GOALS, LEVELS)))
def test_plan_generation_all_goals_and_levels(make_user, profile, goal, level):
    c = make_user()
    profile.update(goal=goal, experience_level=level, equipment="full_gym", session_minutes=60, days_per_week=5)
    plan = _setup_plan(c, profile)
    assert len(plan["sessions"]) == 4 * 5
    for s in plan["sessions"]:
        assert s["exercises"], s["title"]
        names = [e["name"] for e in s["exercises"] if e["kind"] == "gym"]
        assert len(names) == len(set(names)), "duplicate exercise within a session"
        assert s["duration_minutes"] <= profile["session_minutes"] + 5, (s["title"], s["duration_minutes"])


@pytest.mark.parametrize("minutes", [30, 45, 60])
@pytest.mark.parametrize("goal", GOALS)
def test_sessions_fit_requested_time(make_user, profile, goal, minutes):
    c = make_user()
    profile.update(goal=goal, session_minutes=minutes, equipment="full_gym", experience_level="intermediate")
    plan = _setup_plan(c, profile)
    for s in plan["sessions"]:
        assert s["duration_minutes"] <= minutes + 5, (s["title"], s["duration_minutes"], minutes)


@pytest.mark.parametrize("goal", GOALS)
def test_bodyweight_plans_use_no_equipment(make_user, profile, goal):
    c = make_user()
    profile.update(goal=goal, equipment="bodyweight")
    plan = _setup_plan(c, profile)
    gym = [e for s in plan["sessions"] for e in s["exercises"] if e["kind"] == "gym"]
    assert gym and all(e["equipment"] == "Body Only" for e in gym)


def test_avoided_body_parts_are_respected(make_user, profile):
    c = make_user()
    profile.update(goal="strength", equipment="full_gym", avoid_body_parts=["Shoulders", "Chest", "Lower Back"])
    plan = _setup_plan(c, profile)
    gym = [e for s in plan["sessions"] for e in s["exercises"] if e["kind"] == "gym"]
    assert gym and not {e["body_part"] for e in gym} & {"Shoulders", "Chest", "Lower Back"}


def test_beginners_get_no_olympic_or_strongman(make_user, profile):
    c = make_user()
    profile.update(goal="strength", equipment="full_gym", experience_level="beginner")
    plan = _setup_plan(c, profile)
    types = {e["exercise_type"] for s in plan["sessions"] for e in s["exercises"] if e["kind"] == "gym"}
    assert not types & {"Olympic Weightlifting", "Strongman"}


def test_no_heavy_bag_replaces_bag_rounds(make_user, profile):
    c = make_user()
    profile.update(goal="boxing", has_heavy_bag=False)
    plan = _setup_plan(c, profile)
    names = " ".join(e["name"] for s in plan["sessions"] for e in s["exercises"])
    assert "Heavy bag" not in names
    c2 = make_user()
    profile.update(has_heavy_bag=True)
    plan2 = _setup_plan(c2, profile)
    assert "Heavy bag" in " ".join(e["name"] for s in plan2["sessions"] for e in s["exercises"])


def test_week_four_is_a_lighter_week(make_user, profile):
    c = make_user()
    profile.update(goal="strength", equipment="full_gym", experience_level="intermediate", plan_weeks=4)
    plan = _setup_plan(c, profile)
    def total_reps(week):
        return sum((e["reps"] or 0) * (e["sets"] or 0) for s in plan["sessions"] if s["week"] == week for e in s["exercises"] if e["kind"] == "gym")
    assert total_reps(3) > total_reps(1) > total_reps(4)


def test_new_plan_archives_previous(make_user, profile):
    c = make_user()
    first = _setup_plan(c, profile)
    second = c.post("/api/plans").get_json()["plan"]
    assert second["id"] != first["id"]
    assert c.get(f"/api/plans/{first['id']}").get_json()["plan"]["status"] == "archived"
    assert c.get("/api/plans/current").get_json()["plan"]["id"] == second["id"]
    assert len(c.get("/api/plans").get_json()["plans"]) == 2


def test_users_cannot_see_each_others_plans(make_user, profile):
    a, b = make_user(), make_user()
    plan = _setup_plan(a, profile)
    assert b.get(f"/api/plans/{plan['id']}").status_code == 404
    assert b.get("/api/plans").get_json()["plans"] == []
    assert b.get("/api/plans/current").get_json()["plan"] is None


# ----------------------------------------------------- completion + feedback ----
def test_complete_session_flow(make_user, profile):
    c = make_user()
    plan = _setup_plan(c, profile)
    sid = plan["sessions"][0]["id"]
    assert c.post(f"/api/sessions/{sid}/complete", json={"rating": 9}).status_code == 400
    assert c.post(f"/api/sessions/{sid}/complete", json={}).status_code == 400
    r = c.post(f"/api/sessions/{sid}/complete", json={"rating": 3, "notes": "felt good"})
    assert r.status_code == 200 and r.get_json()["next_plan_intensity"] == 1.0
    assert c.post(f"/api/sessions/{sid}/complete", json={"rating": 3}).status_code == 409
    got = c.get(f"/api/plans/{plan['id']}").get_json()["plan"]
    assert got["sessions_completed"] == 1 and got["sessions"][0]["completed"] is True


def test_cannot_complete_someone_elses_session(make_user, profile):
    a, b = make_user(), make_user()
    plan = _setup_plan(a, profile)
    assert b.post(f"/api/sessions/{plan['sessions'][0]['id']}/complete", json={"rating": 3}).status_code == 404


@pytest.mark.parametrize("rating,direction", [(5, "lower"), (1, "higher"), (3, "same")])
def test_feedback_changes_next_plan_intensity(make_user, profile, rating, direction):
    c = make_user()
    profile.update(goal="strength", equipment="full_gym", experience_level="intermediate")
    plan = _setup_plan(c, profile)
    for s in plan["sessions"][:3]:
        c.post(f"/api/sessions/{s['id']}/complete", json={"rating": rating})
    new = c.post("/api/plans").get_json()["plan"]
    if direction == "lower":
        assert new["intensity"] < 1.0
    elif direction == "higher":
        assert new["intensity"] > 1.0
    else:
        assert new["intensity"] == 1.0
    assert any("feedback" in n for n in new["notes"]) == (direction != "same")


@pytest.mark.parametrize("intensity", [0.8, 0.9, 1.1, 1.2])
def test_intensity_scales_the_same_exercises(profile, intensity):
    """Same seed => same exercises; intensity must only change how they're prescribed."""
    from app.services.recommender import get_recommender
    rec = get_recommender()
    profile.update(goal="strength", equipment="full_gym", experience_level="intermediate", avoid_body_parts=[])
    base = rec.generate(profile, intensity=1.0, seed=11)
    adj = rec.generate(profile, intensity=intensity, seed=11)

    def week1(p):
        return {e["name"]: e for s in p["sessions"] if s["week"] == 1 for e in s["exercises"]
                if e["kind"] == "gym" and e["exercise_type"] not in ("Stretching", "Cardio", "Plyometrics")}
    b, a = week1(base), week1(adj)
    shared = set(b) & set(a)
    assert shared
    for name in shared:
        if intensity > 1:
            assert a[name]["sets"] >= b[name]["sets"] and a[name]["rest_seconds"] <= b[name]["rest_seconds"]
        else:
            assert a[name]["sets"] <= b[name]["sets"] and a[name]["rest_seconds"] >= b[name]["rest_seconds"]


def test_same_seed_gives_same_plan(profile):
    from app.services.recommender import get_recommender
    rec = get_recommender()
    profile.update(equipment="full_gym")
    assert rec.generate(profile, seed=5) == rec.generate(profile, seed=5)
    assert rec.generate(profile, seed=5) != rec.generate(profile, seed=6)


def test_model_makes_beginner_plans_easier_than_advanced(profile):
    """The difficulty model should steer exercise choice by experience level."""
    from app.services.recommender import get_recommender
    rec = get_recommender()
    d = rec.df.set_index("Title")["difficulty"]
    profile.update(goal="general", equipment="full_gym", session_minutes=60, days_per_week=5)

    def mean_difficulty(level):
        vals = []
        for seed in range(10):
            plan = rec.generate({**profile, "experience_level": level}, seed=seed)
            vals += [d[e["name"]] for s in plan["sessions"] for e in s["exercises"] if e["kind"] == "gym" and e["name"] in d.index]
        return sum(vals) / len(vals)

    assert mean_difficulty("beginner") < mean_difficulty("intermediate") - 0.1


def test_intensity_is_clamped(make_user, profile):
    c = make_user()
    plan = _setup_plan(c, profile)
    for s in plan["sessions"][:6]:
        r = c.post(f"/api/sessions/{s['id']}/complete", json={"rating": 5})
    assert r.get_json()["next_plan_intensity"] == 0.8


# ------------------------------------------------------------- progress ---------
def test_progress(make_user):
    c = make_user()
    assert c.post("/api/progress", json={"metric": "weight_kg", "value": 72.5, "date": "2026-11-01"}).status_code == 201
    assert c.post("/api/progress", json={"metric": "weight_kg", "value": 71.9, "date": "2026-11-08"}).status_code == 201
    entries = c.get("/api/progress").get_json()["progress"]
    assert [e["value"] for e in entries] == [72.5, 71.9]
    assert c.post("/api/progress", json={"metric": "shoe_size", "value": 9}).status_code == 400
    assert c.post("/api/progress", json={"metric": "weight_kg", "value": 70, "date": "yesterday"}).status_code == 400
    other = make_user()
    assert other.get("/api/progress").get_json()["progress"] == []


def test_unknown_api_route_returns_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and "error" in r.get_json()


# ----------------------------------------------------- built frontend serving ---
def test_serves_built_frontend_and_blocks_traversal(tmp_path, monkeypatch):
    import app as app_module
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("top secret")
    monkeypatch.setattr(app_module, "FRONTEND_DIST", dist)
    c = app_module.create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "t.db")}).test_client()

    assert b"spa" in c.get("/").data
    assert b"console.log" in c.get("/assets/app.js").data
    assert b"spa" in c.get("/some/client/route").data          # SPA fallback
    assert c.get("/api/nope").get_json() == {"error": "Not found."}  # API 404 stays JSON
    for evil in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt"):
        assert b"top secret" not in c.get(evil).data, evil
