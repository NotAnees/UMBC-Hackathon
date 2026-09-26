"""Curated bank of synthetic phishing sample templates, authored in-house.

These are test fixtures for our OWN detector — the red-team equivalent of a spam
corpus (cf. Nazario/PhishTank in PLAN.md). Every template is clearly synthetic,
uses only generic brand/role names, and is filled with a lookalike domain at request
time so the blue-team heuristics have realistic tells to catch. Nothing here is aimed
at a real person and nothing leaves the Mailhog sandbox.

Each template carries placeholders:
  {brand}       - the display brand/role (e.g. "PayPal", "IT Helpdesk")
  {look_domain} - a computed lookalike domain (e.g. "paypal-secure-verify.com")
  {link}        - a full lookalike URL built from {look_domain}
"""
from dataclasses import dataclass

from .schemas import AttackType


@dataclass(frozen=True)
class SampleTemplate:
    subject: str
    from_name: str
    # Local part of the sender; the domain is the computed lookalike ({look_domain}).
    from_local: str
    body: str


# Lookalike-domain suffixes appended to a brand slug to fabricate a mismatched sender.
LOOKALIKE_SUFFIXES = [
    "-secure-verify.com",
    "-account-support.net",
    "-billing-alert.com",
    "-id-confirm.co",
    "-service-notice.net",
]

BANK: dict[AttackType, list[SampleTemplate]] = {
    AttackType.credential_harvest: [
        SampleTemplate(
            subject="[Action Required] Unusual sign-in to your {brand} account",
            from_name="{brand} Account Security",
            from_local="no-reply",
            body=(
                "Dear Customer,\n\n"
                "We detected a sign-in to your {brand} account from an unrecognized device. "
                "For your protection, access has been temporarily limited.\n\n"
                "Confirm your identity within 24 hours to avoid permanent suspension:\n"
                "{link}\n\n"
                "If you do not verify, your account will be locked.\n\n"
                "{brand} Account Security Team"
            ),
        ),
        SampleTemplate(
            subject="Your {brand} password expires today",
            from_name="{brand} IT Support",
            from_local="support",
            body=(
                "Hello,\n\n"
                "Our records show your {brand} password expires today. To keep your mailbox "
                "active, re-validate your credentials using the secure portal below:\n\n"
                "{link}\n\n"
                "Accounts that are not updated will be deactivated automatically.\n\n"
                "Thank you,\n{brand} Helpdesk"
            ),
        ),
    ],
    AttackType.bec_urgency: [
        SampleTemplate(
            subject="Quick task - are you at your desk?",
            from_name="{brand} CFO",
            from_local="finance.director",
            body=(
                "Hi,\n\n"
                "I'm heading into back-to-back meetings and need you to handle something "
                "urgently and discreetly. We need to process a vendor payment today before "
                "the cutoff. Are you available to action a wire transfer right now?\n\n"
                "Reply to this email as soon as you see it - I can't take calls at the moment.\n\n"
                "Sent from my iPhone"
            ),
        ),
        SampleTemplate(
            subject="Urgent - gift card purchase for client",
            from_name="{brand} Manager",
            from_local="exec.office",
            body=(
                "Hi,\n\n"
                "I need a quick favor before end of day. We need several gift cards for a "
                "client appreciation gesture and it has to stay confidential until the reveal. "
                "Can you purchase them now and send me the codes? I'll approve reimbursement "
                "right after.\n\n"
                "This is time-sensitive, please handle personally.\n\n"
                "Thanks"
            ),
        ),
    ],
    AttackType.brand_impersonation: [
        SampleTemplate(
            subject="{brand}: Your recent payment could not be processed",
            from_name="{brand} Billing",
            from_local="billing",
            body=(
                "Dear Member,\n\n"
                "We were unable to process your most recent {brand} payment. To avoid "
                "interruption of service, please update your billing information within "
                "48 hours:\n\n"
                "{link}\n\n"
                "This is an automated message. Please do not reply.\n\n"
                "{brand} Billing Department"
            ),
        ),
        SampleTemplate(
            subject="Your {brand} package is on hold",
            from_name="{brand} Delivery",
            from_local="tracking",
            body=(
                "Hello,\n\n"
                "Your {brand} shipment could not be delivered due to an unpaid handling fee. "
                "Please confirm your details and settle the outstanding balance to reschedule "
                "delivery:\n\n"
                "{link}\n\n"
                "Unclaimed packages are returned to sender after 3 business days.\n\n"
                "{brand} Delivery Notifications"
            ),
        ),
    ],
    AttackType.generic: [
        SampleTemplate(
            subject="You have (3) pending messages awaiting delivery",
            from_name="{brand} Mail Administrator",
            from_local="postmaster",
            body=(
                "Dear User,\n\n"
                "Three incoming messages could not be delivered to your inbox due to a "
                "storage validation error. Release the pending messages by verifying your "
                "mailbox here:\n\n"
                "{link}\n\n"
                "Failure to verify within 24 hours will result in loss of these messages.\n\n"
                "{brand} Mail Administrator"
            ),
        ),
    ],
}
