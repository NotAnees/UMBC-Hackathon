"""Optional Postgres persistence so the blue team can pull generated samples.

Schema alignment: the blue team owns the canonical schema (backend/app/models.py),
so we match their `emails` table columns exactly and write there. We do NOT touch
their `redteam_runs` table (its FK is `generated_email_id` and it carries no ground
truth) — instead the answer key goes in our own `redteam_ground_truth` table, which
can't collide with their models regardless of which service creates tables first.

  emails                - the delivered sample as if it arrived (blue team pulls this
                          and classifies). NO ground truth, so detection stays honest.
  redteam_ground_truth  - red-team-owned answer key (label, difficulty, planted tells),
                          linked to emails.id, used only to SCORE the detector.

All writes are best-effort: if DATABASE_URL is unset or Postgres is down, generation
and Mailhog delivery are unaffected — persistence just no-ops.
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


# `emails` mirrors backend/app/models.py:Email exactly (same columns/types) so whichever
# service creates it first, both sides agree. `redteam_ground_truth` is ours alone.
_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS emails (
        id           SERIAL PRIMARY KEY,
        source       VARCHAR(20) NOT NULL DEFAULT 'redteam',
        external_id  VARCHAR(255),
        raw_headers  TEXT,
        subject      VARCHAR(998),
        sender       VARCHAR(320),
        reply_to     VARCHAR(320),
        body_text    TEXT,
        body_html    TEXT,
        received_at  TIMESTAMPTZ,
        created_at   TIMESTAMPTZ DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS redteam_ground_truth (
        id            SERIAL PRIMARY KEY,
        email_id      INTEGER REFERENCES emails(id) ON DELETE CASCADE,
        kind          TEXT,
        ground_truth  TEXT,
        attack_type   TEXT,
        target_brand  TEXT,
        difficulty    TEXT,
        planted_tells JSONB,
        created_at    TIMESTAMPTZ DEFAULT now()
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
    """Insert one email + its ground-truth row. Returns the email id, or None on failure."""
    eng = _get_engine()
    if eng is None:
        return None
    try:
        with eng.begin() as conn:
            email_id = conn.execute(
                text(
                    """
                    INSERT INTO emails (source, raw_headers, subject, sender, reply_to, body_text, body_html)
                    VALUES (:source, :raw_headers, :subject, :sender, :reply_to, :body_text, :body_html)
                    RETURNING id
                    """
                ),
                email_row,
            ).scalar_one()
            conn.execute(
                text(
                    """
                    INSERT INTO redteam_ground_truth
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
