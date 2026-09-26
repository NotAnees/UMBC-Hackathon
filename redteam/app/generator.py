"""Calls Gemini to produce a synthetic phishing sample for detector testing.

Includes a deterministic offline fallback so the demo still works if the network or
API key is unavailable — the same resilience posture the detection layer uses.
"""
import json
import os
import re

from .schemas import AttackType, GeneratedEmail
from .templates import build_prompt

# Overridable so we can bump the model without a code change. Verify the current
# Google AI Studio model IDs before the demo rather than trusting this default.
_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _parse_json_block(text: str) -> dict:
    """Extract the JSON object from an LLM response, tolerating stray fences/prose."""
    text = text.strip()
    # Strip ```json ... ``` fences if the model added them despite instructions.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    return json.loads(text)


def _offline_sample(attack_type: AttackType, brand: str | None) -> GeneratedEmail:
    """Canned sample used when no API key is set or the API call fails."""
    b = (brand or "IT Helpdesk").strip()
    return GeneratedEmail(
        subject=f"[Action Required] Verify your {b} account",
        from_name=f"{b} Security Team",
        from_address="security@it-helpdesk-support.example.net",
        body=(
            "Dear User,\n\n"
            "We detected unusual sign-in activity on your account. To avoid suspension, "
            "please verify your credentials within 24 hours by clicking the link below:\n\n"
            "http://it-helpdesk-support.example.net/verify\n\n"
            "Failure to act will result in permanent loss of access.\n\n"
            f"Regards,\n{b} Security Team"
        ),
    )


def generate_email(attack_type: AttackType, target_brand: str | None) -> GeneratedEmail:
    """Generate one synthetic phishing email. Falls back to a canned sample on any failure."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key.startswith("x"):
        return _offline_sample(attack_type, target_brand)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = build_prompt(attack_type, target_brand)
        resp = client.models.generate_content(model=_MODEL, contents=prompt)
        data = _parse_json_block(resp.text)
        return GeneratedEmail(
            subject=data["subject"],
            body=data["body"],
            from_name=data["from_name"],
            from_address=data["from_address"],
        )
    except Exception:
        # Never let a flaky API break the demo — fall back to the deterministic sample.
        return _offline_sample(attack_type, target_brand)
