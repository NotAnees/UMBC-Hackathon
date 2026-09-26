"""Delivers a generated sample to the local Mailhog sandbox — and nowhere else.

SAFETY BOUNDARY: the SMTP host is hardcoded to the Mailhog container. There is no
parameter, env override, or code path that accepts an arbitrary recipient or an
external SMTP host. This module can only ever talk to our own test inbox.

Beyond delivery, this module also stamps the message with realistic *phishing tells*
in the headers (mismatched Reply-To, a mismatched envelope sender, and failing
SPF/DKIM/DMARC results). Those tells exist so the blue-team Layer-1 heuristics have
genuine signals to detect — without them, a synthetic email only exercises the LLM
pass. They are entirely synthetic and never leave the sandbox.
"""
import email.policy
import smtplib
from email.message import EmailMessage

from .schemas import GeneratedEmail

# Keep headers on single lines (up to the RFC 5322 hard limit) instead of folding short
# ones like From/Subject across continuation lines. Folding is valid, but Mailhog's JSON
# view doesn't unfold it and shows a blank From — this keeps the demo inbox readable.
_POLICY = email.policy.default.clone(max_line_length=998)

# Hardcoded sandbox destination. Do NOT make these configurable — see module docstring.
_MAILHOG_HOST = "mailhog"
_MAILHOG_SMTP_PORT = 1025
# Fixed internal test mailbox. Not a real address; Mailhog accepts anything and never relays.
_SANDBOX_RECIPIENT = "detector@sandbox.local"

SANDBOX_DESTINATION = f"{_MAILHOG_HOST}:{_MAILHOG_SMTP_PORT} ({_SANDBOX_RECIPIENT})"


def _domain_of(address: str) -> str:
    """Return the domain part of an email address, or a fallback if it's malformed."""
    return address.split("@")[-1].strip() if "@" in address else "example.net"


def _base_label(domain: str) -> str:
    """First label of a domain (e.g. 'paypa1' from 'paypa1-secure.com')."""
    return domain.split(".")[0] or "brand"


def _build_headers(from_address: str) -> dict[str, str]:
    """Derive the synthetic spoofing headers from the (lookalike) sender address.

    - Reply-To lands on a *different* domain than From  -> trips the From/Reply-To
      mismatch heuristic.
    - Return-Path (envelope sender) is a *third* domain  -> trips Return-Path mismatch.
    - Authentication-Results / Received-SPF report failures -> trip the auth-header checks.
    """
    from_domain = _domain_of(from_address)
    base = _base_label(from_domain)

    reply_to = f"support@{base}-secure-team.com"
    envelope_sender = f"bounce@{base}-mailer.net"

    auth_results = (
        f"mailhog.local; spf=fail (sender IP is 203.0.113.13) "
        f"smtp.mailfrom={envelope_sender}; dkim=fail (signature verification failed); "
        f"dmarc=fail (p=none) header.from={from_domain}"
    )
    received_spf = (
        f"fail (mailhog.local: domain of {envelope_sender} does not "
        f"designate 203.0.113.13 as permitted sender)"
    )

    # Note: Return-Path is NOT set here. It is derived by the receiving MTA (Mailhog)
    # from the SMTP envelope sender we pass at send time, which avoids a duplicated header.
    return {
        "Reply-To": reply_to,
        "Authentication-Results": auth_results,
        "Received-SPF": received_spf,
        "_envelope_sender": envelope_sender,  # consumed by the caller, not a real header
    }


def send_to_sandbox(sample: GeneratedEmail) -> None:
    """Send the generated sample to the Mailhog sandbox over SMTP. No external delivery possible."""
    headers = _build_headers(sample.from_address)
    envelope_sender = headers.pop("_envelope_sender")

    msg = EmailMessage(policy=_POLICY)
    msg["Subject"] = sample.subject
    msg["From"] = f"{sample.from_name} <{sample.from_address}>"
    msg["To"] = _SANDBOX_RECIPIENT
    for name, value in headers.items():
        msg[name] = value
    # Tag it so the blue-team pipeline can attribute the source as red-team.
    msg["X-Redteam-Generated"] = "true"
    msg.set_content(sample.body)

    with smtplib.SMTP(_MAILHOG_HOST, _MAILHOG_SMTP_PORT, timeout=10) as smtp:
        # Envelope sender differs from the header From on purpose (Return-Path mismatch).
        # Recipient stays hardcoded to the sandbox mailbox.
        smtp.send_message(msg, from_addr=envelope_sender, to_addrs=[_SANDBOX_RECIPIENT])
