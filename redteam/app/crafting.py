"""Difficulty-aware crafting of the attack's domains, links, and auth posture.

The `difficulty` here is difficulty *for the detector*: an "easy" attack is loud and
obvious (many blatant tells), a "hard" attack is stealthy (subtle or even
header-clean). Each crafted attack also carries a `planted_tells` list — the ground
truth of what we deliberately put in, so the loop can later measure not just whether
the detector caught it but *which* signals it found vs. missed.

Everything here is synthetic and sandbox-only; see sender.py for the hard delivery
boundary. Generating stealthy/obfuscated samples is adversarial robustness testing of
our OWN classifier, not evasion of anyone else's.
"""
import random
from dataclasses import dataclass, field

from .schemas import Difficulty


@dataclass
class CraftedAttack:
    """Everything sender.py needs to deliver one sample, plus ground-truth annotation."""

    subject: str
    from_name: str
    from_address: str
    reply_to: str
    envelope_sender: str
    auth_results: str
    received_spf: str
    body_text: str
    body_html: str | None = None
    planted_tells: list[str] = field(default_factory=list)
    # For benign samples: the clean signals that make it actually legitimate.
    clean_signals: list[str] = field(default_factory=list)
    ground_truth: str = "phishing"
    # Unique token stamped into the X-Redteam-Id header and used as the ground-truth key,
    # so the blue team can join a delivered/analyzed email back to its answer key.
    redteam_id: str = ""


# --- domain crafting -------------------------------------------------------

_HOMOGLYPHS = {"a": "а", "e": "е", "o": "ο", "i": "і", "c": "с"}


def _typosquat(slug: str) -> str:
    """Swap one character for a lookalike ('paypal' -> 'paypa1')."""
    for real, fake in (("l", "1"), ("o", "0"), ("i", "l"), ("e", "3")):
        if real in slug:
            return slug.replace(real, fake, 1)
    return slug + "-support"


def _homoglyph_domain(slug: str, rng: random.Random) -> tuple[str, str]:
    """Return (display_domain, punycode_domain) using a Unicode homoglyph.

    Falls back to a subdomain-spoof domain if the homoglyph can't be IDNA-encoded.
    """
    for real, glyph in _HOMOGLYPHS.items():
        if real in slug:
            display = slug.replace(real, glyph, 1) + ".com"
            try:
                puny = display.encode("idna").decode("ascii")
                return display, puny
            except Exception:
                break
    # Subdomain spoof: the real brand appears as a subdomain of an attacker domain.
    token = rng.choice(["secure-login", "account-verify", "id-check"])
    spoof = f"{slug}.com-{token}.co"
    return spoof, spoof


def craft_domain(slug: str, suffix: str, difficulty: Difficulty, rng: random.Random):
    """Return (from_domain, tell) for the sender address, per difficulty."""
    if difficulty is Difficulty.easy:
        return f"{slug}{suffix}", "lookalike_domain_verbose"
    if difficulty is Difficulty.medium:
        return f"{_typosquat(slug)}.com", "typosquat_domain"
    display, puny = _homoglyph_domain(slug, rng)
    tell = "homoglyph_domain" if puny.startswith("xn--") else "subdomain_spoof"
    return puny, tell


# --- link crafting ---------------------------------------------------------


def craft_link(from_domain: str, brand_domain: str, difficulty: Difficulty, rng: random.Random):
    """Return (href, anchor_text_or_None, tell). anchor_text set only for HTML mismatch."""
    if difficulty is Difficulty.easy:
        ip = f"203.0.113.{rng.randint(2, 250)}"
        return f"http://{ip}/verify", None, "raw_ip_link"
    if difficulty is Difficulty.medium:
        token = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7))
        return f"https://bit.ly/{token}", None, "url_shortener_link"
    # hard: link text shows the real brand, href points at the lookalike (anchor mismatch)
    return f"http://{from_domain}/account/verify", f"https://{brand_domain}/account", "anchor_text_mismatch"


# --- auth-header posture ---------------------------------------------------


def craft_auth(from_domain: str, envelope_sender: str, difficulty: Difficulty):
    """Return (authentication_results, received_spf, tells) per difficulty.

    hard mode PASSES SPF/DKIM/DMARC on purpose: the attacker authenticated their own
    lookalike domain, so header checks alone can't catch it — the detector must rely on
    domain/URL/content signals instead. A strong talking point about layered detection.
    """
    ip = "203.0.113.13"
    if difficulty is Difficulty.hard:
        auth = (
            f"mailhog.local; spf=pass (sender IP is {ip}) smtp.mailfrom={envelope_sender}; "
            f"dkim=pass header.d={from_domain}; dmarc=pass (p=none) header.from={from_domain}"
        )
        spf = f"pass (mailhog.local: domain of {envelope_sender} designates {ip} as permitted sender)"
        return auth, spf, ["auth_pass_lookalike_domain"]
    if difficulty is Difficulty.medium:
        auth = (
            f"mailhog.local; spf=softfail (sender IP is {ip}) smtp.mailfrom={envelope_sender}; "
            f"dkim=none; dmarc=none header.from={from_domain}"
        )
        spf = f"softfail (mailhog.local: transitioning domain of {envelope_sender})"
        return auth, spf, ["auth_softfail", "dkim_none", "dmarc_none"]
    auth = (
        f"mailhog.local; spf=fail (sender IP is {ip}) smtp.mailfrom={envelope_sender}; "
        f"dkim=fail (signature verification failed); dmarc=fail (p=none) header.from={from_domain}"
    )
    spf = f"fail (mailhog.local: domain of {envelope_sender} does not designate {ip} as permitted sender)"
    return auth, spf, ["spf_fail", "dkim_fail", "dmarc_fail"]
