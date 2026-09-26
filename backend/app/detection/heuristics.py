from __future__ import annotations

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


def _auth_signals(auth_results: str | None) -> list[Signal]:
    text = (auth_results or "").lower()
    return [
        _signal("spf_fail", "spf=fail" in text, "SPF authentication failed"),
        _signal("dkim_fail", "dkim=fail" in text, "DKIM authentication failed"),
        _signal("dmarc_fail", "dmarc=fail" in text, "DMARC authentication failed"),
    ]


def _identity_signal(sender: str | None, reply_to: str | None) -> Signal:
    sender_domain = address_domain(sender)
    reply_domain = address_domain(reply_to)
    mismatch = bool(sender_domain) and bool(reply_domain) and sender_domain != reply_domain
    return _signal(
        "sender_reply_to_mismatch",
        mismatch,
        f"From domain '{sender_domain}' != Reply-To domain '{reply_domain}'",
    )


def _keyword_signal(body_text: str | None) -> Signal:
    text = (body_text or "").lower()
    hits = [kw for kw in URGENCY_KEYWORDS if kw in text]
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

    auth_signals = _auth_signals(auth_results)
    signals = [
        *auth_signals,
        _identity_signal(sender, reply_to),
        _signal("link_mismatch", link_triggered, "; ".join(f.reason for f in link_findings)),
        _signal("typosquat", typo_triggered, "; ".join(typo_reasons)),
        _signal(
            "unfamiliar_link",
            unfamiliar_triggered,
            "; ".join(f.reason for f in unfamiliar_findings),
        ),
        _keyword_signal(body_text),
    ]

    subscores: dict[str, float | None] = {
        "auth_failure": round(
            sum(s.triggered for s in auth_signals) / len(auth_signals) * 100, 1
        ),
        "url_mismatch": url_mismatch_subscore(link_findings),
        "typosquat": 100.0 if typo_triggered else 0.0,
        "domain_age": domain_age_subscore(domain_age_days),
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
