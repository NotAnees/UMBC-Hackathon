"""Assembles a synthetic phishing sample from a template + difficulty-aware crafting.

We author the sample text ourselves (samples.py) and craft its domains/links/headers
per difficulty (crafting.py) rather than calling an LLM: the content is a synthetic
detector test fixture, local generation means no refusals or network dependency, and
we get exact ground-truth `planted_tells` for free. The output shape matches what a
live-LLM path would produce, so a generation backend could be swapped in later.
"""
import random
import re

from .crafting import CraftedAttack, craft_auth, craft_domain, craft_link
from .samples import BANK, LOOKALIKE_SUFFIXES
from .schemas import AttackType, Difficulty

_DEFAULT_BRANDS = {
    AttackType.credential_harvest: "Webmail",
    AttackType.bec_urgency: "Acme Corp",
    AttackType.brand_impersonation: "PayPal",
    AttackType.generic: "IT Helpdesk",
}

_URGENCY_TERMS = (
    "24 hours", "48 hours", "urgent", "immediately", "suspend", "expire",
    "within", "time-sensitive", "asap", "as soon as", "deactivat", "permanent",
)
_GENERIC_GREETINGS = ("dear user", "dear customer", "dear member", "hello,", "hi,")


def _brand_slug(brand: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")
    return slug or "account"


def _detect_content_tells(body: str) -> list[str]:
    """Ground-truth tells that come from the body text itself, not the crafting layer."""
    low = body.lower()
    tells = []
    if any(g in low for g in _GENERIC_GREETINGS):
        tells.append("generic_greeting")
    if any(t in low for t in _URGENCY_TERMS):
        tells.append("urgency_language")
    return tells


def _to_html(text: str, href: str, anchor: str) -> str:
    """Render the body as HTML with a mismatched anchor (display != href)."""
    body = text.replace("{link}", f'<a href="{href}">{anchor}</a>')
    return "<html><body>" + body.replace("\n", "<br>\n") + "</body></html>"


def generate_email(
    attack_type: AttackType,
    target_brand: str | None,
    difficulty: Difficulty = Difficulty.easy,
    seed: int | None = None,
) -> CraftedAttack:
    """Produce one fully-crafted synthetic attack for the given type/brand/difficulty."""
    rng = random.Random(seed)
    brand = (target_brand or "").strip() or _DEFAULT_BRANDS[attack_type]
    slug = _brand_slug(brand)
    brand_domain = f"{slug}.com"  # the legit-looking domain the attacker imitates

    template = rng.choice(BANK[attack_type])

    # Domain + sender identity (difficulty-dependent).
    from_domain, domain_tell = craft_domain(slug, rng.choice(LOOKALIKE_SUFFIXES), difficulty, rng)
    from_address = f"{template.from_local}@{from_domain}"

    tells: list[str] = [domain_tell]

    # Reply-To / Return-Path mismatch: present for easy/medium, dropped for stealthy hard.
    if difficulty is Difficulty.hard:
        reply_to = f"{template.from_local}@{from_domain}"
        envelope_sender = f"bounce@{from_domain}"
    else:
        reply_to = f"support@{from_domain.split('.')[0]}-secure-team.com"
        envelope_sender = f"bounce@{from_domain.split('.')[0]}-mailer.net"
        tells += ["reply_to_mismatch", "return_path_mismatch"]

    # Auth-header posture.
    auth_results, received_spf, auth_tells = craft_auth(from_domain, envelope_sender, difficulty)
    tells += auth_tells

    # Link.
    href, anchor, link_tell = craft_link(from_domain, brand_domain, difficulty, rng)
    tells.append(link_tell)

    # Body: HTML with mismatched anchor for hard, plain text with raw link otherwise.
    def fill(text: str) -> str:
        return text.format(brand=brand, look_domain=from_domain, link=href)

    subject = fill(template.subject)
    from_name = fill(template.from_name)
    body_text = fill(template.body)
    body_html = _to_html(template.body.format(brand=brand, look_domain=from_domain, link="{link}"),
                         href, anchor) if anchor else None

    tells += _detect_content_tells(body_text)

    return CraftedAttack(
        subject=subject,
        from_name=from_name,
        from_address=from_address,
        reply_to=reply_to,
        envelope_sender=envelope_sender,
        auth_results=auth_results,
        received_spf=received_spf,
        body_text=body_text,
        body_html=body_html,
        planted_tells=tells,
    )
