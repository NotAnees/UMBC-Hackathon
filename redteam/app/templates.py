"""Prompt templates for each synthetic-phishing attack type.

These describe *tactics* (the tells a real phishing email exhibits) so the detector
has realistic material to catch. They never reference a real person, real email
address, or real organization contact — only generic brand/role names for realism.
"""
from .schemas import AttackType

# Shared framing prepended to every attack prompt. Keeps output structured and
# scoped to a sandbox-only detection test.
SYSTEM_FRAMING = """You are a red-team assistant helping a security team stress-test their own \
phishing detector inside a closed sandbox. Every message you produce is delivered ONLY to a \
local test inbox (Mailhog) and analyzed by the team's own classifier — it never reaches a real \
person. Produce a single synthetic sample email that exhibits realistic phishing tells so the \
detector has something meaningful to catch.

Return ONLY a JSON object with exactly these keys:
{
  "subject": "the email subject line",
  "from_name": "the display name of the fake sender",
  "from_address": "a plausible-but-fake sender email address on a lookalike/mismatched domain",
  "body": "the full plain-text email body"
}
Do not wrap the JSON in markdown fences or add commentary."""

_TEMPLATES = {
    AttackType.credential_harvest: (
        "Write a credential-harvesting email impersonating {brand}. It should ask the recipient "
        "to verify or reset their account credentials via a link, and include typical phishing "
        "tells: a generic greeting, a sense of urgency about account access, and a sender domain "
        "that only looks like the real brand."
    ),
    AttackType.bec_urgency: (
        "Write a business-email-compromise (BEC) message impersonating a senior figure at {brand} "
        "(e.g. a CFO or manager). It should pressure the recipient to act quickly on a financial "
        "or sensitive request, using urgency and authority as the manipulation levers, with no "
        "malicious link necessary — pure social engineering."
    ),
    AttackType.brand_impersonation: (
        "Write a brand-impersonation email posing as {brand}. Mimic the tone of a real "
        "notification (security alert, delivery notice, or billing update), include a call to "
        "action to click a link, and use a mismatched/lookalike sender domain as the giveaway."
    ),
    AttackType.generic: (
        "Write a generic phishing email that could plausibly target anyone from {brand}. Include "
        "common phishing characteristics: urgency, a generic greeting, a suspicious link, and a "
        "spoofed-looking sender."
    ),
}

_DEFAULT_BRANDS = {
    AttackType.credential_harvest: "a popular email provider",
    AttackType.bec_urgency: "a mid-size company",
    AttackType.brand_impersonation: "a well-known shipping company",
    AttackType.generic: "IT Helpdesk",
}


def build_prompt(attack_type: AttackType, target_brand: str | None) -> str:
    """Return the full LLM prompt for a given attack type and optional generic brand/role."""
    brand = (target_brand or "").strip() or _DEFAULT_BRANDS[attack_type]
    instruction = _TEMPLATES[attack_type].format(brand=brand)
    return f"{SYSTEM_FRAMING}\n\nTask: {instruction}"
