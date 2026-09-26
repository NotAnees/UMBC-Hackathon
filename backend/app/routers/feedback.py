from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Feedback, Verdict
from app.schemas import FeedbackOut, FeedbackRequest

router = APIRouter(tags=["feedback"])


@router.post("/verdicts/{verdict_id}/feedback", response_model=FeedbackOut, status_code=201)
def add_feedback(
    verdict_id: int, payload: FeedbackRequest, db: Session = Depends(get_db)
) -> FeedbackOut:
    """Record whether a stored verdict was right, for the agreement-rate metric."""
    if db.scalar(select(Verdict.id).where(Verdict.id == verdict_id)) is None:
        raise HTTPException(status_code=404, detail=f"No verdict with id {verdict_id}")

    entry = Feedback(
        verdict_id=verdict_id,
        marked_by=payload.marked_by,
        is_correct=payload.is_correct,
        note=payload.note,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return FeedbackOut(
        id=entry.id,
        verdict_id=entry.verdict_id,
        marked_by=entry.marked_by,
        is_correct=entry.is_correct,
        note=entry.note,
        created_at=entry.created_at,
    )
