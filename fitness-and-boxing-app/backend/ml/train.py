"""Train and evaluate the exercise difficulty model.

Run from the backend/ folder:

    python -m ml.train

Writes models/exercise_difficulty.joblib and models/metrics.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import difficulty_model as dm  # noqa: E402


def main() -> None:
    dm.train_and_save()
    metrics = json.loads(dm.METRICS_PATH.read_text())
    print(json.dumps(metrics, indent=2))
    print(f"\nSaved model   -> {dm.MODEL_PATH}")
    print(f"Saved metrics -> {dm.METRICS_PATH}")


if __name__ == "__main__":
    main()
