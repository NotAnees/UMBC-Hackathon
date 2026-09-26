"""Optional Postgres persistence so the blue team can pull generated samples.

Two tables (schema mirrors PLAN.md's data model):
  emails        - the delivered sample as if it arrived (headers, subject, body).
                  This is what the blue team pulls and classifies. NO ground truth here,
                  so their detection stays honest.
  redteam_runs  - the answer key: label, difficulty, planted tells, linked to the email.
                  Used only to SCORE the detector afterwards (catch-rate / precision),
                  never as a detection input.

All writes are best-effort: if DATABASE_URL is unset or Postgres is down, generation
still works and delivery to Mailhog is unaffected — persistence just no-ops.
"""
import json
import os

from sqlalchemy import create_engine, text

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            return None
        try:
            _engine = create_engine(url, pool_pre_ping=True)
        except Exception:
            _engine = None
    return _engine


_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS emails (
        id           SERIAL PRIMARY KEY,
        source       TEXT NOT NULL DEFAULT 'redteam',
        raw_headers  TEXT,
        subject      TEXT,
        sender       TEXT,
        reply_to     TEXT,
        return_path  TEXT,
        body_text    TEXT,
        body_html    TEXT,
        received_at  TIMESTAMPTZ DEFAULT now(),
        created_at   TIMESTAMPTZ DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS redteam_runs (
        id              SERIAL PRIMARY KEY,
        email_id        INTEGER REFERENCES emails(id) ON DELETE CASCADE,
        kind            TEXT,
        ground_truth    TEXT,
        attack_type     TEXT,
        target_brand    TEXT,
        difficulty      TEXT,
        planted_tells   JSONB,
        detector_caught BOOLEAN,
        created_at      TIMESTAMPTZ DEFAULT now()
    );
    """,
]


def ensure_schema() -> bool:
    """Create the tables if they don't exist. Safe to call repeatedly. Never raises."""
    eng = _get_engine()
    if eng is None:
        return False
    try:
        with eng.begin() as conn:
            for stmt in _SCHEMA:
                conn.execute(text(stmt))
        return True
    except Exception:
        return False


def is_available() -> bool:
    eng = _get_engine()
    if eng is None:
        return False
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def save_sample(email_row: dict, run_row: dict) -> int | None:
    """Insert one email + its ground-truth run row. Returns the email id, or None on failure."""
    eng = _get_engine()
    if eng is None:
        return None
    try:
        with eng.begin() as conn:
            email_id = conn.execute(
                text(
                    """
                    INSERT INTO emails
                        (source, raw_headers, subject, sender, reply_to, return_path, body_text, body_html)
                    VALUES
                        (:source, :raw_headers, :subject, :sender, :reply_to, :return_path, :body_text, :body_html)
                    RETURNING id
                    """
                ),
                email_row,
            ).scalar_one()
            conn.execute(
                text(
                    """
                    INSERT INTO redteam_runs
                        (email_id, kind, ground_truth, attack_type, target_brand, difficulty, planted_tells)
                    VALUES
                        (:email_id, :kind, :ground_truth, :attack_type, :target_brand, :difficulty,
                         CAST(:planted_tells AS JSONB))
                    """
                ),
                {**run_row, "email_id": email_id, "planted_tells": json.dumps(run_row.get("planted_tells") or [])},
            )
        return email_id
    except Exception:
        return None
