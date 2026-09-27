"""Persist the red-team answer key so the blue team can score its detector.

Single-channel design (2026-09-26): the blue team's Mailhog poller is the ONE path
that inserts emails into the DB and analyzes them. The red team therefore does NOT
write the `emails` table anymore (that avoided duplicate rows). Instead we deliver to
Mailhog with a unique `X-Redteam-Id` header, and record the answer key here keyed by
that id. The blue team joins a delivered/analyzed email back to its ground truth by
reading `X-Redteam-Id` out of `emails.raw_headers`.

  redteam_ground_truth  - answer key (label, difficulty, planted tells) per redteam_id.

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


# Red-team-owned table only. No FK to emails (we don't create email rows) — the join key
# is redteam_id, which also travels in the delivered email's X-Redteam-Id header.
_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS redteam_ground_truth (
        id            SERIAL PRIMARY KEY,
        redteam_id    VARCHAR(64) UNIQUE,
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
    """Create the ground-truth table if it doesn't exist. Safe to call repeatedly. Never raises."""
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


def scorecard_data() -> dict | None:
    """Join our ground truth to the blue team's verdicts (via the X-Redteam-Id header
    the poller stores in emails.raw_headers) so we can score the detector. Never raises.
    """
    eng = _get_engine()
    if eng is None:
        return None
    try:
        with eng.connect() as conn:
            total = conn.execute(text("SELECT count(*) FROM redteam_ground_truth")).scalar_one()
            rows = conn.execute(
                text(
                    """
                    SELECT g.ground_truth AS truth,
                           g.difficulty   AS difficulty,
                           COALESCE(v.final_label, v.risk_label) AS verdict
                    FROM redteam_ground_truth g
                    JOIN emails e
                      ON substring(e.raw_headers from 'X-Redteam-Id: ([0-9a-f]+)') = g.redteam_id
                    JOIN verdicts v ON v.email_id = e.id
                    """
                )
            ).mappings().all()
        return {"total_ground_truth": int(total), "rows": [dict(r) for r in rows]}
    except Exception:
        return None


def save_ground_truth(redteam_id: str, run_row: dict) -> bool:
    """Record the answer key for one sample, keyed by its redteam_id. Never raises."""
    eng = _get_engine()
    if eng is None:
        return False
    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO redteam_ground_truth
                        (redteam_id, kind, ground_truth, attack_type, target_brand, difficulty, planted_tells)
                    VALUES
                        (:redteam_id, :kind, :ground_truth, :attack_type, :target_brand, :difficulty,
                         CAST(:planted_tells AS JSONB))
                    ON CONFLICT (redteam_id) DO NOTHING
                    """
                ),
                {**run_row, "redteam_id": redteam_id,
                 "planted_tells": json.dumps(run_row.get("planted_tells") or [])},
            )
        return True
    except Exception:
        return False
