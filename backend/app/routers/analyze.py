from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.analysis import UnparseableEmail, run_pipeline
from app.db import get_db
from app.schemas import AnalyzeRequest, AnalyzeResponse, EmailSource

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    """Analyze pasted text — either a full .eml or just a message body."""
    try:
        return run_pipeline(
            payload.raw_email,
            source=payload.source,
            db=db,
            domain_age_days=payload.domain_age_days,
            use_llm=payload.use_llm,
        )
    except UnparseableEmail as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/analyze/eml", response_model=AnalyzeResponse)
async def analyze_eml(
    request: Request,
    source: EmailSource = "upload",
    domain_age_days: int | None = Query(default=None, ge=0),
    use_llm: bool = True,
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """Analyze a raw .eml posted as the request body.

    Takes bytes rather than a multipart form so the original message encoding
    survives the trip — and so the service needs no extra upload dependency.
    """
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=422, detail="Empty request body")
    try:
        return run_pipeline(
            raw, source=source, db=db, domain_age_days=domain_age_days, use_llm=use_llm
        )
    except UnparseableEmail as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
