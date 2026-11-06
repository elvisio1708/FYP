import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402

PROFILE = {
    "age": 24,
    "weight_kg": 72,
    "height_cm": 178,
    "experience_level": "beginner",
    "goal": "boxing",
    "days_per_week": 4,
    "session_minutes": 45,
    "equipment": "home",
    "has_heavy_bag": False,
    "avoid_body_parts": [],
    "plan_weeks": 4,
}


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE_PATH": str(tmp_path / "test.db")})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    """Factory: returns a logged-in test client for a fresh user."""
    counter = {"n": 0}

    def _make(username=None):
        counter["n"] += 1
        c = app.test_client()
        name = username or f"user{counter['n']}"
        r = c.post("/api/register", json={"username": name, "email": f"{name}@example.com", "password": "correct-horse-1"})
        assert r.status_code == 201, r.get_json()
        return c

    return _make


@pytest.fixture()
def profile():
    return dict(PROFILE)
