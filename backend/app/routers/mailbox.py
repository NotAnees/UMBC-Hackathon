from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import gmail_source
from app.analysis import UnparseableEmail, run_pipeline
from app.db import get_db
from app.models import Email
from app.schemas import MailboxMessage, MailboxPollResponse, MailboxSource

logger = logging.getLogger(__name__)
router = APIRouter(tags=["mailbox"])

DEFAULT_MAILHOG_API = "http://mailhog:8025/api/v2"
FETCH_TIMEOUT_SECONDS = 10.0


def _mailhog_api() -> str:
    return os.environ.get("MAILHOG_API_URL", DEFAULT_MAILHOG_API).rstrip("/")


def _fetch_mailhog(limit: int) -> list[tuple[str, str]]:
    """(message id, raw message) pairs from the sandbox."""
    try:
        response = httpx.get(
            f"{_mailhog_api()}/messages", params={"limit": limit}, timeout=FETCH_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception as exc:
        logger.warning("Mailhog fetch failed: %s", exc)
        raise HTTPException(
            status_code=503, detail=f"Could not reach Mailhog at {_mailhog_api()}"
        ) from exc

    pairs = []
    for item in items:
        external_id = item.get("ID")
        raw = (item.get("Raw") or {}).get("Data")
        if external_id and raw:
            pairs.append((external_id, raw))
    return pairs


def _fetch_gmail(limit: int, db: Session) -> list[tuple[str, str]]:
    """(message id, raw message) pairs from the real mailbox.

    Ids already stored are skipped before fetching, because each message body costs a
    separate Gmail request — no point paying for mail that is already scored.
    """
    try:
        ids = gmail_source.list_message_ids(limit)
    except gmail_source.GmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    known = _known_ids(ids, db)
    pairs: list[tuple[str, str]] = []
    for message_id in ids:
        if message_id in known:
            pairs.append((message_id, ""))  # placeholder: reported as already analyzed
            continue
        try:
            raw = gmail_source.fetch_raw(message_id)
        except gmail_source.GmailUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if raw:
            pairs.append((message_id, raw))
    return pairs


def _known_ids(ids: list[str], db: Session) -> set[str]:
    if not ids:
        return set()
    return set(db.scalars(select(Email.external_id).where(Email.external_id.in_(ids))).all())


@router.get("/mailbox/poll", response_model=MailboxPollResponse)
def poll_mailbox(
    db: Session = Depends(get_db),
    source: MailboxSource = Query(
        default="mailhog",
        description="mailhog = the red-team sandbox; gmail = the real mailbox, read-only",
    ),
    limit: int = Query(default=25, ge=1, le=100),
    use_llm: bool = Query(
        default=False,
        description="Run the Claude deep scan on each new message. Off by default because a "
        "poll scores a whole batch and every message costs one API call.",
    ),
) -> MailboxPollResponse:
    """Pull mail from a source and analyze whatever has not been seen before.

    Idempotent: every message is stored under its upstream id, so re-polling reports
    already-analyzed messages instead of duplicating verdicts.
    """
    pairs = _fetch_gmail(limit, db) if source == "gmail" else _fetch_mailhog(limit)
    known = _known_ids([mid for mid, _ in pairs], db)

    results: list[MailboxMessage] = []
    analyzed = already = unparseable = 0

    for external_id, raw in pairs:
        if external_id in known or not raw:
            already += 1
            results.append(MailboxMessage(external_id=external_id, status="already_analyzed"))
            continue

        try:
            verdict = run_pipeline(
                raw, source=source, db=db, use_llm=use_llm, external_id=external_id
            )
        except UnparseableEmail:
            unparseable += 1
            results.append(MailboxMessage(external_id=external_id, status="unparseable"))
            continue

        analyzed += 1
        results.append(
            MailboxMessage(
                external_id=external_id,
                subject=verdict.email.subject,
                sender=verdict.email.sender,
                status="analyzed",
                verdict_id=verdict.verdict_id,
                risk_score=verdict.risk_score,
                risk_label=verdict.risk_label,
            )
        )

    return MailboxPollResponse(
        source=source,
        fetched=len(pairs),
        analyzed=analyzed,
        already_analyzed=already,
        unparseable=unparseable,
        used_llm=use_llm,
        messages=results,
    )


@router.get("/mailbox/sources")
def mailbox_sources() -> dict:
    """Which sources are usable right now, so the UI can disable what is not set up."""
    return {
        "mailhog": {"available": True, "label": "Red-team sandbox"},
        "gmail": {
            "available": gmail_source.is_configured(),
            "label": "Gmail inbox (read-only)",
            "hint": "Run backend/scripts/gmail_authorize.py on the host to enable.",
        },
    }
