# Seconds Out: AI-Powered Fitness & Boxing Training Plan App

A full-stack web app that builds personalised fitness and boxing training plans. Built as my final year project at the Technological University of the Shannon.

You create an account, answer a short setup wizard (goal, experience, equipment, time available, injuries to avoid), and the app generates a multi-week plan. You train with a built-in round timer, rate how each session felt, and the next plan adjusts to that feedback.

## Features

- **Round timer:** a full-screen guided workout with synthesised bells, work and rest phases, a 10-second warning and circuits that loop through their stations. It uses the wall clock, so a background tab can't make a round run long. It also keeps the screen awake and works from the keyboard (Space, arrow keys, Esc).
- **Today dashboard:** the session that matters now, this week at a glance, streak and totals, and how your ratings will change the next plan. Recent misses become a catch-up; old ones stop blocking the schedule.
- **Explained recommendations:** gym exercises show the model's difficulty rating and their match score.
- **Exercise swap:** replaces an exercise everywhere it is still to come, respecting your equipment and injuries.
- **Progress:** sessions per week, rating trend and body measurements, with hover detail.
- **Account controls:** password change, account deletion, and lockout after repeated failed logins.

## How it works

| Layer | Tech |
|---|---|
| Frontend | Vue 3 + Vite, Vue Router |
| Backend | Python, Flask, SQLite (`sqlite3`) |
| ML | scikit-learn, pandas |
| Auth | Flask signed session cookie, `werkzeug` password hashing |

**Plan generation** (`backend/app/services/`):

1. The goal and days per week pick a weekly split (e.g. technique / strength / bag work / conditioning).
2. **Boxing sessions** are built from rule-based templates (rounds, combinations, footwork, defence, HIIT). The number of rounds is calculated from the session length, so a session never overruns the time you have.
3. **Gym sessions** are filled from the [gym exercise dataset](fitness-and-boxing-app/backend/data/megaGymDataset.csv) (2,909 unique exercises). Every candidate exercise is scored `0.50 × goal fit + 0.35 × level fit + 0.15 × rating`. Equipment, avoided body parts and the beginner safety rule (no Olympic lifts or strongman for beginners) are hard filters.
4. **The ML part:** coaching rules score each exercise on skill, single-limb and explosive work, and machine support, with the dataset's own label as one small vote. A scikit-learn model (TF-IDF on the cleaned title + one-hot type/body part/equipment → ridge regression) learns those scores, giving a 0–2 difficulty for every exercise. The planner prefers exercises close to the user's level, and beginners have a hard cap.
5. **Feedback loop:** the last 6 session ratings (1 = too easy … 5 = too hard) set an intensity multiplier (0.8–1.2). It changes sets and rest for gym work and rest between rounds for boxing.

### Model results

The first version predicted the dataset's `Level` column and reported 88.5% accuracy. Checking that number turned up three problems:

- **The labels don't measure difficulty.** 1,093 rows carry a publisher prefix (`Holman`, `HM`, `FYR2`…) and all of them are "Intermediate", which looks like a default. Olympic lifts are labelled Beginner 30 times out of 35. Across 60 hand-written easy/hard pairs, the labels are right on 8, tied on 35 and backwards on 17.
- **The score was inflated.** On rows with no publisher prefix, with duplicate descriptions kept in one fold, it falls to 82.9% accuracy and 0.59 balanced accuracy.
- **It had learned the wrong thing.** It ranked obvious easy/hard pairs worse than a coin flip, largely because a missing description reveals which source a row came from.

The current model uses **weak supervision** instead (see `app/services/difficulty_rules.py`). Because label accuracy can't rank models when the labels are the problem, it is judged on [easy/hard pairs](fitness-and-boxing-app/backend/data/judgement_pairs.json). The held-out set was fixed before the rules were written and scored once, using out-of-fold predictions.

| 32 held-out pairs | Correct |
|---|---|
| Old model | 14 (44%) |
| Rules alone | 30 (94%) |
| **Current model** | **31 (97%)** |

Limitations of this result:

- The same person wrote the rules and the pairs, so this is not independent validation. A review of the pairs by a qualified coach is the most valuable next step.
- Almost all of the gain comes from the rules. The model's own contribution is covering exercises no rule matches, and smoothing.
- That coverage is partial. With a whole family hidden from training, it rates snatches clearly hard (+1.39 against a -0.20 average) but misses rare moves: pistol squats come out at -0.46 and muscle-ups at +0.12. Rare skills depend on the rules.
- The score no longer predicts the dataset's Beginner label, by design.

Full numbers are in [`backend/models/metrics.json`](fitness-and-boxing-app/backend/models/metrics.json).

## Run it

You need Python 3.10+ and Node 18+.

**Backend** (http://127.0.0.1:5000)

```bash
cd fitness-and-boxing-app/backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The database is created automatically on first start. The ML model is trained automatically on first use (a few seconds) — or train and see the metrics yourself with `python ml/train.py`.

**Frontend** (http://localhost:5173, proxies `/api` to Flask)

```bash
cd fitness-and-boxing-app/frontend
npm install
npm run dev
```

**Demo account** (optional): fills a local account with about a month of made-up history, handy for demos.

```bash
cd fitness-and-boxing-app/backend
python scripts/seed_demo.py       # log in as demo / secondsout; --reset recreates it
```

Never run this against a deployed database: the password is public.

**Single-server mode:** run `npm run build`, then start the backend. Flask serves the built app from `frontend/dist` at http://127.0.0.1:5000.

**Tests**

```bash
cd fitness-and-boxing-app/backend
pip install -r requirements-dev.txt
python -m pytest tests -q          # auth, validation, plan rules, feedback loop, ML, stats, swaps

cd ../frontend
npm test                           # workout step builder and scheduling rules
```

### Configuration

Environment variables, all optional for local development:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs session cookies. **Set this in production.** A local key is generated in `backend/instance/` otherwise. |
| `DATABASE_PATH` | SQLite file location (default `backend/instance/app.db`). |
| `COOKIE_SECURE=1` | Mark the session cookie HTTPS-only. Set when deployed over HTTPS. |
| `FLASK_DEBUG=1` | Enable Flask debug mode (off by default). |

## API

All routes are under `/api` and, except `register`, `login` and `health`, need a logged-in session. Failed logins are limited to 8 per username and address every 15 minutes.

| Method | Route | Purpose |
|---|---|---|
| POST | `/register`, `/login`, `/logout` | Account |
| GET | `/me` | Current user |
| PUT | `/account/password` | Change password (needs the current one) |
| DELETE | `/account` | Delete the account and all its data (needs the password) |
| GET / PUT | `/profile` | Read / save profile |
| POST | `/plans` | Generate a plan from the profile and recent feedback |
| GET | `/plans`, `/plans/current`, `/plans/<id>` | List / active / one plan with sessions |
| POST | `/sessions/<id>/complete` | Mark done with `rating` (1–5) and optional `notes` |
| DELETE | `/sessions/<id>/complete` | Reopen a session and remove its rating |
| POST | `/exercises/<id>/swap` | Swap a gym exercise for the rest of the active plan |
| GET | `/stats` | Totals, streak, weekly volume, rating history, next-plan intensity |
| GET / POST | `/progress` | Weight, waist, body-fat log |
| DELETE | `/progress/<id>` | Delete a measurement |

## Known limitations

- Boxing sessions are template-based, not learned. The dataset has no boxing content.
- No sparring, partner drills or technique videos. Learn technique from a qualified coach.
- No email verification or password reset yet.
- Rating feedback applies to the next plan you generate, not to sessions in the current one.
- Weights lifted are not logged, so there is no per-exercise progression tracking.
- Exercise names and descriptions come straight from the dataset and vary in quality, and some still show publisher tags such as `HM`.
- Plans are not medical advice; there is no screening beyond "body parts to avoid".

## What changed in this rebuild

The first version did not start. Main fixes:

- Two competing app factories and a `routes.py` that imported a non-existent `app` object → one factory, working routes.
- No `SECRET_KEY`, no table creation, MySQL with a password-less root user → SQLite, auto-created schema, configurable secret.
- Login crashed on unknown usernames and printed password hashes to the console → generic errors, no hash logging, input validation.
- `TrainingPlan` model lacked the fields the routes wrote to it → consolidated schema (plans → sessions → exercises).
- The ML script read a file that didn't exist, scaled text columns, never evaluated, and was never loaded by Flask → trained, cross-validated against a baseline, and used by the planner. Missing ratings are no longer filled with an invented average.
- The Vue frontend imported an `App.vue` that didn't exist → full Vue 3 app.
- 16,000+ files from `venv/` and `node_modules/` were committed → `.gitignore`.

## Author

**Elvis Haziri**
📧 elvisihaziri@gmail.com
[LinkedIn Profile](https://www.linkedin.com/in/elvis-haziri-095b34251)
