from __future__ import annotations

import re
from dataclasses import dataclass, field
from email.utils import parseaddr

from app.detection.url_analysis import (
    LinkFinding,
    check_link_mismatch,
    check_typosquat,
    check_unfamiliar_links,
    link_hosts,
    registrable_domain,
)

URGENCY_KEYWORDS = [
    "urgent",
    "immediately",
    "verify your account",
    "account suspended",
    "act now",
    "final notice",
    "confirm your identity",
    "unusual activity",
    "your account will be",
]

# Weight per signal, summed for every triggered signal and capped at 100.
# `unfamiliar_link` is deliberately light: legitimate bulk mail routinely links
# to ESP/tracking/CDN domains, so it is corroborating evidence, not proof.
SIGNAL_WEIGHTS = {
    "spf_fail": 20,
    "dkim_fail": 15,
    "dmarc_fail": 15,
    "sender_reply_to_mismatch": 15,
    "link_mismatch": 20,
    "typosquat": 20,
    "unfamiliar_link": 10,
    "urgency_language": 10,
}

AUTH_SIGNAL_NAMES = ("spf_fail", "dkim_fail", "dmarc_fail")
AUTH_MECHANISMS = (("spf", "spf_fail"), ("dkim", "dkim_fail"), ("dmarc", "dmarc_fail"))

# How much each authentication outcome contributes to the auth_failure subscore.
# `none`/`neutral`/errors are not failures — they mean nothing was proven — so they
# sit between a pass and a real failure rather than being scored as clean.
AUTH_RESULT_RISK = {
    "pass": 0.0,
    "none": 0.5,
    "neutral": 0.5,
    "temperror": 0.5,
    "permerror": 0.5,
    "softfail": 0.75,
    "fail": 1.0,
}
FAILING_AUTH_RESULTS = frozenset({"fail", "softfail"})

# Urgency subscore by number of matched phrases. Deliberately shallow at one hit:
# legitimate mail says "urgent" all the time, so a lone match should nudge the score,
# not drive it. Tune here.
URGENCY_HIT_SCALE = {1: 40.0, 2: 70.0}

# How much each kind of link problem contributes to the url_mismatch subscore.
URL_MISMATCH_SEVERITY = {
    "text_spoof": 100.0,
    "raw_ip": 100.0,
    "punycode": 100.0,
    "shortener": 50.0,
    "other": 50.0,
}

# (max_age_days, subscore) — a freshly registered domain is the strongest signal.
DOMAIN_AGE_BANDS = ((7, 100.0), (30, 85.0), (90, 65.0), (180, 45.0), (365, 25.0), (730, 10.0))


@dataclass
class Signal:
    name: str
    weight: int
    triggered: bool
    evidence: str | None = None


@dataclass
class HeuristicResult:
    score: int
    link_mismatch: bool
    unfamiliar_link: bool
    typosquat: bool
    signals: list[Signal] = field(default_factory=list)
    # Graded 0-100 inputs for the weighted risk score. None means "not
    # measurable from this email" (e.g. domain age with no WHOIS data), which
    # the risk scorer treats differently from a measured zero.
    subscores: dict[str, float | None] = field(default_factory=dict)

    def findings(self) -> dict:
        return {
            s.name: {"triggered": s.triggered, "weight": s.weight, "evidence": s.evidence}
            for s in self.signals
        }


def _signal(name: str, triggered: bool, evidence: str | None) -> Signal:
    return Signal(name, SIGNAL_WEIGHTS[name], triggered, evidence if triggered else None)


def address_domain(header_value: str | None) -> str:
    """Registrable domain of an address header, tolerating the display-name form
    ('PayPal Service <service@paypal.com>')."""
    _, address = parseaddr(header_value or "")
    if "@" not in address:
        return ""
    return registrable_domain(address.rsplit("@", 1)[-1])


def domain_age_subscore(domain_age_days: int | None) -> float | None:
    """0-100 risk from domain age, or None when the age is unknown."""
    if domain_age_days is None or domain_age_days < 0:
        return None
    for max_days, subscore in DOMAIN_AGE_BANDS:
        if domain_age_days <= max_days:
            return subscore
    return 0.0


def url_mismatch_subscore(findings: list[LinkFinding]) -> float:
    return max((URL_MISMATCH_SEVERITY.get(f.kind, 50.0) for f in findings), default=0.0)


def auth_outcomes(auth_results: str | None) -> dict[str, str]:
    """The stated result per mechanism, e.g. {'spf': 'softfail', 'dmarc': 'none'}.
    Mechanisms absent from the headers are absent from the dict — not assumed to pass."""
    text = (auth_results or "").lower()
    outcomes: dict[str, str] = {}
    for mechanism, _ in AUTH_MECHANISMS:
        match = re.search(rf"\b{mechanism}\s*=\s*([a-z]+)", text)
        if match and match.group(1) in AUTH_RESULT_RISK:
            outcomes[mechanism] = match.group(1)
    return outcomes


def _auth_signals(outcomes: dict[str, str]) -> list[Signal]:
    signals = []
    for mechanism, signal_name in AUTH_MECHANISMS:
        result = outcomes.get(mechanism)
        signals.append(
            _signal(
                signal_name,
                result in FAILING_AUTH_RESULTS,
                f"{mechanism.upper()} returned '{result}'",
            )
        )
    return signals


def auth_failure_subscore(outcomes: dict[str, str]) -> float | None:
    """0-100 across the mechanisms the headers actually reported, or None when the
    message carries no authentication results at all (a pasted body, for instance) —
    unknown is not the same as clean."""
    if not outcomes:
        return None
    risks = [AUTH_RESULT_RISK[result] for result in outcomes.values()]
    return round(sum(risks) / len(risks) * 100, 1)


def _identity_signal(sender: str | None, reply_to: str | None) -> Signal:
    sender_domain = address_domain(sender)
    reply_domain = address_domain(reply_to)
    mismatch = bool(sender_domain) and bool(reply_domain) and sender_domain != reply_domain
    return _signal(
        "sender_reply_to_mismatch",
        mismatch,
        f"From domain '{sender_domain}' != Reply-To domain '{reply_domain}'",
    )


def urgency_hits(body_text: str | None) -> list[str]:
    text = (body_text or "").lower()
    return [kw for kw in URGENCY_KEYWORDS if kw in text]


def urgency_subscore(hits: list[str]) -> float:
    """Graded by how many phrases matched. A single urgent-sounding phrase is weak
    evidence — real mail says 'urgent' — while several stacked together is the
    pattern manipulation actually follows."""
    if not hits:
        return 0.0
    return URGENCY_HIT_SCALE.get(len(hits), 100.0)


def _keyword_signal(hits: list[str]) -> Signal:
    return _signal("urgency_language", bool(hits), f"matched: {', '.join(hits)}")


def run_heuristics(
    *,
    auth_results: str | None,
    sender: str | None,
    reply_to: str | None,
    body_text: str | None,
    body_html: str | None,
    known_domains: set[str] | None = None,
    brand_domains: set[str] | None = None,
    domain_age_days: int | None = None,
) -> HeuristicResult:
    html = body_html or ""
    sender_domain = address_domain(sender)

    link_triggered, link_findings = check_link_mismatch(html, body_text)
    unfamiliar_triggered, unfamiliar_findings = check_unfamiliar_links(
        html, body_text=body_text, sender_domain=sender_domain, known_domains=known_domains
    )
    typo_candidates = [d for d in [sender_domain, *link_hosts(html, body_text)] if d]
    typo_triggered, typo_reasons = check_typosquat(typo_candidates, brand_domains=brand_domains)

    outcomes = auth_outcomes(auth_results)
    hits = urgency_hits(body_text)
    identity = _identity_signal(sender, reply_to)
    signals = [
        *_auth_signals(outcomes),
        identity,
        _signal("link_mismatch", link_triggered, "; ".join(f.reason for f in link_findings)),
        _signal("typosquat", typo_triggered, "; ".join(typo_reasons)),
        _signal(
            "unfamiliar_link",
            unfamiliar_triggered,
            "; ".join(f.reason for f in unfamiliar_findings),
        ),
        _keyword_signal(hits),
    ]

    subscores: dict[str, float | None] = {
        "auth_failure": auth_failure_subscore(outcomes),
        "url_mismatch": url_mismatch_subscore(link_findings),
        "typosquat": 100.0 if typo_triggered else 0.0,
        "domain_age": domain_age_subscore(domain_age_days),
        "identity_mismatch": 100.0 if identity.triggered else 0.0,
        "urgency_language": urgency_subscore(hits),
    }

    score = min(sum(s.weight for s in signals if s.triggered), 100)
    return HeuristicResult(
        score=score,
        link_mismatch=link_triggered,
        unfamiliar_link=unfamiliar_triggered,
        typosquat=typo_triggered,
        signals=signals,
        subscores=subscores,
    )
