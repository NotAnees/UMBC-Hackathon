from __future__ import annotations

from dataclasses import dataclass

from app.detection.heuristics import AUTH_SIGNAL_NAMES, HeuristicResult

LEGITIMATE_MAX = 33
SUSPICIOUS_MAX = 66

# An LLM phishing call above this confidence floors the label at phishing.
LLM_PHISHING_FLOOR = 85

# A phishing-or-suspicious call at or above this confidence floors the label at
# suspicious. Without this the semantic pass has no way to express doubt: a
# "suspicious" call maps to a flat 50 subscore, which on a message with no links and
# no headers renormalises to ~24 and lands back in the legitimate band — the model
# saying "this looks wrong" and the product answering "legitimate". Below this
# confidence the model is guessing and the deterministic score stands on its own.
LLM_SUSPICIOUS_FLOOR = 50

# legitimate < suspicious < phishing. A floor may only raise a label; an LLM that is
# less alarmed than the deterministic signals must never talk the verdict down.
_SEVERITY = {"legitimate": 0, "suspicious": 1, "phishing": 2}


def _raise_to(label: str, floor: str) -> str:
    return floor if _SEVERITY[floor] > _SEVERITY[label] else label

# Must sum to 1.0. Tune here — domain_age is the noisiest input (old infrastructure
# gets compromised, legitimate businesses register new domains) and urgency_language
# the most false-positive-prone, so both are held low relative to hard evidence.
RISK_WEIGHTS = {
    "llm_confidence": 0.30,
    "auth_failure": 0.20,
    "url_mismatch": 0.15,
    "domain_age": 0.10,
    "typosquat": 0.10,
    "identity_mismatch": 0.10,
    "urgency_language": 0.05,
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
    llm_subscore: float | None = None,
    llm_verdict: str | None = None,
    llm_confidence: float | None = None,
) -> RiskScore:
    """Weighted risk score across the five components in `RISK_WEIGHTS`.

    When every component is measurable this is exactly the stated formula. A
    component that cannot be measured (no LLM pass yet, unknown domain age) is
    dropped and the remaining weights are renormalized, so the result stays on a
    0-100 scale instead of being silently deflated toward "legitimate" by
    missing data. `weight_covered` reports how much of the formula actually ran.

    `llm_subscore` is the *risk* value the semantic pass converts to (see
    `llm_risk_subscore`) and is what enters the formula; `llm_confidence` is the
    model's own confidence and is only read by the floors below. They are not
    interchangeable: a "suspicious" call is always subscore 50 whatever the model's
    confidence, so comparing a floor against the subscore would make the threshold
    meaningless. The component key stays `llm_confidence` because it is persisted
    in `risk_components` and labelled in the UI.
    """
    raw: dict[str, float | None] = {"llm_confidence": llm_subscore}
    for name in RISK_WEIGHTS:
        if name != "llm_confidence":
            raw[name] = result.subscores.get(name)

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

    label = label_for(risk)
    # Floor per PLAN.md section 6: a high-confidence phishing call from the semantic
    # pass stands even when the deterministic signals are quiet, which is the BEC case
    # (no bad links, no failed auth, nothing for the other components to measure).
    # The same case is why the weaker calls need a floor too: the AI carries 0.30, so
    # on a structurally-silent message its subscore alone cannot lift the weighted
    # score out of the legitimate band, and without these the label would follow the
    # silence rather than the reading.
    confidence = llm_confidence if llm_confidence is not None else (llm_subscore or 0)
    if llm_verdict == "phishing" and confidence > LLM_PHISHING_FLOOR:
        label = _raise_to(label, "phishing")
    elif llm_verdict in {"phishing", "suspicious"} and confidence >= LLM_SUSPICIOUS_FLOOR:
        label = _raise_to(label, "suspicious")

    return RiskScore(
        risk_score=risk,
        risk_label=label,
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
