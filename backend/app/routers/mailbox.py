from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import UnparseableEmail, run_pipeline
from app.db import get_db
from app.email_parser import parse_email
from app.models import Email, Verdict
from app.schemas import MailboxMessage, MailboxPollResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["mailbox"])

DEFAULT_MAILHOG_API = "http://mailhog:8025/api/v2"
FETCH_TIMEOUT_SECONDS = 10.0


def _mailhog_api() -> str:
    return os.environ.get("MAILHOG_API_URL", DEFAULT_MAILHOG_API).rstrip("/")


def _unclaimed_twin(raw: str, db: Session) -> Email | None:
    """The row another service already stored for this same message, if any.

    The red-team service writes its samples straight to Postgres *and* delivers them
    to Mailhog, so polling would otherwise store a second copy — leaving its ground
    truth on one row and our verdict on the other, which makes catch-rate
    uncomputable. Matching claims the original instead.

    Sender and subject are the match key. The body is deliberately excluded: SMTP
    rewrites line endings, so a body stored as "\\n" arrives as "\\r\\n" and never
    compares equal. Requiring the row to have no external_id and no verdict yet is
    what keeps each delivered message claiming a different row when a batch contains
    several identical samples.
    """
    parsed = parse_email(raw)
    if not parsed.subject or not parsed.sender:
        return None

    return db.scalars(
        select(Email)
        .outerjoin(Verdict, Verdict.email_id == Email.id)
        .where(
            Email.external_id.is_(None),
            Email.subject == parsed.subject,
            Email.sender == parsed.sender,
            Verdict.id.is_(None),
        )
        .order_by(Email.id)
        .limit(1)
    ).first()


@router.get("/mailbox/poll", response_model=MailboxPollResponse)
def poll_mailbox(
    db: Session = Depends(get_db),
    limit: int = Query(default=25, ge=1, le=100),
    use_llm: bool = Query(
        default=False,
        description="Off by default: polling analyzes a whole batch, and the Gemini free "
        "tier allows only 20 requests per day per model. Turn it on for the live demo.",
    ),
) -> MailboxPollResponse:
    """Pull messages from the Mailhog sandbox and analyze the ones not yet seen.

    Idempotent: each message is recorded under its Mailhog ID, so re-polling
    reports already-analyzed messages instead of duplicating verdicts.
    """
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

    known = set(
        db.scalars(
            select(Email.external_id).where(
                Email.external_id.in_([i.get("ID") for i in items if i.get("ID")])
            )
        ).all()
    )

    results: list[MailboxMessage] = []
    analyzed = already = unparseable = 0

    for item in items:
        external_id = item.get("ID")
        raw = (item.get("Raw") or {}).get("Data")
        if not external_id or not raw:
            continue

        if external_id in known:
            already += 1
            results.append(
                MailboxMessage(external_id=external_id, status="already_analyzed")
            )
            continue

        try:
            verdict = run_pipeline(
                raw,
                source="mailhog",
                db=db,
                use_llm=use_llm,
                external_id=external_id,
                existing_email=_unclaimed_twin(raw, db),
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
        fetched=len(items),
        analyzed=analyzed,
        already_analyzed=already,
        unparseable=unparseable,
        used_llm=use_llm,
        messages=results,
    )
