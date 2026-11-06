"""Coaching knowledge used to label exercise difficulty (weak supervision).

The dataset's own Level column can't be trained on directly:

  * About 1,090 rows carry a publisher prefix ("Holman", "HM", "FYR2"...) and
    every one is "Intermediate", which looks like a default rather than a rating.
  * Olympic lifts are labelled Beginner 30 times out of 35.
  * On hand-written easy/hard pairs the labels get 2 of 28 right, tie on 16 and
    are backwards on 10 (see data/judgement_pairs.json).

So each exercise instead gets difficulty *points* from the rules below: movement
skill, single-limb work, explosive work, and how much a machine or support helps.
The dataset label counts as one small, noisy vote. A model then learns from these
points (see difficulty_model.py), which also smooths over exercises no rule covers.
"""
from __future__ import annotations

import re

PUBLISHER_PREFIXES = ("30", "am", "fyr", "fyr2", "hm", "holman", "metaburn", "tbs", "un", "uns", "up")
_PREFIX = re.compile(r"^(?:" + "|".join(PUBLISHER_PREFIXES) + r")\b\s*", re.I)
_VARIATION = re.compile(r"\s*-\s*gethin variation", re.I)

_HIGH_SKILL = re.compile(
    r"snatch|jerk|muscle.?up|handstand|pistol|kipping|planche|human flag|skin the cat|l-sit|lever|turkish"
    r"|windmill|overhead squat|depth jump|clap|dragon flag|atlas|log press|tire flip|yoke|sissy"
)
_DEMANDING = re.compile(
    r"\bclean\b|thruster|deadlift|back squat|front squat|good morning|weighted|explosive|jump|hop\b|bound"
    r"|burpee|sprint|single.?(arm|leg)|one.?(arm|leg)|renegade|bulgarian|\bdips?\b|pull.?up|chin.?up|swing"
    r"|\btrx\b|\brings?\b|suspension|bear crawl|plyo"
)
_RECOVERY = re.compile(r"stretch|foam roll|\bsmr\b|mobility|breathing|\bpose\b|assisted|massage")
_SIMPLE = re.compile(
    r"machine|seated|lying|wall sit|walking|\bwalk\b|\bjog\b|march|crunch|glute bridge|leg extension|leg curl"
    r"|leg press|pulldown|curl\b|calf raise|lateral raise|shrug|plank|bodyweight squat|band\b|banded|rotation"
)

TYPE_POINTS = {
    "Olympic Weightlifting": 2.0, "Strongman": 2.0, "Plyometrics": 1.0,
    "Powerlifting": 1.0, "Stretching": -2.0, "Cardio": -0.5,
}
EQUIPMENT_POINTS = {
    "Machine": -1.0, "Cable": -0.5, "Bands": -0.5, "Foam Roll": -1.5, "Barbell": 0.5, "Kettlebells": 0.25,
}
LABEL_POINTS = {"Beginner": -0.5, "Intermediate": 0.0, "Expert": 1.0}


def has_publisher_prefix(title: str) -> bool:
    return bool(_PREFIX.match(title))


def clean_title(title: str) -> str:
    """Drop publisher tags, which say who wrote an exercise and not how hard it is."""
    return _VARIATION.sub("", _PREFIX.sub("", title)).strip()


def difficulty_points(title: str, exercise_type: str, equipment: str, level: str) -> float:
    """Rule score: around -3 (very easy) to +3 (very hard), 0 for no strong signal."""
    name = clean_title(title).lower()
    points = TYPE_POINTS.get(exercise_type, 0.0) + EQUIPMENT_POINTS.get(equipment, 0.0)
    points += 2.0 * bool(_HIGH_SKILL.search(name)) + 1.0 * bool(_DEMANDING.search(name))
    points -= 2.0 * bool(_RECOVERY.search(name)) + 1.0 * bool(_SIMPLE.search(name))
    if not has_publisher_prefix(title):  # a prefixed row's label is only a default
        points += LABEL_POINTS.get(level, 0.0)
    return points
