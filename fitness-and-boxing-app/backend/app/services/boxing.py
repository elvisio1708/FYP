"""Rule-based boxing session templates.

The gym dataset has no boxing content, so boxing sessions are built from
templates. They are time-boxed: the number of rounds is computed from the
user's session length, and the *rest* between rounds is what flexes with
feedback (shorter rest = harder), so a session never overruns the time the
user said they have.
"""
from __future__ import annotations

from typing import Callable

WARMUP_MIN = 5
COOLDOWN_MIN = 5
CIRCUIT_PREFIX = "Circuit: "  # stations sharing this prefix repeat as one loop

# (round length s, base rest s) per experience level
ROUND_FORMAT = {
    "beginner": (120, 60),
    "intermediate": (180, 60),
    "advanced": (180, 45),
}

# Combination "curriculum" per level. Each week of a plan moves one step along,
# so week 2 is not just a copy of week 1.
COMBOS = {
    "beginner": [
        "Jab, jab (1-1)",
        "Jab, cross (1-2)",
        "Jab, cross, step back",
        "1-2 then slip right",
    ],
    "intermediate": [
        "Jab, cross, lead hook (1-2-3)",
        "1-2, slip, cross",
        "Jab to the body, jab to the head, cross",
        "1-2-3, pivot out",
    ],
    "advanced": [
        "1-2-3-2 with a feint to start",
        "Slip, roll under, hook-cross counter",
        "Jab, check hook, step out, 1-2",
        "6-punch flow: 1-2-3-2-3-2, defence between every 2 punches",
    ],
}

DEFENCE = {
    "beginner": ["Slip left and right", "Guard up, step back out of range"],
    "intermediate": ["Slip and roll under (U-shape)", "Parry the jab, counter with a cross"],
    "advanced": ["Slip-roll-counter chains", "Shoulder roll and pull counter"],
}


def _rest_seconds(level: str, intensity: float) -> int:
    """Shorter rest at higher intensity, clamped to a sensible 30-90 s, 5 s steps."""
    base = ROUND_FORMAT[level][1]
    rest = base / max(intensity, 0.5)
    return int(min(90, max(30, 5 * round(rest / 5))))


def _split(total: int, fractions: list[float]) -> list[int]:
    """Split ``total`` rounds by ``fractions``; every part gets at least 1."""
    raw = [max(1, round(total * f)) for f in fractions]
    # Trim or pad so the parts always sum to total (largest part absorbs the diff).
    diff = total - sum(raw)
    raw[raw.index(max(raw))] += diff
    return [max(1, r) for r in raw]


def _ex(name, description, rounds, work, rest, kind="boxing", notes=""):
    return {
        "name": name,
        "kind": kind,
        "body_part": "Full body",
        "equipment": "None",
        "description": description,
        "sets": int(rounds),
        "reps": None,
        "duration_seconds": int(work),
        "rest_seconds": int(rest),
        "notes": notes,
    }


def warmup() -> list[dict]:
    return [
        {
            "name": "Skipping / light jog on the spot",
            "kind": "warmup",
            "body_part": "Full body",
            "equipment": "None",
            "description": "Easy pace to raise your heart rate.",
            "sets": 1,
            "reps": None,
            "duration_seconds": 3 * 60,
            "rest_seconds": 0,
            "notes": "",
        },
        {
            "name": "Dynamic mobility",
            "kind": "warmup",
            "body_part": "Full body",
            "equipment": "None",
            "description": "Arm circles, torso rotations, hip openers, leg swings.",
            "sets": 1,
            "reps": None,
            "duration_seconds": 2 * 60,
            "rest_seconds": 0,
            "notes": "",
        },
    ]


def cooldown() -> list[dict]:
    return [
        {
            "name": "Cool-down stretch",
            "kind": "cooldown",
            "body_part": "Full body",
            "equipment": "None",
            "description": "Shoulders, chest, hips, calves and neck. Slow breathing.",
            "sets": 1,
            "reps": None,
            "duration_seconds": COOLDOWN_MIN * 60,
            "rest_seconds": 0,
            "notes": "",
        }
    ]


def _budget_rounds(minutes: int, level: str, rest: int) -> tuple[int, int, int]:
    work = ROUND_FORMAT[level][0]
    budget = (minutes - WARMUP_MIN - COOLDOWN_MIN) * 60
    rounds = max(3, budget // (work + rest))
    return rounds, work, rest


def technique(level, minutes, intensity, week, has_bag):
    rest = _rest_seconds(level, intensity)
    total, work, rest = _budget_rounds(minutes, level, rest)
    combos = COMBOS[level]
    combo = combos[(week - 1) % len(combos)]
    shadow, drills, finish = _split(total, [0.3, 0.4, 0.3])
    finish_name = "Heavy bag rounds" if has_bag else "Shadowboxing rounds (power)"
    ex = [
        _ex("Shadowboxing", "Stance, guard and footwork. Light and relaxed, focus on form.", shadow, work, rest),
        _ex(
            f"Combination drill: {combo}",
            "Repeat the combination slowly, then build speed. Reset your guard after every combo.",
            drills, work, rest,
            notes="Technique before power.",
        ),
        _ex(
            finish_name,
            f"Throw the week's combination ({combo}) with intent. Stay balanced and move after punching.",
            finish, work, rest,
        ),
    ]
    return "Boxing technique", "Fundamentals and combinations", ex


def bag(level, minutes, intensity, week, has_bag):
    rest = _rest_seconds(level, intensity)
    total, work, rest = _budget_rounds(minutes, level, rest)
    shadow, main = _split(total, [0.2, 0.8])
    combos = COMBOS[level]
    combo = combos[(week - 1) % len(combos)]
    if has_bag:
        main_ex = _ex(
            "Heavy bag rounds",
            f"Work {combo}, then free-flow. Last 30 seconds of each round: increase pace.",
            main, work, rest,
        )
    else:
        main_ex = _ex(
            "Shadowboxing rounds (no bag)",
            f"Work {combo}, then free-flow. Visualise an opponent and exhale on every punch.",
            main, work, rest,
            notes="No heavy bag in your profile, so these replace bag rounds.",
        )
    ex = [_ex("Shadowboxing warm-up rounds", "Loosen up before hitting hard.", shadow, work, rest), main_ex]
    return "Bag work", "Power, rhythm and endurance", ex


def footwork(level, minutes, intensity, week, has_bag):
    rest = _rest_seconds(level, intensity)
    total, work, rest = _budget_rounds(minutes, level, rest)
    foot, defn, shadow = _split(total, [0.4, 0.4, 0.2])
    defence = DEFENCE[level][(week - 1) % len(DEFENCE[level])]
    ex = [
        _ex("Footwork drills", "Step-drag forward/back/left/right, pivots, and circling. Stay on the balls of your feet.", foot, work, rest),
        _ex(f"Defence: {defence}", "Slow, then at speed. Keep your hands up while you move your head.", defn, work, rest),
        _ex("Shadowboxing with movement", "Combine punches with the footwork and defence you just drilled.", shadow, work, rest),
    ]
    return "Footwork and defence", "Movement and defence", ex


def hiit(level, minutes, intensity, week, has_bag):
    # Interval format (30-45 s on, 20-30 s off) rather than full rounds.
    on = {"beginner": 30, "intermediate": 40, "advanced": 45}[level]
    off = int(min(40, max(15, 5 * round((on / 2) / max(intensity, 0.5) / 5))))
    budget = (minutes - WARMUP_MIN - COOLDOWN_MIN) * 60
    stations = [
        ("Skipping", "Steady rope pace. Replace with high knees if you have no rope."),
        ("Shadowboxing sprints", "Fast 1-2s and hooks with your feet moving."),
        ("Burpees (or squat thrusts)", "Controlled pace, land softly."),
        ("Mountain climbers", "Hips level, fast feet."),
        ("Squat jumps (or fast bodyweight squats)", "Chest up, soft landings."),
    ]
    per_round = len(stations) * (on + off)
    # Cap total rounds by level so a long session doesn't become an overly hard one.
    cap = {"beginner": 5, "intermediate": 7, "advanced": 9}[level]
    rounds = min(cap, max(2, budget // per_round))
    ex = [
        _ex(
            f"{CIRCUIT_PREFIX}{name}",
            desc,
            rounds, on, off,
            kind="boxing",
            notes=f"Station {i + 1} of {len(stations)}. Do all stations in order, then repeat for {rounds} rounds.",
        )
        for i, (name, desc) in enumerate(stations)
    ]
    return "Boxing HIIT", "Conditioning and fat burning", ex


SESSION_BUILDERS: dict[str, Callable] = {
    "boxing_technique": technique,
    "boxing_bag": bag,
    "boxing_footwork": footwork,
    "boxing_hiit": hiit,
}


def build_boxing_session(kind, level, minutes, intensity, week, has_bag):
    """Return (title, focus, exercises) for a boxing session kind."""
    title, focus, body = SESSION_BUILDERS[kind](level, minutes, intensity, week, has_bag)
    return title, focus, warmup() + body + cooldown()
