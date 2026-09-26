from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Email, Feedback, Verdict
from app.schemas import EmailSource, VerdictDetail, VerdictList, VerdictSummary

router = APIRouter(tags=["history"])

VERDICT_LABELS = ("legitimate", "suspicious", "phishing")


def _summary_fields(email: Email, verdict: Verdict) -> dict:
    return {
        "verdict_id": verdict.id,
        "email_id": email.id,
        "source": email.source,
        "subject": email.subject,
        "sender": email.sender,
        "heuristic_score": verdict.heuristic_score,
        "heuristic_label": verdict.final_label,
        "risk_score": verdict.risk_score,
        "risk_label": verdict.risk_label,
        "llm_verdict": verdict.llm_verdict,
        "created_at": verdict.created_at,
    }


@router.get("/verdicts", response_model=VerdictList)
def list_verdicts(
    db: Session = Depends(get_db),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source: EmailSource | None = None,
    label: str | None = Query(default=None, description="Filter on the risk label"),
) -> VerdictList:
    """Most recent verdicts first, for the history list."""
    if label is not None and label not in VERDICT_LABELS:
        raise HTTPException(status_code=422, detail=f"label must be one of {VERDICT_LABELS}")

    filters = []
    if source is not None:
        filters.append(Email.source == source)
    if label is not None:
        filters.append(Verdict.risk_label == label)

    total = db.scalar(
        select(func.count()).select_from(Verdict).join(Email, Email.id == Verdict.email_id).where(*filters)
    )
    rows = db.execute(
        select(Email, Verdict)
        .join(Verdict, Verdict.email_id == Email.id)
        .where(*filters)
        .order_by(Verdict.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return VerdictList(
        total=total or 0,
        limit=limit,
        offset=offset,
        items=[VerdictSummary(**_summary_fields(email, verdict)) for email, verdict in rows],
    )


@router.get("/verdicts/{verdict_id}", response_model=VerdictDetail)
def get_verdict(verdict_id: int, db: Session = Depends(get_db)) -> VerdictDetail:
    """Everything stored about one verdict, including the why-breakdown."""
    row = db.execute(
        select(Email, Verdict)
        .join(Verdict, Verdict.email_id == Email.id)
        .where(Verdict.id == verdict_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No verdict with id {verdict_id}")

    email, verdict = row
    feedback = db.scalars(
        select(Feedback).where(Feedback.verdict_id == verdict_id).order_by(Feedback.id)
    ).all()

    return VerdictDetail(
        **_summary_fields(email, verdict),
        reply_to=email.reply_to,
        received_at=email.received_at,
        raw_headers=email.raw_headers,
        body_text=email.body_text,
        body_html=email.body_html,
        heuristic_findings=verdict.heuristic_findings,
        risk_components=verdict.risk_components,
        domain_age_days=verdict.domain_age_days,
        link_mismatch=verdict.link_mismatch,
        unfamiliar_link=verdict.unfamiliar_link,
        typosquat=verdict.typosquat,
        llm_confidence=verdict.llm_confidence,
        llm_rationale=verdict.llm_rationale,
        llm_risky_spans=(verdict.llm_risky_spans or {}).get("spans", []),
        feedback=[
            {
                "id": f.id,
                "verdict_id": f.verdict_id,
                "marked_by": f.marked_by,
                "is_correct": f.is_correct,
                "note": f.note,
                "created_at": f.created_at,
            }
            for f in feedback
        ],
    )
