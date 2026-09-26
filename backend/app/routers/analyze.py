from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.detection.heuristics import HeuristicResult, run_heuristics
from app.detection.scorer import RiskScore, ScoreResult, compute_risk_score, score_heuristics
from app.email_parser import ParsedEmail, parse_email
from app.models import Email, Verdict
from app.schemas import AnalyzeRequest, AnalyzeResponse, EmailSource

router = APIRouter(tags=["analyze"])


def _analyze(
    raw: str | bytes,
    source: str,
    domain_age_days: int | None,
    db: Session,
) -> AnalyzeResponse:
    parsed = parse_email(raw)
    if not any([parsed.body_text, parsed.body_html, parsed.subject, parsed.sender]):
        raise HTTPException(status_code=422, detail="Nothing parseable in the supplied message")

    heuristics = run_heuristics(
        auth_results=parsed.auth_results,
        sender=parsed.sender,
        reply_to=parsed.reply_to,
        body_text=parsed.body_text,
        body_html=parsed.body_html,
        domain_age_days=domain_age_days,
    )
    scored = score_heuristics(heuristics)
    risk = compute_risk_score(heuristics)

    email, verdict = _persist(parsed, source, domain_age_days, heuristics, scored, risk, db)
    return _response(email, verdict, parsed, heuristics, scored, risk)


def _persist(
    parsed: ParsedEmail,
    source: str,
    domain_age_days: int | None,
    heuristics: HeuristicResult,
    scored: ScoreResult,
    risk: RiskScore,
    db: Session,
) -> tuple[Email, Verdict]:
    email = Email(
        source=source,
        raw_headers=parsed.raw_headers,
        subject=parsed.subject,
        sender=parsed.sender,
        reply_to=parsed.reply_to,
        body_text=parsed.body_text,
        body_html=parsed.body_html,
        received_at=parsed.received_at,
    )
    db.add(email)
    db.flush()

    verdict = Verdict(
        email_id=email.id,
        heuristic_score=scored.heuristic_score,
        heuristic_findings=scored.heuristic_findings,
        link_mismatch=heuristics.link_mismatch,
        unfamiliar_link=heuristics.unfamiliar_link,
        typosquat=heuristics.typosquat,
        domain_age_days=domain_age_days,
        risk_score=risk.risk_score,
        risk_components=risk.components,
        final_score=scored.final_score,
        final_label=scored.final_label,
    )
    db.add(verdict)
    db.commit()
    db.refresh(verdict)
    return email, verdict


def _response(
    email: Email,
    verdict: Verdict,
    parsed: ParsedEmail,
    heuristics: HeuristicResult,
    scored: ScoreResult,
    risk: RiskScore,
) -> AnalyzeResponse:
    return AnalyzeResponse(
        email_id=email.id,
        verdict_id=verdict.id,
        email={
            "subject": parsed.subject,
            "sender": parsed.sender,
            "reply_to": parsed.reply_to,
            "received_at": parsed.received_at,
            "auth_results": parsed.auth_results,
            "has_html": parsed.body_html is not None,
        },
        heuristic_score=scored.heuristic_score,
        heuristic_label=scored.final_label,
        risk_score=risk.risk_score,
        risk_label=risk.risk_label,
        risk_components=risk.components,
        risk_weight_covered=risk.weight_covered,
        risk_unavailable=risk.unavailable,
        link_mismatch=heuristics.link_mismatch,
        unfamiliar_link=heuristics.unfamiliar_link,
        typosquat=heuristics.typosquat,
        signals=[
            {
                "name": s.name,
                "weight": s.weight,
                "triggered": s.triggered,
                "evidence": s.evidence,
            }
            for s in heuristics.signals
        ],
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    """Analyze pasted text — either a full .eml or just a message body."""
    return _analyze(payload.raw_email, payload.source, payload.domain_age_days, db)


@router.post("/analyze/eml", response_model=AnalyzeResponse)
async def analyze_eml(
    request: Request,
    source: EmailSource = "upload",
    domain_age_days: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """Analyze a raw .eml posted as the request body.

    Takes bytes rather than a multipart form so the original message encoding
    survives the trip — and so the service needs no extra upload dependency.
    """
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=422, detail="Empty request body")
    return _analyze(raw, source, domain_age_days, db)
