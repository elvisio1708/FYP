"""Training plan generation.

How a plan is built
-------------------
1. The user's profile picks a weekly *split* (which kind of session on which day).
2. Boxing sessions come from rule-based templates (``boxing.py``).
3. Gym sessions are filled slot by slot (e.g. "a chest exercise", "a hamstring
   exercise") from the exercise dataset. Each candidate is scored:

       score = 0.50 * goal_fit + 0.35 * level_fit + 0.15 * rating

   * goal_fit  - how well the exercise *type* suits the user's goal.
   * level_fit - how close the model's difficulty score is to the user's
                 experience level (see ``difficulty_model.difficulty_score``).
   * rating    - dataset rating if it has one, otherwise a neutral 0.5.

   The top candidates are sampled (weighted by score) so plans have variety but
   stay sensible. Equipment, avoided body parts and the user's experience level
   are hard filters, not soft preferences.
4. Sets, reps and rest come from the goal/level; ``intensity`` (derived from the
   user's session feedback) scales volume for gym work and rest for boxing.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from . import boxing
from . import difficulty_model as dm

GOALS = ("strength", "fat_loss", "boxing", "general")
LEVELS = ("beginner", "intermediate", "advanced")
EQUIPMENT = ("bodyweight", "home", "full_gym")
SESSION_MINUTES = (30, 45, 60)

BODY_PARTS = (
    "Abdominals", "Abductors", "Adductors", "Biceps", "Calves", "Chest",
    "Forearms", "Glutes", "Hamstrings", "Lats", "Lower Back", "Middle Back",
    "Neck", "Quadriceps", "Shoulders", "Traps", "Triceps",
)

_HOME = {"Body Only", "Dumbbell", "Kettlebells", "Bands", "Medicine Ball", "Exercise Ball", "Foam Roll"}
EQUIPMENT_ALLOWED = {
    "bodyweight": {"Body Only"},
    "home": _HOME,
    "full_gym": None,  # None = everything
}

# Weekly split per goal; the first N entries are used for N days per week.
SPLITS = {
    "strength": ["gym_upper", "gym_lower", "gym_full", "gym_upper", "gym_lower", "gym_full"],
    "fat_loss": ["gym_full", "boxing_hiit", "gym_full", "boxing_hiit", "gym_full", "gym_mobility"],
    "boxing": ["boxing_technique", "gym_boxing", "boxing_bag", "boxing_hiit", "gym_boxing", "boxing_footwork"],
    "general": ["gym_full", "boxing_technique", "gym_full", "gym_mobility", "boxing_hiit", "gym_upper"],
}

DAY_PATTERNS = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5]}

# Body-part slots to fill for each gym session kind.
SLOTS = {
    "gym_upper": [["Chest"], ["Lats", "Middle Back"], ["Shoulders"], ["Biceps"], ["Triceps"], ["Chest", "Shoulders"], ["Middle Back", "Traps"]],
    "gym_lower": [["Quadriceps"], ["Hamstrings"], ["Glutes"], ["Calves"], ["Abdominals"], ["Quadriceps", "Glutes"], ["Lower Back"]],
    "gym_full": [["Quadriceps"], ["Chest"], ["Lats", "Middle Back"], ["Hamstrings", "Glutes"], ["Shoulders"], ["Abdominals"], ["Triceps", "Biceps"]],
    "gym_boxing": [["Quadriceps", "Glutes", "Hamstrings"], ["Shoulders"], ["Lats", "Middle Back"], ["Abdominals"], ["Hamstrings", "Glutes"], ["Triceps"], ["Abdominals", "Lower Back"]],
    "gym_mobility": [["Shoulders"], ["Hamstrings"], ["Quadriceps"], ["Lower Back"], ["Glutes"], ["Chest"], ["Lats", "Middle Back"]],
}
SLOT_COUNT = {30: 5, 45: 6, 60: 7}  # upper bound; _fit_time trims to the user's minutes

GYM_TITLES = {
    "gym_upper": ("Upper body", "Push and pull strength"),
    "gym_lower": ("Lower body", "Legs, glutes and core"),
    "gym_full": ("Full body", "Whole-body training"),
    "gym_boxing": ("Strength and power for boxing", "Explosive legs, shoulders and core"),
    "gym_mobility": ("Mobility and recovery", "Stretching and flexibility"),
}

# How well each dataset exercise Type suits each goal (0-1).
TYPE_FIT = {
    "strength": {"Strength": 1.0, "Powerlifting": 0.9, "Olympic Weightlifting": 0.6, "Strongman": 0.5, "Plyometrics": 0.3, "Cardio": 0.2},
    "fat_loss": {"Plyometrics": 1.0, "Cardio": 1.0, "Strength": 0.8, "Olympic Weightlifting": 0.5, "Strongman": 0.5, "Powerlifting": 0.4},
    "boxing": {"Plyometrics": 1.0, "Strength": 0.8, "Cardio": 0.8, "Olympic Weightlifting": 0.5, "Strongman": 0.4, "Powerlifting": 0.4},
    "general": {"Strength": 1.0, "Cardio": 0.7, "Plyometrics": 0.6, "Powerlifting": 0.4, "Olympic Weightlifting": 0.3, "Strongman": 0.3},
}
# Target on the model's 0-2 difficulty scale. Beginners aim above zero because
# the very bottom of the scale is stretches and fully supported machine work.
LEVEL_TARGET = {"beginner": 0.5, "intermediate": 1.0, "advanced": 1.5}
BEGINNER_MAX_DIFFICULTY = 1.3  # hard limit, like the Olympic lift rule below

# (sets, reps, rest seconds) for strength-type exercises
PRESCRIPTION = {
    "strength": {"beginner": (3, 8, 90), "intermediate": (4, 6, 120), "advanced": (4, 5, 150)},
    "fat_loss": {"beginner": (3, 12, 45), "intermediate": (3, 12, 45), "advanced": (4, 12, 40)},
    "boxing": {"beginner": (3, 8, 60), "intermediate": (3, 8, 60), "advanced": (4, 6, 60)},
    "general": {"beginner": (3, 10, 60), "intermediate": (3, 10, 60), "advanced": (4, 8, 75)},
}
WEEK_FACTOR = [1.0, 1.1, 1.2, 0.85]  # week 4 of every block is a lighter week
CARDIO_MINUTES = {"beginner": 8, "intermediate": 10, "advanced": 12}


class Recommender:
    def __init__(self, exercises: pd.DataFrame, model):
        df = exercises.copy()
        df["difficulty"] = dm.difficulty_score(model, df)
        self.df = df

    # ---- candidate selection -------------------------------------------------
    def _pool(self, profile: dict, kind: str) -> pd.DataFrame:
        df = self.df
        allowed = EQUIPMENT_ALLOWED[profile["equipment"]]
        if allowed is not None:
            df = df[df["Equipment"].isin(allowed)]
        if profile.get("avoid_body_parts"):
            df = df[~df["BodyPart"].isin(profile["avoid_body_parts"])]
        if kind == "gym_mobility":
            df = df[df["Type"] == "Stretching"]
        else:
            df = df[df["Type"] != "Stretching"]
            if profile["experience_level"] == "beginner":
                # Technical / high-injury-risk lifts are not suggested to beginners.
                df = df[~df["Type"].isin(["Olympic Weightlifting", "Strongman"])]
                df = df[df["difficulty"] <= BEGINNER_MAX_DIFFICULTY]
        return df

    def _score(self, cand: pd.DataFrame, profile: dict, kind: str) -> pd.Series:
        if kind == "gym_mobility":
            goal_fit = pd.Series(1.0, index=cand.index)
        else:
            goal_fit = cand["Type"].map(TYPE_FIT[profile["goal"]]).fillna(0.2)
        target = LEVEL_TARGET[profile["experience_level"]]
        level_fit = (1 - (cand["difficulty"] - target).abs()).clip(lower=0.05)
        rating = (cand["Rating"] / 10).fillna(0.5)
        return 0.5 * goal_fit + 0.35 * level_fit + 0.15 * rating

    def _pick(self, pool, parts, profile, kind, used, rng):
        cand = pool[pool["BodyPart"].isin(parts)]
        fresh = cand[~cand["Title"].isin(used)]
        if not fresh.empty:
            cand = fresh
        if cand.empty:
            return None
        scores = self._score(cand, profile, kind).sort_values(ascending=False).head(8)
        weights = np.square(scores.values) + 1e-6
        idx = rng.choices(list(scores.index), weights=list(weights), k=1)[0]
        row = cand.loc[idx].copy()
        row["match_score"] = float(scores[idx])
        return row

    def _select_gym_exercises(self, profile, kind, used, rng):
        pool = self._pool(profile, kind)
        n = SLOT_COUNT[profile["session_minutes"]]
        picked = []
        for parts in SLOTS[kind]:
            if len(picked) >= n:
                break
            row = self._pick(pool, parts, profile, kind, used, rng)
            if row is not None:
                picked.append(row)
                used.add(row["Title"])
        return picked

    def alternative(self, profile: dict, kind: str, body_part: str, exclude: set[str], seed: int | None = None):
        """Another exercise for the same body part, or None if there isn't one."""
        pool = self._pool(profile, kind)
        pool = pool[~pool["Title"].isin(exclude)]
        return self._pick(pool, [body_part], profile, kind, set(), random.Random(seed))

    # ---- prescription --------------------------------------------------------
    @staticmethod
    def _prescribe(row, profile, intensity, week_factor) -> dict:
        goal, level = profile["goal"], profile["experience_level"]
        t = row["Type"]
        reps = duration = None
        if t == "Stretching":
            sets, duration, rest = 2, 30, 15
            note = "Hold each stretch; breathe slowly and don't bounce."
        elif t == "Cardio":
            sets, duration, rest = 1, CARDIO_MINUTES[level] * 60, 0
            note = "Steady pace you could hold a conversation at."
        elif t == "Plyometrics":
            sets, reps, rest = 3, max(4, round(6 * week_factor)), 60
            sets = max(2, round(sets * intensity))
            note = "Explosive but controlled. Stop the set if your landing gets sloppy."
        else:
            base_sets, base_reps, base_rest = PRESCRIPTION[goal][level]
            sets = max(2, round(base_sets * intensity))
            reps = max(3, round(base_reps * week_factor))
            # Harder = shorter rest, so the extra volume still fits the session time.
            rest = int(min(180, max(30, 5 * round(base_rest / max(intensity, 0.5) / 5))))
            note = "Pick a weight that leaves 1-2 reps in reserve."
        return {
            "name": row["Title"],
            "kind": "gym",
            "exercise_type": t,
            "body_part": row["BodyPart"],
            "equipment": row["Equipment"],
            "description": shorten(row["Desc"] or ""),
            "sets": int(sets),
            "reps": int(reps) if reps else None,
            "duration_seconds": int(duration) if duration else None,
            "rest_seconds": int(rest),
            "notes": note,
            "difficulty": round(float(row["difficulty"]), 3),
            "match_score": round(float(row["match_score"]), 3),
        }

    # ---- plan ----------------------------------------------------------------
    def generate(self, profile: dict, intensity: float = 1.0, start: date | None = None, seed: int | None = None) -> dict:
        start = start or date.today()
        seed = int(seed if seed is not None else random.SystemRandom().randrange(1 << 30))
        rng = random.Random(seed)
        days = profile["days_per_week"]
        split = SPLITS[profile["goal"]][:days]
        offsets = DAY_PATTERNS[days]
        used: set[str] = set()

        # Choose each gym day's exercises once so they stay the same across weeks.
        gym_choice = {}
        for i, kind in enumerate(split):
            if kind.startswith("gym_"):
                gym_choice[i] = self._select_gym_exercises(profile, kind, used, rng)

        sessions = []
        for week in range(1, profile["plan_weeks"] + 1):
            wf = week_factor(week)
            box_intensity = intensity * (1 + (wf - 1) / 2)
            for i, kind in enumerate(split):
                if kind.startswith("gym_"):
                    title, focus = GYM_TITLES[kind]
                    exercises = (
                        boxing.warmup() if kind != "gym_mobility" else []
                    ) + [self._prescribe(r, profile, intensity, wf) for r in gym_choice[i]]
                    exercises = self._fit_time(exercises, profile["session_minutes"])
                    if kind != "gym_mobility":
                        exercises += boxing.cooldown()
                else:
                    title, focus, exercises = boxing.build_boxing_session(
                        kind, profile["experience_level"], profile["session_minutes"],
                        box_intensity, week, profile["has_heavy_bag"],
                    )
                sessions.append({
                    "week": week,
                    "day_index": i,
                    "scheduled_for": (start + timedelta(days=7 * (week - 1) + offsets[i])).isoformat(),
                    "kind": kind,
                    "title": title,
                    "focus": focus,
                    "duration_minutes": estimate_minutes(exercises),
                    "exercises": exercises,
                })

        notes = []
        if profile["plan_weeks"] >= 4:
            notes.append("Week 4 of each block is deliberately lighter so you can recover.")
        if not profile["has_heavy_bag"] and {"boxing_technique", "boxing_bag"} & set(split):
            notes.append("No heavy bag in your profile, so bag rounds are done as shadowboxing.")
        if profile.get("avoid_body_parts"):
            notes.append("Avoiding: " + ", ".join(profile["avoid_body_parts"]) + ".")
        if abs(intensity - 1.0) > 0.01:
            direction = "harder" if intensity > 1 else "easier"
            notes.append(f"Adjusted {direction} based on your recent session feedback.")
        return {
            "seed": seed,
            "goal": profile["goal"],
            "experience_level": profile["experience_level"],
            "weeks": profile["plan_weeks"],
            "days_per_week": days,
            "intensity": round(intensity, 2),
            "notes": notes,
            "sessions": sessions,
        }

    @staticmethod
    def _fit_time(exercises: list[dict], minutes: int) -> list[dict]:
        """Drop trailing exercises until the session fits the user's time."""
        reserve = boxing.COOLDOWN_MIN
        while len(exercises) > 3 and estimate_minutes(exercises) + reserve > minutes:
            exercises = exercises[:-1]
        return exercises


def shorten(text: str, limit: int = 400) -> str:
    """Trim long dataset descriptions at a sentence end, not mid-word."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = cut.rfind(". ")
    return cut[: end + 1] if end > 0 else cut.rsplit(" ", 1)[0] + "…"


def week_factor(week: int) -> float:
    return WEEK_FACTOR[(week - 1) % len(WEEK_FACTOR)]


def estimate_minutes(exercises: list[dict]) -> int:
    total = 0
    for ex in exercises:
        sets = ex.get("sets") or 1
        rest = ex.get("rest_seconds") or 0
        if ex.get("duration_seconds"):
            total += sets * (ex["duration_seconds"] + rest)
        else:
            total += sets * ((ex.get("reps") or 10) * 4 + rest)  # ~4 s per rep
    return int(round(total / 60))


@lru_cache(maxsize=1)
def get_recommender() -> Recommender:
    """Build the recommender once per process (loads or trains the model)."""
    return Recommender(dm.load_exercises(), dm.load_or_train())
