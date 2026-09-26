"""Delivers a crafted sample to the local Mailhog sandbox — and nowhere else.

SAFETY BOUNDARY: the SMTP host is hardcoded to the Mailhog container. There is no
parameter, env override, or code path that accepts an arbitrary recipient or an
external SMTP host. This module can only ever talk to our own test inbox.

The message's spoofing tells (mismatched Reply-To/Return-Path, SPF/DKIM/DMARC posture,
lookalike domains, HTML anchor mismatch) are decided upstream in crafting.py; this
module just stamps and delivers them so the blue-team heuristics have real signals.
"""
import email.policy
import smtplib
from email.message import EmailMessage

from .crafting import CraftedAttack

# Hardcoded sandbox destination. Do NOT make these configurable — see module docstring.
_MAILHOG_HOST = "mailhog"
_MAILHOG_SMTP_PORT = 1025
# Fixed internal test mailbox. Not a real address; Mailhog accepts anything and never relays.
_SANDBOX_RECIPIENT = "detector@sandbox.local"

SANDBOX_DESTINATION = f"{_MAILHOG_HOST}:{_MAILHOG_SMTP_PORT} ({_SANDBOX_RECIPIENT})"

# Keep short headers (From/Subject) on one line instead of folding; Mailhog's JSON view
# doesn't unfold and would otherwise show a blank From.
_POLICY = email.policy.default.clone(max_line_length=998)


def build_message(attack: CraftedAttack) -> EmailMessage:
    """Assemble the EmailMessage that gets delivered (single source of truth for content)."""
    msg = EmailMessage(policy=_POLICY)
    msg["Subject"] = attack.subject
    msg["From"] = f"{attack.from_name} <{attack.from_address}>"
    msg["To"] = _SANDBOX_RECIPIENT
    msg["Reply-To"] = attack.reply_to
    msg["Authentication-Results"] = attack.auth_results
    msg["Received-SPF"] = attack.received_spf
    # Tag it so the blue-team pipeline can attribute the source as red-team.
    msg["X-Redteam-Generated"] = "true"
    msg.set_content(attack.body_text)
    if attack.body_html:
        msg.add_alternative(attack.body_html, subtype="html")
    return msg


def header_block(attack: CraftedAttack) -> str:
    """A raw header block for DB persistence, incl. a synthesized Return-Path.

    Mailhog derives Return-Path from the SMTP envelope sender at delivery time, but the
    DB copy never goes through SMTP — so we write it explicitly here, giving the blue
    team's parser the same Return-Path / auth signals it would see in the inbox.
    """
    lines = [
        f"Return-Path: <{attack.envelope_sender}>",
        f"Authentication-Results: {attack.auth_results}",
        f"Received-SPF: {attack.received_spf}",
        f"From: {attack.from_name} <{attack.from_address}>",
        f"Reply-To: {attack.reply_to}",
        f"To: {_SANDBOX_RECIPIENT}",
        f"Subject: {attack.subject}",
        "X-Redteam-Generated: true",
    ]
    return "\n".join(lines)


def send_to_sandbox(attack: CraftedAttack) -> None:
    """Send the crafted sample to the Mailhog sandbox over SMTP. No external delivery possible."""
    msg = build_message(attack)
    with smtplib.SMTP(_MAILHOG_HOST, _MAILHOG_SMTP_PORT, timeout=10) as smtp:
        # Envelope sender may differ from the header From (Return-Path mismatch tell).
        # Recipient stays hardcoded to the sandbox mailbox.
        smtp.send_message(msg, from_addr=attack.envelope_sender, to_addrs=[_SANDBOX_RECIPIENT])
