from __future__ import annotations

from dataclasses import dataclass

from app.detection.heuristics import AUTH_SIGNAL_NAMES, HeuristicResult

LEGITIMATE_MAX = 33
SUSPICIOUS_MAX = 66

# risk = .3*llm_confidence + .2*auth_failure + .2*domain_age + .15*url_mismatch + .15*typosquat
RISK_WEIGHTS = {
    "llm_confidence": 0.30,
    "auth_failure": 0.20,
    "domain_age": 0.20,
    "url_mismatch": 0.15,
    "typosquat": 0.15,
}


@dataclass
class ScoreResult:
    heuristic_score: int
    heuristic_findings: dict
    link_mismatch: bool
    unfamiliar_link: bool
    final_score: int
    final_label: str


@dataclass
class RiskScore:
    risk_score: float
    risk_label: str
    components: dict[str, dict]
    unavailable: list[str]
    weight_covered: float


def label_for(score: float) -> str:
    if score <= LEGITIMATE_MAX:
        return "legitimate"
    if score <= SUSPICIOUS_MAX:
        return "suspicious"
    return "phishing"


def compute_risk_score(
    result: HeuristicResult,
    *,
    llm_confidence: float | None = None,
) -> RiskScore:
    """Weighted risk score across the five components in `RISK_WEIGHTS`.

    When every component is measurable this is exactly the stated formula. A
    component that cannot be measured (no LLM pass yet, unknown domain age) is
    dropped and the remaining weights are renormalized, so the result stays on a
    0-100 scale instead of being silently deflated toward "legitimate" by
    missing data. `weight_covered` reports how much of the formula actually ran.
    """
    raw: dict[str, float | None] = {
        "llm_confidence": llm_confidence,
        "auth_failure": result.subscores.get("auth_failure"),
        "domain_age": result.subscores.get("domain_age"),
        "url_mismatch": result.subscores.get("url_mismatch"),
        "typosquat": result.subscores.get("typosquat"),
    }

    available = {name: value for name, value in raw.items() if value is not None}
    unavailable = sorted(name for name, value in raw.items() if value is None)
    weight_covered = round(sum(RISK_WEIGHTS[name] for name in available), 4)

    if weight_covered:
        weighted = sum(RISK_WEIGHTS[name] * value for name, value in available.items())
        risk = round(weighted / weight_covered, 1)
    else:
        risk = 0.0

    components = {
        name: {
            "subscore": value,
            "weight": RISK_WEIGHTS[name],
            "contribution": round(RISK_WEIGHTS[name] * value / weight_covered, 1)
            if weight_covered
            else 0.0,
        }
        for name, value in available.items()
    }

    return RiskScore(
        risk_score=risk,
        risk_label=label_for(risk),
        components=components,
        unavailable=unavailable,
        weight_covered=weight_covered,
    )


def score_heuristics(result: HeuristicResult) -> ScoreResult:
    """Weighted heuristic score per PLAN.md section 6 — the signal-sum view,
    independent of `compute_risk_score`'s component formula.
    """
    label = label_for(result.score)

    by_name = {s.name: s for s in result.signals}
    auth_signals = [by_name[n] for n in AUTH_SIGNAL_NAMES if n in by_name]
    auth_failed_all = len(auth_signals) == len(AUTH_SIGNAL_NAMES) and all(
        s.triggered for s in auth_signals
    )
    identity_mismatch = bool(
        by_name.get("sender_reply_to_mismatch") and by_name["sender_reply_to_mismatch"].triggered
    )

    # Floor per PLAN.md section 6. Redundant at the current weights (that
    # combination already sums to 65), but the plan says to tune weights live,
    # so this keeps the guarantee from silently disappearing when they drop.
    if auth_failed_all and identity_mismatch and label == "legitimate":
        label = "suspicious"

    return ScoreResult(
        heuristic_score=result.score,
        heuristic_findings=result.findings(),
        link_mismatch=result.link_mismatch,
        unfamiliar_link=result.unfamiliar_link,
        final_score=result.score,
        final_label=label,
    )
