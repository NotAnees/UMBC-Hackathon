"""Delivers a generated sample to the local Mailhog sandbox — and nowhere else.

SAFETY BOUNDARY: the SMTP host is hardcoded to the Mailhog container. There is no
parameter, env override, or code path that accepts an arbitrary recipient or an
external SMTP host. This module can only ever talk to our own test inbox.
"""
import smtplib
from email.message import EmailMessage

from .schemas import GeneratedEmail

# Hardcoded sandbox destination. Do NOT make these configurable — see module docstring.
_MAILHOG_HOST = "mailhog"
_MAILHOG_SMTP_PORT = 1025
# Fixed internal test mailbox. Not a real address; Mailhog accepts anything and never relays.
_SANDBOX_RECIPIENT = "detector@sandbox.local"

SANDBOX_DESTINATION = f"{_MAILHOG_HOST}:{_MAILHOG_SMTP_PORT} ({_SANDBOX_RECIPIENT})"


def send_to_sandbox(email: GeneratedEmail) -> None:
    """Send the generated sample to the Mailhog sandbox over SMTP. No external delivery possible."""
    msg = EmailMessage()
    msg["Subject"] = email.subject
    msg["From"] = f"{email.from_name} <{email.from_address}>"
    msg["To"] = _SANDBOX_RECIPIENT
    # Tag it so the blue-team pipeline can attribute the source as red-team.
    msg["X-Redteam-Generated"] = "true"
    msg.set_content(email.body)

    with smtplib.SMTP(_MAILHOG_HOST, _MAILHOG_SMTP_PORT, timeout=10) as smtp:
        smtp.send_message(msg)
