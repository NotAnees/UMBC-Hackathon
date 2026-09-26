"""Tiny in-memory log of samples generated this session (powers the /stats view).

Not a database — it resets when the process restarts. It exists only so the dashboard
can show session activity (counts by type/difficulty/label, tell frequency) without
depending on the blue-team Postgres. Durable storage of verdicts is the blue team's job.
"""
from datetime import datetime, timezone

_LOG: list[dict] = []


def record(entry: dict) -> dict:
    """Append one generation event and return it (with a timestamp added)."""
    entry = {**entry, "created_at": datetime.now(timezone.utc).isoformat()}
    _LOG.append(entry)
    return entry


def all_records() -> list[dict]:
    return list(_LOG)


def clear() -> None:
    _LOG.clear()
