from __future__ import annotations

from sqlalchemy.orm import Session

from app.detection.heuristics import HeuristicResult, run_heuristics
from app.detection.llm_pass import LlmResult, run_llm_pass
from app.detection.scorer import RiskScore, ScoreResult, compute_risk_score, score_heuristics
from app.email_parser import ParsedEmail, parse_email
from app.models import Email, Verdict
from app.schemas import AnalyzeResponse


class UnparseableEmail(ValueError):
    """Raised when a payload yields no usable email fields at all."""


def run_pipeline(
    raw: str | bytes,
    *,
    source: str,
    db: Session,
    domain_age_days: int | None = None,
    use_llm: bool = True,
    external_id: str | None = None,
    existing_email: Email | None = None,
) -> AnalyzeResponse:
    parsed = parse_email(raw)
    if not any([parsed.body_text, parsed.body_html, parsed.subject, parsed.sender]):
        raise UnparseableEmail("Nothing parseable in the supplied message")

    heuristics = run_heuristics(
        auth_results=parsed.auth_results,
        sender=parsed.sender,
        reply_to=parsed.reply_to,
        body_text=parsed.body_text,
        body_html=parsed.body_html,
        domain_age_days=domain_age_days,
    )

    llm = (
        run_llm_pass(
            subject=parsed.subject,
            sender=parsed.sender,
            reply_to=parsed.reply_to,
            auth_results=parsed.auth_results,
            body_text=parsed.body_text,
            body_html=parsed.body_html,
            heuristics=heuristics,
        )
        if use_llm
        else None
    )

    scored = score_heuristics(heuristics)
    risk = compute_risk_score(
        heuristics,
        llm_subscore=llm.risk_subscore if llm else None,
        llm_verdict=llm.verdict if llm else None,
        llm_confidence=llm.confidence if llm else None,
    )

    email, verdict = _persist(
        parsed, source, domain_age_days, heuristics, scored, risk, llm, external_id,
        existing_email, db,
    )
    return _response(email, verdict, parsed, heuristics, scored, risk, llm)


def _persist(
    parsed: ParsedEmail,
    source: str,
    domain_age_days: int | None,
    heuristics: HeuristicResult,
    scored: ScoreResult,
    risk: RiskScore,
    llm: LlmResult | None,
    external_id: str | None,
    existing_email: Email | None,
    db: Session,
) -> tuple[Email, Verdict]:
    if existing_email is not None:
        # Scoring a row another service already stored (a red-team sample), so the
        # verdict attaches to that row instead of creating a second copy of the same
        # email — otherwise ground truth and verdicts end up on different rows.
        email = existing_email
        email.external_id = external_id
    else:
        email = Email(
            source=source,
            external_id=external_id,
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
        llm_verdict=llm.verdict if llm else None,
        llm_confidence=llm.confidence if llm else None,
        llm_rationale=llm.rationale if llm else None,
        llm_risky_spans={"spans": llm.risky_spans} if llm else None,
        link_mismatch=heuristics.link_mismatch,
        unfamiliar_link=heuristics.unfamiliar_link,
        typosquat=heuristics.typosquat,
        domain_age_days=domain_age_days,
        risk_score=risk.risk_score,
        risk_label=risk.risk_label,
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
    llm: LlmResult | None,
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
            "body_text": parsed.body_text,
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
        llm=(
            {
                "verdict": llm.verdict,
                "confidence": llm.confidence,
                "rationale": llm.rationale,
                "risky_spans": llm.risky_spans,
                "signals_confirmed": llm.signals_confirmed,
            }
            if llm
            else None
        ),
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
