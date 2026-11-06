PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    date_joined   TEXT NOT NULL,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    age              INTEGER NOT NULL,
    weight_kg        REAL    NOT NULL,
    height_cm        REAL,
    experience_level TEXT    NOT NULL,
    goal             TEXT    NOT NULL,
    days_per_week    INTEGER NOT NULL,
    session_minutes  INTEGER NOT NULL,
    equipment        TEXT    NOT NULL,
    has_heavy_bag    INTEGER NOT NULL DEFAULT 0,
    avoid_body_parts TEXT    NOT NULL DEFAULT '',
    plan_weeks       INTEGER NOT NULL DEFAULT 4,
    updated_at       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS training_plans (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal             TEXT    NOT NULL,
    experience_level TEXT    NOT NULL,
    weeks            INTEGER NOT NULL,
    days_per_week    INTEGER NOT NULL,
    intensity        REAL    NOT NULL,
    notes            TEXT    NOT NULL DEFAULT '[]',
    seed             INTEGER,
    start_date       TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'active',
    created_at       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS training_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id          INTEGER NOT NULL REFERENCES training_plans(id) ON DELETE CASCADE,
    week             INTEGER NOT NULL,
    day_index        INTEGER NOT NULL,
    scheduled_for    TEXT    NOT NULL,
    kind             TEXT    NOT NULL,
    title            TEXT    NOT NULL,
    focus            TEXT,
    duration_minutes INTEGER,
    completed        INTEGER NOT NULL DEFAULT 0,
    completed_at     TEXT
);

CREATE TABLE IF NOT EXISTS session_exercises (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
    position         INTEGER NOT NULL,
    name             TEXT    NOT NULL,
    kind             TEXT    NOT NULL,
    exercise_type    TEXT,
    body_part        TEXT,
    equipment        TEXT,
    description      TEXT,
    sets             INTEGER,
    reps             INTEGER,
    duration_seconds INTEGER,
    rest_seconds     INTEGER,
    notes            TEXT,
    difficulty       REAL,  -- model-predicted difficulty, 0 (beginner) to 2 (expert)
    match_score      REAL   -- recommender score for this user, 0 to 1
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES training_sessions(id) ON DELETE SET NULL,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    content    TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    metric     TEXT    NOT NULL,
    value      REAL    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key        TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attempts_key    ON login_attempts(key, created_at);
CREATE INDEX IF NOT EXISTS idx_plans_user      ON training_plans(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_plan   ON training_sessions(plan_id);
CREATE INDEX IF NOT EXISTS idx_exercises_sess  ON session_exercises(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user   ON feedback(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_progress_user   ON progress(user_id, metric, date);
