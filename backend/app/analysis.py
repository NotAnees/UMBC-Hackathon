from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detection.heuristics import HeuristicResult, run_heuristics
from app.detection.llm_pass import LlmResult, run_llm_pass
from app.detection.scorer import RiskScore, ScoreResult, compute_risk_score, score_heuristics
from app.email_parser import ParsedEmail, parse_email
from app.models import Email, Verdict
from app.schemas import AnalyzeResponse


class UnparseableEmail(ValueError):
    """Raised when a payload yields no usable email fields at all."""


def _content_hash(parsed: ParsedEmail) -> str:
    """Stable identity for 'the same email' across scans (extension, poll, paste).

    Keyed on sender + subject + body_text so the same message analyzed twice maps to one
    row, while separately-generated samples (different lookalike links in the body) stay
    distinct.
    """
    key = "\n".join(
        [
            (parsed.sender or "").strip().lower(),
            (parsed.subject or "").strip().lower(),
            (parsed.body_text or "").strip(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()


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


def rescan_verdict(verdict_id: int, db: Session, use_llm: bool = True) -> AnalyzeResponse | None:
    """Re-run the pipeline on an already-scored email and UPDATE its verdict in place.

    Powers the History "deep scan this page" button. Returns None if the verdict is gone.
    """
    row = db.execute(
        select(Email, Verdict).join(Verdict, Verdict.email_id == Email.id).where(Verdict.id == verdict_id)
    ).first()
    if row is None:
        return None
    email, _ = row
    # Reconstruct a raw message from stored fields so parse_email re-derives auth_results;
    # existing_email pins the update to this exact row (no new row, no external_id churn).
    raw = f"{email.raw_headers or ''}\n\n{email.body_text or ''}"
    return run_pipeline(raw, source=email.source, db=db, use_llm=use_llm, existing_email=email)


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
    content_hash = _content_hash(parsed)

    # Find the row this scan belongs to: an explicit existing_email, else the same
    # upstream id, else the same content — so one email keeps one verdict, updated in
    # place, rather than accruing a new row (and a different score) on every scan.
    email = existing_email
    if email is None and external_id:
        email = db.scalar(select(Email).where(Email.external_id == external_id))
    if email is None:
        email = db.scalar(select(Email).where(Email.content_hash == content_hash))

    if email is None:
        email = Email(source=source)
        db.add(email)

    # Refresh the stored fields (keep the original source; only set external_id when given).
    if external_id is not None:
        email.external_id = external_id
    email.content_hash = content_hash
    email.raw_headers = parsed.raw_headers
    email.subject = parsed.subject
    email.sender = parsed.sender
    email.reply_to = parsed.reply_to
    email.body_text = parsed.body_text
    email.body_html = parsed.body_html
    if parsed.received_at is not None:
        email.received_at = parsed.received_at
    db.flush()

    # One verdict per email: update the existing one in place, or create the first.
    verdict = db.scalar(
        select(Verdict).where(Verdict.email_id == email.id).order_by(Verdict.id.desc())
    )
    if verdict is None:
        verdict = Verdict(email_id=email.id)
        db.add(verdict)

    verdict.heuristic_score = scored.heuristic_score
    verdict.heuristic_findings = scored.heuristic_findings
    verdict.llm_verdict = llm.verdict if llm else None
    verdict.llm_confidence = llm.confidence if llm else None
    verdict.llm_rationale = llm.rationale if llm else None
    verdict.llm_risky_spans = {"spans": llm.risky_spans} if llm else None
    verdict.link_mismatch = heuristics.link_mismatch
    verdict.unfamiliar_link = heuristics.unfamiliar_link
    verdict.typosquat = heuristics.typosquat
    verdict.domain_age_days = domain_age_days
    verdict.risk_score = risk.risk_score
    verdict.risk_label = risk.risk_label
    verdict.risk_components = risk.components
    verdict.final_score = scored.final_score
    verdict.final_label = scored.final_label

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
