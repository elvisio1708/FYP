"""Exercise difficulty model.

Learns a continuous difficulty score for every exercise in the gym dataset.

Why not just predict the dataset's Level column? An earlier version did, and on
hand-written easy/hard pairs it was worse than a coin flip, because the labels do
not measure difficulty (see ``difficulty_rules.py``). This version uses weak
supervision: coaching rules plus the label as one noisy vote produce a target
score, and a ridge regression learns that score from the exercise's cleaned title,
type, body part and equipment. The learner carries the rules over to exercises no
rule matches, and smooths the rules' hard edges.

Deliberately not used as features (each would flatter the numbers for a bad reason):
  * Publisher prefixes, which reveal the source rather than the difficulty.
  * Descriptions and ratings: 76% of Beginner rows have no description and 69% have
    a rating, against 49% and 19% of Intermediate rows, so whether one exists mostly
    reveals which source a row came from.

~65% of ratings are missing. They are left as NaN and never imputed, so a made-up
average can't leak into the recommender's ranking.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .difficulty_rules import clean_title, difficulty_points, has_publisher_prefix

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BACKEND_DIR / "data" / "megaGymDataset.csv"
PAIRS_PATH = BACKEND_DIR / "data" / "judgement_pairs.json"
MODEL_PATH = BACKEND_DIR / "models" / "exercise_difficulty_v2.joblib"
METRICS_PATH = BACKEND_DIR / "models" / "metrics.json"

LEVELS = ["Beginner", "Intermediate", "Expert"]  # ordinal order
CATEGORICAL = ["Type", "BodyPart", "Equipment"]
FEATURES = ["name"] + CATEGORICAL
POINTS_CLIP = 3.0     # rule points beyond this add nothing
POINTS_PER_LEVEL = 2  # two rule points = one step on the 0-2 difficulty scale
HIDDEN_FAMILIES = ("snatch", "pistol", "muscle.?up", "clap", "stretch", "machine")


def load_exercises(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load and clean the raw dataset. Ratings are deliberately not imputed."""
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    # Some titles end in a stray hyphen ("Jumping jack-").
    df["Title"] = df["Title"].astype(str).str.strip().str.rstrip("- ")
    df = df[df["Title"] != ""]
    df = df.drop_duplicates(subset="Title", keep="first")
    df["Desc"] = df["Desc"].fillna("")
    for col in CATEGORICAL:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()
    df["text"] = (df["Title"] + ". " + df["Desc"]).str.strip()
    df["name"] = df["Title"].map(clean_title)
    # Ratings stay NaN when missing; 0.0 in this dataset means "no rating yet".
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df.loc[df["Rating"] <= 0, "Rating"] = np.nan
    return df.reset_index(drop=True)


def target_points(df: pd.DataFrame) -> pd.Series:
    points = [
        difficulty_points(r.Title, r.Type, r.Equipment, r.Level)
        for r in df[["Title", "Type", "Equipment", "Level"]].itertuples()
    ]
    return pd.Series(points, index=df.index).clip(-POINTS_CLIP, POINTS_CLIP)


def _features(text_column: str, max_features: int) -> ColumnTransformer:
    return ColumnTransformer([
        ("text", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=max_features, sublinear_tf=True), text_column),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])


def build_pipeline() -> Pipeline:
    return Pipeline([("features", _features("name", 6000)), ("reg", Ridge(alpha=1.0))])


def build_label_baseline() -> Pipeline:
    """The first version of the model, kept only as the comparison in evaluate()."""
    clf = LogisticRegression(class_weight="balanced", max_iter=3000, C=2.0, random_state=42)
    return Pipeline([("features", _features("text", 4000)), ("clf", clf)])


def _expected_level(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    weights = np.array([LEVELS.index(c) for c in model.classes_], dtype=float)
    return model.predict_proba(X) @ weights


def _score_pairs(scores: dict, pairs: list) -> dict:
    usable = [(easy, hard) for easy, hard in pairs if easy in scores and hard in scores]
    correct = int(sum(scores[easy] < scores[hard] for easy, hard in usable))
    return {"correct": correct, "total": len(usable), "percent": round(100 * correct / len(usable), 1)}


def evaluate(df: pd.DataFrame, n_splits: int = 5) -> dict:
    """Compare old and new on out-of-fold scores.

    Exercises sharing a description stay in the same fold, so a duplicate can't
    be seen in training and then scored. The headline is the held-out judgement
    pairs: label accuracy can't rank the models when the labels are the problem.
    """
    pairs = json.loads(PAIRS_PATH.read_text())
    groups = df["Desc"].where(df["Desc"] != "", df["Title"].str.lower())
    points = target_points(df)
    folds = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)

    new_scores = np.zeros(len(df))
    old_scores = np.zeros(len(df))
    old_labels = np.empty(len(df), dtype=object)
    for train, test in folds.split(df, df["Level"], groups):
        fit, held = df.iloc[train], df.iloc[test]
        new_scores[test] = build_pipeline().fit(fit[FEATURES], points.iloc[train]).predict(held[FEATURES])
        old = build_label_baseline().fit(fit[["text"] + CATEGORICAL], fit["Level"])
        old_scores[test] = _expected_level(old, held[["text"] + CATEGORICAL])
        old_labels[test] = old.predict(held[["text"] + CATEGORICAL])

    def compare(which: str) -> dict:
        return {
            "old_model": _score_pairs(dict(zip(df["Title"], old_scores)), pairs[which]),
            "rules_only": _score_pairs(dict(zip(df["Title"], points)), pairs[which]),
            "new_model": _score_pairs(dict(zip(df["Title"], new_scores)), pairs[which]),
        }

    labels = dict(zip(df["Title"], df["Level"].map(LEVELS.index)))
    all_pairs = [(e, h) for e, h in pairs["development"] + pairs["held_out"] if e in labels and h in labels]

    hidden = {}
    for family in HIDDEN_FAMILIES:
        mask = df["Title"].str.contains(family, case=False)
        model = build_pipeline().fit(df.loc[~mask, FEATURES], points[~mask])
        hidden[family] = {
            "rows": int(mask.sum()),
            "rule_points": round(float(points[mask].mean()), 2),
            "predicted_when_hidden": round(float(model.predict(df.loc[mask, FEATURES]).mean()), 2),
        }

    prefixed = df["Title"].map(has_publisher_prefix)
    rated = (~prefixed).to_numpy()
    return {
        "n_samples": int(len(df)),
        "class_counts": {k: int(v) for k, v in df["Level"].value_counts().items()},
        "publisher_prefixed_rows": int(prefixed.sum()),
        "cv_folds": n_splits,
        "judgement_pairs": {"held_out": compare("held_out"), "development": compare("development")},
        "dataset_labels_on_pairs": {
            "correct": int(sum(labels[e] < labels[h] for e, h in all_pairs)),
            "tied": int(sum(labels[e] == labels[h] for e, h in all_pairs)),
            "backwards": int(sum(labels[e] > labels[h] for e, h in all_pairs)),
        },
        "old_model_on_label_task": {
            "scope": "rows without a publisher prefix, duplicates kept in one fold",
            "accuracy": round(accuracy_score(df["Level"][rated], old_labels[rated]), 4),
            "balanced_accuracy": round(balanced_accuracy_score(df["Level"][rated], old_labels[rated]), 4),
        },
        "generalisation_family_hidden_from_training": {
            "mean_rule_points_all_rows": round(float(points.mean()), 2),
            "families": hidden,
        },
    }


def train_and_save(
    data_path: Path = DATA_PATH,
    model_path: Path = MODEL_PATH,
    metrics_path: Path = METRICS_PATH,
    run_eval: bool = True,
) -> Pipeline:
    df = load_exercises(data_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if run_eval:
        metrics_path.write_text(json.dumps(evaluate(df), indent=2))
    model = build_pipeline().fit(df[FEATURES], target_points(df))
    joblib.dump(model, model_path)
    return model


def load_or_train(model_path: Path = MODEL_PATH) -> Pipeline:
    """Load the saved model, retraining if it is missing or unreadable.

    Retraining takes a few seconds, so this keeps a fresh clone working even if
    the saved file was made with a different scikit-learn version.
    """
    if model_path.exists():
        try:
            return joblib.load(model_path)
        except Exception:  # noqa: BLE001 - any unpickling/version problem -> retrain
            pass
    return train_and_save(model_path=model_path, run_eval=False)


def difficulty_score(model: Pipeline, df: pd.DataFrame) -> np.ndarray:
    """Difficulty on a 0-2 scale (0 = very easy, 1 = moderate, 2 = very hard)."""
    return np.clip(1 + model.predict(df[FEATURES]) / POINTS_PER_LEVEL, 0, 2)
