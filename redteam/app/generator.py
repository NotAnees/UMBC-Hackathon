"""Builds a synthetic phishing sample by filling an in-house template from samples.py.

We author the sample text ourselves (see samples.py) rather than calling an LLM: the
content is a clearly-synthetic detector test fixture, and generating it locally means
no network dependency and no provider refusals mid-demo. The output shape is identical
to what a live LLM path would produce, so a generation backend could be swapped in later
without changing callers.
"""
import random
import re

from .samples import BANK, LOOKALIKE_SUFFIXES
from .schemas import AttackType, GeneratedEmail


def _brand_slug(brand: str) -> str:
    """'IT Helpdesk' -> 'it-helpdesk'; used to build a lookalike domain from the brand."""
    slug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")
    return slug or "account"


def _lookalike_domain(brand: str, rng: random.Random) -> str:
    """Fabricate a mismatched, brand-resembling domain (the sender-identity tell)."""
    return f"{_brand_slug(brand)}{rng.choice(LOOKALIKE_SUFFIXES)}"


_DEFAULT_BRANDS = {
    AttackType.credential_harvest: "Webmail",
    AttackType.bec_urgency: "Acme Corp",
    AttackType.brand_impersonation: "PayPal",
    AttackType.generic: "IT Helpdesk",
}


def generate_email(
    attack_type: AttackType,
    target_brand: str | None,
    seed: int | None = None,
) -> GeneratedEmail:
    """Produce one synthetic phishing email for the given attack type and brand.

    `seed` makes selection deterministic (useful for reproducible demo/tests); when None,
    a random template and lookalike domain are chosen for variety.
    """
    rng = random.Random(seed)
    brand = (target_brand or "").strip() or _DEFAULT_BRANDS[attack_type]

    template = rng.choice(BANK[attack_type])
    look_domain = _lookalike_domain(brand, rng)
    link = f"http://{look_domain}/verify"

    def fill(text: str) -> str:
        return text.format(brand=brand, look_domain=look_domain, link=link)

    return GeneratedEmail(
        subject=fill(template.subject),
        body=fill(template.body),
        from_name=fill(template.from_name),
        from_address=f"{template.from_local}@{look_domain}",
    )
